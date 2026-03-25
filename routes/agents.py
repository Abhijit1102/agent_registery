from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database.session import get_db
from schemas.pydantic_schemas import AgentCreate, AgentResponse
from services import agent_service

router = APIRouter(tags=["Agents"])


@router.post("/agents", response_model=AgentResponse, status_code=201)
def create_agent(payload: AgentCreate, db: Session = Depends(get_db)) -> AgentResponse:
    """Register a new agent. Tags are auto-extracted from the description."""
    return agent_service.create_agent(db, payload)


@router.get("/agents", response_model=List[AgentResponse])
def list_agents(db: Session = Depends(get_db)) -> List[AgentResponse]:
    """Return all registered agents."""
    return agent_service.list_agents(db)


@router.get("/search", response_model=List[AgentResponse])
def search_agents(
    q: str = Query(..., description="Keyword to search in name or description"),
    db: Session = Depends(get_db),
) -> List[AgentResponse]:
    """Case-insensitive search on agent name and description."""
    return agent_service.search_agents(db, q)
