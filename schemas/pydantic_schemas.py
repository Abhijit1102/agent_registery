import json
from pydantic import BaseModel, field_validator, model_validator
from typing import List


# ─── Agent Schemas ─────────────────────────────────────────────────────────────

class AgentCreate(BaseModel):
    name: str
    description: str
    endpoint: str

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name must not be empty")
        return v

    @field_validator("endpoint")
    @classmethod
    def endpoint_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("endpoint must not be empty")
        return v

    @field_validator("description")
    @classmethod
    def description_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("description must not be empty")
        return v


class AgentResponse(BaseModel):
    id: int
    name: str
    description: str
    endpoint: str
    tags: List[str]

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def parse_tags(cls, values):
        """ORM stores tags as a JSON string; deserialize before validation."""
        if hasattr(values, "__dict__"):
            # ORM object
            raw = getattr(values, "tags", "[]")
            if isinstance(raw, str):
                values.__dict__["tags"] = json.loads(raw)
        elif isinstance(values, dict):
            raw = values.get("tags", "[]")
            if isinstance(raw, str):
                values["tags"] = json.loads(raw)
        return values


# ─── Usage Schemas ─────────────────────────────────────────────────────────────

class UsageCreate(BaseModel):
    caller: str
    target: str
    units: int
    request_id: str

    @field_validator("units")
    @classmethod
    def units_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("units must be a positive integer")
        return v

    @field_validator("caller", "target", "request_id")
    @classmethod
    def not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("field must not be empty")
        return v


class UsageLogResponse(BaseModel):
    id: int
    caller: str
    target: str
    units: int
    request_id: str

    model_config = {"from_attributes": True}


class UsageLogResult(BaseModel):
    """Returned from POST /usage — includes a flag for idempotent skips."""
    log: UsageLogResponse
    created: bool  # False if request_id already existed (duplicate skipped)


class UsageSummaryEntry(BaseModel):
    target: str
    total_units: int

    model_config = {"from_attributes": True}
