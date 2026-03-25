import json
import re
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from database.orm_models import Agent
from schemas.pydantic_schemas import AgentCreate, AgentResponse

# ─── Stopwords ─────────────────────────────────────────────────────────────────

_STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "is", "are", "was", "were", "be",
    "been", "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "shall", "can", "this",
    "that", "these", "those", "it", "its", "not", "no", "so", "if",
    "then", "than", "also", "into", "up", "out", "about", "which", "who",
    "what", "when", "where", "how", "any", "all", "each", "both", "more",
    "their", "they", "them", "we", "our", "you", "your", "he", "she",
}

_MIN_TAG_LENGTH = 3
_MAX_TAGS = 10


def extract_tags(text: str) -> List[str]:
    """
    Simple keyword extraction:
    1. Lowercase
    2. Strip non-alpha characters
    3. Remove stopwords
    4. Deduplicate while preserving order
    5. Return up to MAX_TAGS tags of at least MIN_TAG_LENGTH chars
    """
    words = re.findall(r"[a-zA-Z]+", text.lower())
    seen: set[str] = set()
    tags: List[str] = []
    for word in words:
        if word not in _STOPWORDS and len(word) >= _MIN_TAG_LENGTH and word not in seen:
            seen.add(word)
            tags.append(word)
        if len(tags) >= _MAX_TAGS:
            break
    return tags


# ─── Service functions ─────────────────────────────────────────────────────────

def create_agent(db: Session, payload: AgentCreate) -> AgentResponse:
    existing = db.query(Agent).filter(Agent.name == payload.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Agent with name '{payload.name}' already exists.",
        )

    tags = extract_tags(payload.description)
    agent = Agent(
        name=payload.name,
        description=payload.description,
        endpoint=payload.endpoint,
        tags=json.dumps(tags),
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return AgentResponse.model_validate(agent)


def list_agents(db: Session) -> List[AgentResponse]:
    agents = db.query(Agent).all()
    return [AgentResponse.model_validate(a) for a in agents]


def search_agents(db: Session, q: str) -> List[AgentResponse]:
    """Case-insensitive search across name and description."""
    if not q or not q.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query 'q' must not be empty.",
        )
    keyword = f"%{q.strip().lower()}%"
    agents = (
        db.query(Agent)
        .filter(
            Agent.name.ilike(keyword) | Agent.description.ilike(keyword)
        )
        .all()
    )
    return [AgentResponse.model_validate(a) for a in agents]


def get_agent_by_name(db: Session, name: str) -> Optional[Agent]:
    return db.query(Agent).filter(Agent.name == name).first()
