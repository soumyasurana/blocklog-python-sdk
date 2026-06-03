from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any


class BlocklogLangChainCallbackHandler:
    def __init__(self, client, *, source: str = "langchain") -> None:
        self.client = client
        self.source = source
        self._last_run_id = None

    def on_chain_start(self, serialized: dict[str, Any], inputs: dict[str, Any], *, run_id=None, parent_run_id=None, **kwargs):
        self._last_run_id = run_id
        self.client.event(
            "agent.chain.started",
            {
                "serialized": serialized,
                "inputs": inputs,
                "parent_run_id": str(parent_run_id) if parent_run_id else None,
            },
            source=self.source,
            span_id=str(run_id) if run_id else None,
            causality_type="chain_start",
            agent_metadata=_agent_metadata(
                framework="langchain",
                parent_run_id=parent_run_id,
                extra=kwargs.get("metadata"),
                context={
                    "input_keys": sorted(inputs.keys()),
                    "context_fetched_at": _utc_now(),
                },
            ),
        )

    def on_chain_end(self, outputs: dict[str, Any], *, run_id=None, parent_run_id=None, **kwargs):
        self.client.event(
            "agent.chain.completed",
            {"outputs": outputs, "parent_run_id": str(parent_run_id) if parent_run_id else None},
            source=self.source,
            span_id=str(run_id or self._last_run_id) if (run_id or self._last_run_id) else None,
            causality_type="chain_end",
            agent_metadata=_agent_metadata(framework="langchain", parent_run_id=parent_run_id, extra=kwargs.get("metadata")),
        )

    def on_llm_start(self, serialized: dict[str, Any], prompts: Sequence[str], *, run_id=None, parent_run_id=None, **kwargs):
        self.client.event(
            "agent.model.started",
            {"serialized": serialized, "prompts": list(prompts), "parent_run_id": str(parent_run_id) if parent_run_id else None},
            source=self.source,
            span_id=str(run_id) if run_id else None,
            causality_type="llm_start",
            agent_metadata=_agent_metadata(
                framework="langchain",
                parent_run_id=parent_run_id,
                extra=kwargs.get("metadata"),
                context={
                    "prompt_count": len(prompts),
                    "context_fetched_at": _utc_now(),
                },
            ),
        )

    def on_llm_end(self, response: Any, *, run_id=None, parent_run_id=None, **kwargs):
        self.client.event(
            "agent.model.completed",
            {"response": _safe_model_dump(response), "parent_run_id": str(parent_run_id) if parent_run_id else None},
            source=self.source,
            span_id=str(run_id) if run_id else None,
            causality_type="llm_end",
            agent_metadata=_agent_metadata(framework="langchain", parent_run_id=parent_run_id, extra=kwargs.get("metadata")),
        )

    def on_tool_start(self, serialized: dict[str, Any], input_str: str, *, run_id=None, parent_run_id=None, **kwargs):
        self.client.event(
            "agent.tool.started",
            {"serialized": serialized, "input": input_str, "parent_run_id": str(parent_run_id) if parent_run_id else None},
            source=self.source,
            span_id=str(run_id) if run_id else None,
            causality_type="tool_start",
            agent_metadata=_agent_metadata(
                framework="langchain",
                parent_run_id=parent_run_id,
                extra=kwargs.get("metadata"),
                context={"context_fetched_at": _utc_now()},
            ),
        )

    def on_tool_end(self, output: Any, *, run_id=None, parent_run_id=None, **kwargs):
        self.client.event(
            "agent.tool.completed",
            {"output": _safe_model_dump(output), "parent_run_id": str(parent_run_id) if parent_run_id else None},
            source=self.source,
            span_id=str(run_id) if run_id else None,
            causality_type="tool_end",
            agent_metadata=_agent_metadata(framework="langchain", parent_run_id=parent_run_id, extra=kwargs.get("metadata")),
        )


def instrument_langchain(client):
    return BlocklogLangChainCallbackHandler(client)


def _safe_model_dump(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    if isinstance(value, (str, int, float, bool, list, dict)) or value is None:
        return value
    return str(value)


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
