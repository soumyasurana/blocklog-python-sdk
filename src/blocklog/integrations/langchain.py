from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

try:
    from langchain_core.callbacks import BaseCallbackHandler
except ImportError:  # pragma: no cover - allow use without langchain installed
    class BaseCallbackHandler:  # type: ignore[no-redef]
        """Fallback no-op base so this module is importable without langchain_core."""


class BlocklogLangChainCallbackHandler(BaseCallbackHandler):
    def __init__(self, client, *, source: str = "langchain") -> None:
        self.client = client
        self.source = source
        # Keyed by run_id so concurrent/nested runs don't clobber each other.
        # Falls back to None-keyed bucket for callbacks that never receive a run_id.
        self._run_id_stack: dict[UUID | None, UUID | None] = {}

    # ---------- internal helpers ----------

    def _emit(
        self,
        event_name: str,
        payload: dict[str, Any],
        *,
        run_id,
        parent_run_id,
        causality_type: str,
        metadata: dict[str, Any] | None,
        context: dict[str, Any] | None = None,
    ) -> None:
        resolved_run_id = run_id or self._run_id_stack.get(parent_run_id)
        self.client.event(
            event_name,
            {**payload, "parent_run_id": str(parent_run_id) if parent_run_id else None},
            source=self.source,
            span_id=str(resolved_run_id) if resolved_run_id else None,
            causality_type=causality_type,
            agent_metadata=_agent_metadata(
                framework="langchain",
                parent_run_id=parent_run_id,
                extra=metadata,
                context=context,
            ),
        )

    # ---------- chain ----------

    def on_chain_start(self, serialized: dict[str, Any], inputs: dict[str, Any], *, run_id=None, parent_run_id=None, **kwargs):
        self._run_id_stack[parent_run_id] = run_id
        self._emit(
            "agent.chain.started",
            {"serialized": serialized, "inputs": inputs},
            run_id=run_id,
            parent_run_id=parent_run_id,
            causality_type="chain_start",
            metadata=kwargs.get("metadata"),
            context={"input_keys": sorted(inputs.keys()), "context_fetched_at": _utc_now()},
        )

    def on_chain_end(self, outputs: dict[str, Any], *, run_id=None, parent_run_id=None, **kwargs):
        self._emit(
            "agent.chain.completed",
            {"outputs": outputs},
            run_id=run_id,
            parent_run_id=parent_run_id,
            causality_type="chain_end",
            metadata=kwargs.get("metadata"),
        )
        self._run_id_stack.pop(parent_run_id, None)

    def on_chain_error(self, error: BaseException, *, run_id=None, parent_run_id=None, **kwargs):
        self._emit(
            "agent.chain.errored",
            _error_payload(error),
            run_id=run_id,
            parent_run_id=parent_run_id,
            causality_type="chain_error",
            metadata=kwargs.get("metadata"),
        )
        self._run_id_stack.pop(parent_run_id, None)

    # ---------- llm ----------

    def on_llm_start(self, serialized: dict[str, Any], prompts: Sequence[str], *, run_id=None, parent_run_id=None, **kwargs):
        self._emit(
            "agent.model.started",
            {"serialized": serialized, "prompts": list(prompts)},
            run_id=run_id,
            parent_run_id=parent_run_id,
            causality_type="llm_start",
            metadata=kwargs.get("metadata"),
            context={"prompt_count": len(prompts), "context_fetched_at": _utc_now()},
        )

    def on_llm_end(self, response: Any, *, run_id=None, parent_run_id=None, **kwargs):
        self._emit(
            "agent.model.completed",
            {"response": _safe_model_dump(response)},
            run_id=run_id,
            parent_run_id=parent_run_id,
            causality_type="llm_end",
            metadata=kwargs.get("metadata"),
        )

    def on_llm_error(self, error: BaseException, *, run_id=None, parent_run_id=None, **kwargs):
        self._emit(
            "agent.model.errored",
            _error_payload(error),
            run_id=run_id,
            parent_run_id=parent_run_id,
            causality_type="llm_error",
            metadata=kwargs.get("metadata"),
        )

    # ---------- tool ----------

    def on_tool_start(self, serialized: dict[str, Any], input_str: str, *, run_id=None, parent_run_id=None, **kwargs):
        self._emit(
            "agent.tool.started",
            {"serialized": serialized, "input": input_str},
            run_id=run_id,
            parent_run_id=parent_run_id,
            causality_type="tool_start",
            metadata=kwargs.get("metadata"),
            context={"context_fetched_at": _utc_now()},
        )

    def on_tool_end(self, output: Any, *, run_id=None, parent_run_id=None, **kwargs):
        self._emit(
            "agent.tool.completed",
            {"output": _safe_model_dump(output)},
            run_id=run_id,
            parent_run_id=parent_run_id,
            causality_type="tool_end",
            metadata=kwargs.get("metadata"),
        )

    def on_tool_error(self, error: BaseException, *, run_id=None, parent_run_id=None, **kwargs):
        self._emit(
            "agent.tool.errored",
            _error_payload(error),
            run_id=run_id,
            parent_run_id=parent_run_id,
            causality_type="tool_error",
            metadata=kwargs.get("metadata"),
        )


def instrument_langchain(client) -> BlocklogLangChainCallbackHandler:
    return BlocklogLangChainCallbackHandler(client)


def _safe_model_dump(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    if isinstance(value, (str, int, float, bool, list, dict)) or value is None:
        return value
    return str(value)


def _error_payload(error: BaseException) -> dict[str, Any]:
    return {
        "error_type": type(error).__name__,
        "error_message": str(error),
    }


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _agent_metadata(*, framework: str, parent_run_id=None, extra: dict[str, Any] | None = None, context: dict[str, Any] | None = None) -> dict[str, Any]:
    metadata = {
        "framework": framework,
        "captured_at": _utc_now(),
        "parent_run_id": str(parent_run_id) if parent_run_id else None,
    }
    if context:
        metadata.update(context)
    if extra:
        metadata.update(extra)
    return metadata