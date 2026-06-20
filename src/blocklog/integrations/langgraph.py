from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

try:
    from langchain_core.callbacks import BaseCallbackHandler
except ImportError:  # pragma: no cover
    class BaseCallbackHandler:  # type: ignore[no-redef]
        """Fallback no-op base so this module is importable without langchain_core."""


class BlocklogLangGraphCallbackHandler(BaseCallbackHandler):
    """Blocklog callback handler for LangGraph.

    Captures graph-level lifecycle events (node execution, edges, state
    transitions, subgraph runs) in addition to the standard LLM / tool /
    chain events inherited from the LangChain handler pattern.

    Usage::

        from blocklog.integrations.langgraph import instrument_langgraph

        handler = instrument_langgraph(client)

        # Pass to a compiled graph
        graph.invoke(inputs, config={"callbacks": [handler]})

        # Or attach globally via RunnableConfig
        from langchain_core.runnables import RunnableConfig
        config = RunnableConfig(callbacks=[handler])
    """

    def __init__(self, client, *, source: str = "langgraph") -> None:
        self.client = client
        self.source = source
        # Keyed by run_id; mirrors the LangChain handler's stack pattern so
        # concurrent / nested graph runs don't clobber one another.
        self._run_id_stack: dict[UUID | None, UUID | None] = {}
        # Track active node names per run_id for edge attribution.
        self._node_name_stack: dict[UUID | None, str | None] = {}

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

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
                framework="langgraph",
                parent_run_id=parent_run_id,
                extra=metadata,
                context=context,
            ),
        )

    # ------------------------------------------------------------------ #
    # Graph lifecycle                                                      #
    # ------------------------------------------------------------------ #

    def on_chain_start(
        self,
        serialized: dict[str, Any],
        inputs: dict[str, Any],
        *,
        run_id=None,
        parent_run_id=None,
        **kwargs,
    ) -> None:
        """Fired when the top-level CompiledGraph (or any sub-chain) starts."""
        self._run_id_stack[parent_run_id] = run_id

        graph_name = _graph_name(serialized)
        is_graph = _is_graph(serialized)
        event_name = "agent.graph.started" if is_graph else "agent.chain.started"
        causality = "graph_start" if is_graph else "chain_start"

        self._emit(
            event_name,
            {
                "graph_name": graph_name,
                "serialized": serialized,
                "inputs": _safe_state(inputs),
            },
            run_id=run_id,
            parent_run_id=parent_run_id,
            causality_type=causality,
            metadata=kwargs.get("metadata"),
            context={
                "input_keys": sorted(inputs.keys()) if isinstance(inputs, dict) else [],
                "context_fetched_at": _utc_now(),
            },
        )

    def on_chain_end(
        self,
        outputs: dict[str, Any],
        *,
        run_id=None,
        parent_run_id=None,
        **kwargs,
    ) -> None:
        """Fired when the top-level graph (or sub-chain) finishes."""
        serialized = kwargs.get("serialized") or {}
        is_graph = _is_graph(serialized)
        event_name = "agent.graph.completed" if is_graph else "agent.chain.completed"
        causality = "graph_end" if is_graph else "chain_end"

        self._emit(
            event_name,
            {"outputs": _safe_state(outputs)},
            run_id=run_id,
            parent_run_id=parent_run_id,
            causality_type=causality,
            metadata=kwargs.get("metadata"),
        )
        self._run_id_stack.pop(parent_run_id, None)
        self._node_name_stack.pop(run_id, None)

    def on_chain_error(
        self,
        error: BaseException,
        *,
        run_id=None,
        parent_run_id=None,
        **kwargs,
    ) -> None:
        """Fired when the graph (or sub-chain) raises an unhandled error."""
        serialized = kwargs.get("serialized") or {}
        is_graph = _is_graph(serialized)
        event_name = "agent.graph.errored" if is_graph else "agent.chain.errored"
        causality = "graph_error" if is_graph else "chain_error"

        self._emit(
            event_name,
            _error_payload(error),
            run_id=run_id,
            parent_run_id=parent_run_id,
            causality_type=causality,
            metadata=kwargs.get("metadata"),
        )
        self._run_id_stack.pop(parent_run_id, None)
        self._node_name_stack.pop(run_id, None)

    # ------------------------------------------------------------------ #
    # Node lifecycle                                                       #
    # LangGraph emits on_chain_* per node, tagged with the node name      #
    # in serialized["name"] / kwargs["name"].  We surface these as        #
    # dedicated node events for richer observability.                     #
    # ------------------------------------------------------------------ #

    def on_node_start(
        self,
        serialized: dict[str, Any],
        inputs: dict[str, Any],
        *,
        run_id=None,
        parent_run_id=None,
        **kwargs,
    ) -> None:
        """Fired when a graph node begins execution."""
        self._run_id_stack[parent_run_id] = run_id
        node_name = _node_name(serialized, kwargs)
        self._node_name_stack[run_id] = node_name

        self._emit(
            "agent.graph.node.started",
            {
                "node_name": node_name,
                "inputs": _safe_state(inputs),
            },
            run_id=run_id,
            parent_run_id=parent_run_id,
            causality_type="node_start",
            metadata=kwargs.get("metadata"),
            context={
                "node_name": node_name,
                "context_fetched_at": _utc_now(),
            },
        )

    def on_node_end(
        self,
        outputs: dict[str, Any],
        *,
        run_id=None,
        parent_run_id=None,
        **kwargs,
    ) -> None:
        """Fired when a graph node completes successfully."""
        node_name = self._node_name_stack.get(run_id)

        self._emit(
            "agent.graph.node.completed",
            {
                "node_name": node_name,
                "outputs": _safe_state(outputs),
            },
            run_id=run_id,
            parent_run_id=parent_run_id,
            causality_type="node_end",
            metadata=kwargs.get("metadata"),
        )
        self._run_id_stack.pop(parent_run_id, None)
        self._node_name_stack.pop(run_id, None)

    def on_node_error(
        self,
        error: BaseException,
        *,
        run_id=None,
        parent_run_id=None,
        **kwargs,
    ) -> None:
        """Fired when a graph node raises an error."""
        node_name = self._node_name_stack.get(run_id)

        self._emit(
            "agent.graph.node.errored",
            {
                "node_name": node_name,
                **_error_payload(error),
            },
            run_id=run_id,
            parent_run_id=parent_run_id,
            causality_type="node_error",
            metadata=kwargs.get("metadata"),
        )
        self._run_id_stack.pop(parent_run_id, None)
        self._node_name_stack.pop(run_id, None)

    # ------------------------------------------------------------------ #
    # LLM lifecycle                                                        #
    # ------------------------------------------------------------------ #

    def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: Sequence[str],
        *,
        run_id=None,
        parent_run_id=None,
        **kwargs,
    ) -> None:
        self._emit(
            "agent.model.started",
            {"serialized": serialized, "prompts": list(prompts)},
            run_id=run_id,
            parent_run_id=parent_run_id,
            causality_type="llm_start",
            metadata=kwargs.get("metadata"),
            context={"prompt_count": len(prompts), "context_fetched_at": _utc_now()},
        )

    def on_llm_end(
        self,
        response: Any,
        *,
        run_id=None,
        parent_run_id=None,
        **kwargs,
    ) -> None:
        self._emit(
            "agent.model.completed",
            {"response": _safe_model_dump(response)},
            run_id=run_id,
            parent_run_id=parent_run_id,
            causality_type="llm_end",
            metadata=kwargs.get("metadata"),
        )

    def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id=None,
        parent_run_id=None,
        **kwargs,
    ) -> None:
        self._emit(
            "agent.model.errored",
            _error_payload(error),
            run_id=run_id,
            parent_run_id=parent_run_id,
            causality_type="llm_error",
            metadata=kwargs.get("metadata"),
        )

    # ------------------------------------------------------------------ #
    # Tool lifecycle                                                       #
    # ------------------------------------------------------------------ #

    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        *,
        run_id=None,
        parent_run_id=None,
        **kwargs,
    ) -> None:
        self._emit(
            "agent.tool.started",
            {"serialized": serialized, "input": input_str},
            run_id=run_id,
            parent_run_id=parent_run_id,
            causality_type="tool_start",
            metadata=kwargs.get("metadata"),
            context={"context_fetched_at": _utc_now()},
        )

    def on_tool_end(
        self,
        output: Any,
        *,
        run_id=None,
        parent_run_id=None,
        **kwargs,
    ) -> None:
        self._emit(
            "agent.tool.completed",
            {"output": _safe_model_dump(output)},
            run_id=run_id,
            parent_run_id=parent_run_id,
            causality_type="tool_end",
            metadata=kwargs.get("metadata"),
        )

    def on_tool_error(
        self,
        error: BaseException,
        *,
        run_id=None,
        parent_run_id=None,
        **kwargs,
    ) -> None:
        self._emit(
            "agent.tool.errored",
            _error_payload(error),
            run_id=run_id,
            parent_run_id=parent_run_id,
            causality_type="tool_error",
            metadata=kwargs.get("metadata"),
        )

    # ------------------------------------------------------------------ #
    # Checkpoint / state-persistence lifecycle                            #
    # LangGraph saves / loads checkpoints via its Checkpointer.           #
    # We surface these so you can audit every state snapshot.            #
    # ------------------------------------------------------------------ #

    def on_checkpoint_start(
        self,
        *,
        run_id=None,
        parent_run_id=None,
        thread_id: str | None = None,
        checkpoint_ns: str | None = None,
        **kwargs,
    ) -> None:
        """Fired just before LangGraph writes a checkpoint."""
        self._emit(
            "agent.graph.checkpoint.started",
            {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
            },
            run_id=run_id,
            parent_run_id=parent_run_id,
            causality_type="checkpoint_start",
            metadata=kwargs.get("metadata"),
            context={"context_fetched_at": _utc_now()},
        )

    def on_checkpoint_end(
        self,
        checkpoint_id: str | None = None,
        *,
        run_id=None,
        parent_run_id=None,
        thread_id: str | None = None,
        checkpoint_ns: str | None = None,
        **kwargs,
    ) -> None:
        """Fired after LangGraph successfully persists a checkpoint."""
        self._emit(
            "agent.graph.checkpoint.completed",
            {
                "checkpoint_id": checkpoint_id,
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
            },
            run_id=run_id,
            parent_run_id=parent_run_id,
            causality_type="checkpoint_end",
            metadata=kwargs.get("metadata"),
        )

    # ------------------------------------------------------------------ #
    # Subgraph lifecycle                                                  #
    # Subgraphs appear as nested on_chain_* calls; we detect them via     #
    # the serialized graph id and emit dedicated subgraph events.         #
    # ------------------------------------------------------------------ #

    def on_subgraph_start(
        self,
        serialized: dict[str, Any],
        inputs: dict[str, Any],
        *,
        run_id=None,
        parent_run_id=None,
        **kwargs,
    ) -> None:
        """Fired when a nested subgraph begins execution."""
        self._run_id_stack[parent_run_id] = run_id
        graph_name = _graph_name(serialized)

        self._emit(
            "agent.graph.subgraph.started",
            {
                "subgraph_name": graph_name,
                "inputs": _safe_state(inputs),
            },
            run_id=run_id,
            parent_run_id=parent_run_id,
            causality_type="subgraph_start",
            metadata=kwargs.get("metadata"),
            context={
                "subgraph_name": graph_name,
                "context_fetched_at": _utc_now(),
            },
        )

    def on_subgraph_end(
        self,
        outputs: dict[str, Any],
        *,
        run_id=None,
        parent_run_id=None,
        **kwargs,
    ) -> None:
        """Fired when a nested subgraph completes successfully."""
        self._emit(
            "agent.graph.subgraph.completed",
            {"outputs": _safe_state(outputs)},
            run_id=run_id,
            parent_run_id=parent_run_id,
            causality_type="subgraph_end",
            metadata=kwargs.get("metadata"),
        )
        self._run_id_stack.pop(parent_run_id, None)


# ------------------------------------------------------------------ #
# Public factory                                                      #
# ------------------------------------------------------------------ #

def instrument_langgraph(client) -> BlocklogLangGraphCallbackHandler:
    """Return a configured :class:`BlocklogLangGraphCallbackHandler`.

    Attach the returned handler to every graph invocation::

        handler = instrument_langgraph(client)
        result = graph.invoke(state, config={"callbacks": [handler]})
    """
    return BlocklogLangGraphCallbackHandler(client)


# ------------------------------------------------------------------ #
# Private utilities                                                   #
# ------------------------------------------------------------------ #

def _graph_name(serialized: dict[str, Any]) -> str:
    """Extract a human-readable graph name from LangGraph's serialized dict."""
    return (
        serialized.get("name")
        or serialized.get("id", ["unknown"])[-1]
        or "unknown_graph"
    )


def _node_name(serialized: dict[str, Any], kwargs: dict[str, Any]) -> str:
    """Extract the node name, preferring kwargs['name'] set by LangGraph."""
    return (
        kwargs.get("name")
        or serialized.get("name")
        or serialized.get("id", ["unknown_node"])[-1]
        or "unknown_node"
    )


def _is_graph(serialized: dict[str, Any]) -> bool:
    """Heuristic: LangGraph sets the graph type in the serialized id list."""
    ids = serialized.get("id", [])
    return any("graph" in str(part).lower() for part in ids)


def _safe_state(value: Any) -> Any:
    """Safely serialise a LangGraph state dict (which may hold Pydantic models)."""
    if isinstance(value, dict):
        return {k: _safe_model_dump(v) for k, v in value.items()}
    return _safe_model_dump(value)


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


def _agent_metadata(
    *,
    framework: str,
    parent_run_id=None,
    extra: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "framework": framework,
        "captured_at": _utc_now(),
        "parent_run_id": str(parent_run_id) if parent_run_id else None,
    }
    if context:
        metadata.update(context)
    if extra:
        metadata.update(extra)
    return metadata