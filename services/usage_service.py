from typing import List

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database.orm_models import UsageLog, UsageSummary
from schemas.pydantic_schemas import (
    UsageCreate,
    UsageLogResponse,
    UsageLogResult,
    UsageSummaryEntry,
)
from services.agent_service import get_agent_by_name


def log_usage(db: Session, payload: UsageCreate) -> UsageLogResult:
    # Validate that caller and target agents exist
    caller_agent = get_agent_by_name(db, payload.caller)
    if not caller_agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Caller agent '{payload.caller}' does not exist.",
        )

    target_agent = get_agent_by_name(db, payload.target)
    if not target_agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target agent '{payload.target}' does not exist.",
        )

    # Idempotency check: if request_id already exists, return the existing log
    existing = (
        db.query(UsageLog)
        .filter(UsageLog.request_id == payload.request_id)
        .first()
    )
    if existing:
        return UsageLogResult(
            log=UsageLogResponse.model_validate(existing),
            created=False,
        )

    # Insert new usage log
    log_entry = UsageLog(
        caller=payload.caller,
        target=payload.target,
        units=payload.units,
        request_id=payload.request_id,
    )
    db.add(log_entry)

    try:
        db.flush()  # Send INSERT; catch IntegrityError from race conditions
    except IntegrityError:
        # Another concurrent request inserted the same request_id
        db.rollback()
        existing = (
            db.query(UsageLog)
            .filter(UsageLog.request_id == payload.request_id)
            .first()
        )
        return UsageLogResult(
            log=UsageLogResponse.model_validate(existing),
            created=False,
        )

    # UPSERT into usage_summary to maintain running totals
    # SQLite supports ON CONFLICT ... DO UPDATE (UPSERT) since version 3.24
    upsert_sql = text(
        """
        INSERT INTO usage_summary (target, total_units)
        VALUES (:target, :units)
        ON CONFLICT(target) DO UPDATE SET
            total_units = usage_summary.total_units + excluded.total_units
        """
    )
    db.execute(upsert_sql, {"target": payload.target, "units": payload.units})

    db.commit()
    db.refresh(log_entry)

    return UsageLogResult(
        log=UsageLogResponse.model_validate(log_entry),
        created=True,
    )


def get_usage_summary(db: Session) -> List[UsageSummaryEntry]:
    summaries = db.query(UsageSummary).order_by(UsageSummary.total_units.desc()).all()
    return [UsageSummaryEntry.model_validate(s) for s in summaries]
