from __future__ import annotations

from hashlib import sha256
from typing import Any

from blocklog.batching.buffer import EventBuffer
from blocklog.config import BlocklogConfig
from blocklog.context.managers import agent_session
from blocklog.context.vars import get_context
from blocklog.integrations.langchain import instrument_langchain
from blocklog.integrations.langgraph import instrument_langgraph
from blocklog.integrations.openai_agents import instrument_openai_agents
from blocklog.middleware.hooks import apply_hooks
from blocklog.models.events import EventEnvelope
from blocklog.models.responses import IngestResponse
from blocklog.signing.ed25519 import pseudo_sign
from blocklog.transport.httpx_sync import SyncTransport
from blocklog.transport.retry import RetryPolicy


class BlocklogClient:
    def __init__(self, config: BlocklogConfig) -> None:
        self.config = config
        self.transport = SyncTransport(
            base_url=config.base_url,
            api_key=config.api_key,
            timeout=config.timeout,
        )
        self.retry = RetryPolicy(max_retries=config.max_retries)
        self.buffer = EventBuffer(batch_size=config.batch_size)
        self.hooks = []

    @classmethod
    def from_env(cls) -> "BlocklogClient":
        return cls(BlocklogConfig.from_env())

    def add_hook(self, hook) -> "BlocklogClient":
        self.hooks.append(hook)
        return self

    def session(self, *, agent_id: str | None = None, source: str = "python-sdk", workflow_id=None):
        return agent_session(agent_id=agent_id, source=source, workflow_id=workflow_id)

    def instrument_openai_agents(self) -> "BlocklogClient":
        return instrument_openai_agents(self)

    def instrument_langchain(self) -> "BlocklogClient":
        return instrument_langchain(self)

    def instrument_langgraph(self) -> "BlocklogClient":
        return instrument_langgraph(self)

    def event(self, event_type: str, payload: dict[str, Any], **kwargs) -> IngestResponse:
        envelope = self._build_event(event_type=event_type, payload=payload, **kwargs)
        result = self.retry.run(lambda: self.transport.request("POST", "/logs", json=self._serialize(envelope)))
        return IngestResponse.model_validate(result)

    def enqueue(self, event_type: str, payload: dict[str, Any], **kwargs):
        envelope = self._build_event(event_type=event_type, payload=payload, **kwargs)
        batch = self.buffer.add(envelope)
        if batch:
            return self.flush(batch=batch)
        return None

    def flush(self, *, batch=None):
        batch = batch or self.buffer.flush()
        if not batch:
            return {"ingested": 0, "log_ids": []}
        payload = {"logs": [self._serialize(item) for item in batch]}
        return self.retry.run(lambda: self.transport.request("POST", "/logs/batch", json=payload))

    def _build_event(self, *, event_type: str, payload: dict[str, Any], **kwargs) -> EventEnvelope:
        context = get_context()
        event = EventEnvelope(
            event_type=event_type,
            payload=payload,
            source=kwargs.get("source") or (context.source if context else "python-sdk"),
            trace_id=kwargs.get("trace_id") or (context.trace_id if context else None),
            session_id=kwargs.get("session_id") or (context.session_id if context else None),
            workflow_id=kwargs.get("workflow_id") or (context.workflow_id if context else None),
            actor_id=kwargs.get("actor_id") or (context.agent_id if context else None),
            actor_type=kwargs.get("actor_type", "agent"),
            parent_event_id=kwargs.get("parent_event_id"),
            root_event_id=kwargs.get("root_event_id"),
            span_id=kwargs.get("span_id"),
            attempt_no=kwargs.get("attempt_no", 1),
            causality_type=kwargs.get("causality_type"),
            agent_metadata=kwargs.get("agent_metadata", {}),
        )
        if not event.idempotency_key:
            event.idempotency_key = self._idempotency_key(event)
        return event

    def _serialize(self, envelope: EventEnvelope) -> dict[str, Any]:
        payload = {
            "event_type": envelope.event_type,
            "timestamp": envelope.timestamp.isoformat(),
            "data": envelope.payload,
            "source": envelope.source,
            "idempotency_key": envelope.idempotency_key,
            "trace_id": str(envelope.trace_id) if envelope.trace_id else None,
            "session_id": str(envelope.session_id) if envelope.session_id else None,
            "workflow_id": str(envelope.workflow_id) if envelope.workflow_id else None,
            "parent_event_id": str(envelope.parent_event_id) if envelope.parent_event_id else None,
            "root_event_id": str(envelope.root_event_id) if envelope.root_event_id else None,
            "span_id": envelope.span_id,
            "attempt_no": envelope.attempt_no,
            "causality_type": envelope.causality_type,
            "schema_version": envelope.schema_version,
            "event_version": envelope.event_version,
            "actor_type": envelope.actor_type,
            "actor_id": envelope.actor_id,
            "agent_metadata": envelope.agent_metadata,
        }
        payload = apply_hooks(payload, self.hooks)
        payload["log_signature"] = pseudo_sign(payload)
        return payload

    @staticmethod
    def _idempotency_key(envelope: EventEnvelope) -> str:
        digest = sha256(
            f"{envelope.event_type}:{envelope.source}:{envelope.trace_id}:{envelope.session_id}:{envelope.payload}".encode(
                "utf-8"
            )
        ).hexdigest()[:32]
        return f"blk_{digest}"
