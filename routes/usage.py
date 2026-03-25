from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database.session import get_db
from schemas.pydantic_schemas import UsageCreate, UsageLogResult, UsageSummaryEntry
from services import usage_service

router = APIRouter(tags=["Usage"])


@router.post("/usage", response_model=UsageLogResult, status_code=200)
def log_usage(payload: UsageCreate, db: Session = Depends(get_db)) -> UsageLogResult:
    """
    Log a usage event between two agents.

    - **caller** and **target** must be names of existing agents.
    - **units** must be a positive integer.
    - **request_id** is used for idempotency: duplicate IDs are silently ignored.
      The response includes `created=false` when a duplicate is detected.
    """
    return usage_service.log_usage(db, payload)


@router.get("/usage-summary", response_model=List[UsageSummaryEntry])
def get_usage_summary(db: Session = Depends(get_db)) -> List[UsageSummaryEntry]:
    """Return aggregated usage totals per target agent, sorted by total_units descending."""
    return usage_service.get_usage_summary(db)
