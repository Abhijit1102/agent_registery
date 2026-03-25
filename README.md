# Agent Registry & Usage Tracking Platform

A lightweight FastAPI service for registering AI agents, searching them by keyword, and tracking inter-agent usage with idempotency guarantees.

---

## Project Structure

```
agent_registry/
├── main.py                    # App entry point, router registration, DB init
├── database/
│   ├── orm_models.py          # SQLAlchemy models (Mapped[])
│   ├── schema.sql             # Raw SQL schema + UPSERT notes
│   └── session.py            # Engine, SessionLocal, get_db dependency
├── schemas/
│   └── pydantic_schemas.py   # Request / response models + validation
├── routes/
│   ├── agents.py             # POST /agents, GET /agents, GET /search
│   └── usage.py              # POST /usage, GET /usage-summary
├── services/
│   ├── agent_service.py      # Agent CRUD + keyword extraction
│   └── usage_service.py      # Idempotent usage logging + UPSERT aggregation
├── tests/
│   ├── conftest.py           # Pytest fixtures (in-memory DB, TestClient)
│   ├── test_agents.py        # Agent endpoint tests
│   └── test_usage.py         # Usage endpoint tests
└── README.md
```

---

## Setup Instructions

### 1. Prerequisites

- Python 3.11+
- pip

### 2. Install dependencies

```bash
cd agent_registry
pip install fastapi uvicorn sqlalchemy pydantic pytest httpx
```

Or with a requirements file:

```bash
pip install -r requirements.txt
```

**requirements.txt**

```
fastapi>=0.111.0
uvicorn[standard]>=0.29.0
sqlalchemy>=2.0.0
pydantic>=2.0.0
pytest>=8.0.0
httpx>=0.27.0
```

### 3. Run the server

```bash
uvicorn main:app --reload
```

The API will be available at: `http://127.0.0.1:8000`
Interactive docs: `http://127.0.0.1:8000/docs`

---

## Example API Calls

### Register an agent

```bash
curl -X POST http://localhost:8000/agents \
  -H "Content-Type: application/json" \
  -d '{
    "name": "TextSummarizer",
    "description": "Summarizes long documents into concise paragraphs using NLP",
    "endpoint": "http://summarizer.internal/run"
  }'
```

**Response:**

```json
{
  "id": 1,
  "name": "TextSummarizer",
  "description": "Summarizes long documents into concise paragraphs using NLP",
  "endpoint": "http://summarizer.internal/run",
  "tags": [
    "summarizes",
    "long",
    "documents",
    "concise",
    "paragraphs",
    "using",
    "nlp"
  ]
}
```

### List all agents

```bash
curl http://localhost:8000/agents
```

### Search agents

```bash
curl "http://localhost:8000/search?q=nlp"
```

### Log usage between agents

```bash
curl -X POST http://localhost:8000/usage \
  -H "Content-Type: application/json" \
  -d '{
    "caller": "OrchestratorBot",
    "target": "TextSummarizer",
    "units": 50,
    "request_id": "txn-20240101-abc123"
  }'
```

**Response (new):**

```json
{
  "log": {
    "id": 1,
    "caller": "OrchestratorBot",
    "target": "TextSummarizer",
    "units": 50,
    "request_id": "txn-20240101-abc123"
  },
  "created": true
}
```

**Response (duplicate):**

```json
{
  "log": { ... },
  "created": false
}
```

### Get usage summary

```bash
curl http://localhost:8000/usage-summary
```

**Response:**

```json
[
  { "target": "TextSummarizer", "total_units": 150 },
  { "target": "OrchestratorBot", "total_units": 30 }
]
```

---

## Running Tests

```bash
# From the agent_registry/ directory
pytest tests/ -v
```

All tests use an **in-memory SQLite** database and are fully isolated (tables are created and dropped per test).

---

## Idempotency Explained

When you POST to `/usage`, you supply a `request_id`. This is a client-generated unique identifier for the request (e.g., a UUID or transaction ID).

**How it works:**

1. Before inserting, the service checks if `request_id` already exists in `usage_logs`.
2. If found → return the existing log with `created: false`. Nothing is inserted or counted again.
3. If not found → insert the log and UPSERT `usage_summary` atomically.
4. A `UNIQUE` constraint on `usage_logs.request_id` also guards against race conditions at the database level. Even if two concurrent requests slip through the application check simultaneously, only one INSERT will succeed — the other raises `IntegrityError`, which is caught and handled gracefully.

This guarantees **exactly-once** counting even under retries or network failures.

---

## Design Decisions

| Decision                    | Rationale                                                                       |
| --------------------------- | ------------------------------------------------------------------------------- |
| SQLite + SQLAlchemy         | Zero-config local storage; easy swap to PostgreSQL by changing `DATABASE_URL`   |
| `usage_summary` table       | Pre-aggregated totals avoid `SUM(units)` full-table scans at query time         |
| UPSERT for aggregation      | `INSERT ... ON CONFLICT DO UPDATE` is atomic — no separate SELECT + UPDATE race |
| Tags as JSON string         | SQLite has no native array type; `json.dumps/loads` is simple and portable      |
| `created` field in response | Lets callers distinguish new vs duplicate without parsing error codes           |
| Service layer separation    | Routes stay thin; business logic is testable independently                      |

---

## Q&A: Extension & Scale

### 1. How to extend for billing without double charging?

The idempotency mechanism already provides the foundation:

- Each `request_id` maps to exactly one billing event. A billing worker reads `usage_logs` and marks rows as `billed=True` after charging.
- Add a `billed` boolean column and a `billed_at` timestamp to `usage_logs`.
- The billing job queries `WHERE billed = false`, charges the customer, then atomically sets `billed = true` in the same transaction.
- Because `request_id` is unique and `billed` is only flipped once, re-running the job on the same batch is safe.
- For extra safety, use a distributed lock (Redis `SETNX`) or a Stripe-style idempotency key when calling the external payment provider.

### 2. How to scale to 100K agents?

Several changes apply at different layers:

**Database:**

- Swap SQLite for PostgreSQL with indexes on `agents.name`, `agents.description` (full-text index via `tsvector`), and `usage_logs.request_id`.
- Partition `usage_logs` by date for faster scans and archival.

**Search:**

- Replace `ILIKE` with PostgreSQL full-text search or an Elasticsearch index for sub-millisecond keyword queries across 100K records.

**Aggregation:**

- The `usage_summary` UPSERT pattern scales well. For very high write throughput, buffer updates in Redis (`INCR`) and flush to the DB periodically.

**API layer:**

- Run multiple Uvicorn workers behind a load balancer (e.g., nginx or AWS ALB).
- Add a caching layer (Redis) for `GET /agents` and `GET /usage-summary` with short TTLs.
- Rate-limit `/usage` per caller to prevent abuse.
