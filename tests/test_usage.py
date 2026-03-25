import pytest
from fastapi.testclient import TestClient


# ─── Helpers ───────────────────────────────────────────────────────────────────

def create_agent(client: TestClient, name: str, description: str, endpoint: str):
    return client.post("/agents", json={
        "name": name,
        "description": description,
        "endpoint": endpoint,
    })


# ─── POST /agents ───────────────────────────────────────────────────────────────

class TestCreateAgent:
    def test_create_agent_success(self, client: TestClient):
        resp = create_agent(
            client,
            name="NLP Processor",
            description="Processes natural language text and extracts entities",
            endpoint="http://nlp.internal/process",
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "NLP Processor"
        assert data["endpoint"] == "http://nlp.internal/process"
        assert isinstance(data["tags"], list)
        assert len(data["tags"]) > 0
        assert "id" in data

    def test_create_agent_tags_are_extracted(self, client: TestClient):
        resp = create_agent(
            client,
            name="Summarizer",
            description="Summarizes long documents into short concise paragraphs",
            endpoint="http://summarizer.internal/run",
        )
        assert resp.status_code == 201
        tags = resp.json()["tags"]
        # Stopwords like "into", "short" filtered; meaningful words remain
        assert "summarizes" in tags or "documents" in tags or "concise" in tags

    def test_create_agent_duplicate_name_returns_409(self, client: TestClient):
        create_agent(client, "DupeBot", "Does something", "http://x.com")
        resp = create_agent(client, "DupeBot", "Same name different desc", "http://y.com")
        assert resp.status_code == 409
        assert "already exists" in resp.json()["detail"]

    def test_create_agent_empty_name_returns_422(self, client: TestClient):
        resp = client.post("/agents", json={"name": "", "description": "desc", "endpoint": "http://x.com"})
        assert resp.status_code == 422

    def test_create_agent_missing_field_returns_422(self, client: TestClient):
        resp = client.post("/agents", json={"name": "Bot"})
        assert resp.status_code == 422


# ─── GET /agents ────────────────────────────────────────────────────────────────

class TestListAgents:
    def test_list_agents_empty(self, client: TestClient):
        resp = client.get("/agents")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_agents_returns_all(self, client: TestClient):
        create_agent(client, "Alpha", "First agent", "http://alpha.com")
        create_agent(client, "Beta", "Second agent", "http://beta.com")
        resp = client.get("/agents")
        assert resp.status_code == 200
        assert len(resp.json()) == 2
        names = {a["name"] for a in resp.json()}
        assert names == {"Alpha", "Beta"}


# ─── GET /search ────────────────────────────────────────────────────────────────

class TestSearchAgents:
    def test_search_by_name(self, client: TestClient):
        create_agent(client, "TextParser", "Parses raw text data", "http://tp.com")
        create_agent(client, "ImageBot", "Handles image recognition tasks", "http://ib.com")
        resp = client.get("/search", params={"q": "text"})
        assert resp.status_code == 200
        results = resp.json()
        assert len(results) == 1
        assert results[0]["name"] == "TextParser"

    def test_search_by_description(self, client: TestClient):
        create_agent(client, "Classify", "Performs sentiment classification on reviews", "http://cls.com")
        resp = client.get("/search", params={"q": "sentiment"})
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_search_case_insensitive(self, client: TestClient):
        create_agent(client, "AudioTranscriber", "Transcribes audio files", "http://at.com")
        resp = client.get("/search", params={"q": "AUDIO"})
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_search_no_results(self, client: TestClient):
        create_agent(client, "Alpha", "First agent", "http://a.com")
        resp = client.get("/search", params={"q": "zzznomatch"})
        assert resp.status_code == 200
        assert resp.json() == []

    def test_search_missing_query_returns_422(self, client: TestClient):
        resp = client.get("/search")
        assert resp.status_code == 422

    def test_search_matches_multiple(self, client: TestClient):
        create_agent(client, "NLP Agent", "natural language processing", "http://nlp.com")
        create_agent(client, "Text Analyzer", "Analyzes natural language patterns", "http://ta.com")
        resp = client.get("/search", params={"q": "natural"})
        assert resp.status_code == 200
        assert len(resp.json()) == 2
