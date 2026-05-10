from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class IngestResponse(BaseModel):
    log_id: str
    company_id: str
    event_type: str
    source: str
    idempotency_key: str | None = None
    timestamp: datetime | None = None
    created_at: datetime
    trace_id: UUID | None = None
    session_id: UUID | None = None
    workflow_id: UUID | None = None
    parent_event_id: UUID | None = None
