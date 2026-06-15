from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class EventEnvelope(BaseModel):
    event_type: str
    payload: dict
    source: str = "python-sdk"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    idempotency_key: str | None = None
    trace_id: UUID | None = None
    session_id: UUID | None = None
    workflow_id: UUID | None = None
    parent_event_id: UUID | None = None
    root_event_id: UUID | None = None
    span_id: str | None = None
    attempt_no: int = 1
    causality_type: str | None = None
    schema_version: str = "1.0"
    event_version: str = "1.0"
    agent_type: str | None = None
    agent_id: str | None = None
    agent_metadata: dict = Field(default_factory=dict)


class SessionContext(BaseModel):
    trace_id: UUID = Field(default_factory=uuid4)
    session_id: UUID = Field(default_factory=uuid4)
    workflow_id: UUID | None = None
    agent_id: str | None = None
    source: str = "python-sdk"
