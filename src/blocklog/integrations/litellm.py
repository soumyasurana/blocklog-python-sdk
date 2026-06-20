from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

try:
    from litellm.integrations.custom_logger import CustomLogger
except ImportError:  # pragma: no cover - allow use without litellm installed
    class CustomLogger:  # type: ignore[no-redef]
        """Fallback no-op base so this module is importable without litellm."""


class BlocklogLiteLLMCallbackHandler(CustomLogger):
    """Blocklog callback handler for LiteLLM.

    Hooks into LiteLLM's ``CustomLogger`` interface to emit Blocklog events
    for every completion call — sync, async, streaming, pre-call, and post-call.

    Usage::

        import litellm
        from blocklog.integrations.litellm import instrument_litellm

        handler = instrument_litellm(client)

        # Register globally — covers every litellm.completion / acompletion call
        litellm.callbacks = [handler]

        # Or append alongside existing callbacks
        litellm.callbacks += [handler]
    """

    def __init__(self, client, *, source: str = "litellm") -> None:
        self.client = client
        self.source = source

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _emit(
        self,
        event_name: str,
        payload: dict[str, Any],
        *,
        causality_type: str,
        span_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.client.event(
            event_name,
            payload,
            source=self.source,
            span_id=span_id,
            causality_type=causality_type,
            agent_metadata=_agent_metadata(extra=metadata),
        )

    def _span_id_from_kwargs(self, kwargs: dict[str, Any]) -> str:
        """Derive a stable span ID from the call ID embedded in kwargs.

        LiteLLM stores the completion id in ``kwargs["litellm_call_id"]`` for
        most call paths, and also exposes it on the response object.  We fall
        back to a fresh UUID only if neither is present so span continuity is
        preserved across pre/post/success hooks for the same request.
        """
        call_id = (
            kwargs.get("litellm_call_id")
            or kwargs.get("id")
        )
        return str(call_id) if call_id else str(uuid.uuid4())

    def _base_request_payload(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        """Extract the stable request fields available in every hook."""
        litellm_params = kwargs.get("litellm_params") or {}
        return {
            "model": kwargs.get("model"),
            "messages": _safe_value(kwargs.get("messages", [])),
            "call_type": kwargs.get("call_type"),
            "stream": bool(kwargs.get("stream", False)),
            "cache_hit": bool(kwargs.get("cache_hit", False)),
            "metadata": _safe_value(litellm_params.get("metadata")),
            "litellm_call_id": kwargs.get("litellm_call_id"),
        }

    def _usage_from_response(self, response_obj: Any) -> dict[str, Any] | None:
        """Pull token usage from the response object in a version-safe way."""
        usage = getattr(response_obj, "usage", None)
        if usage is None:
            return None
        if hasattr(usage, "model_dump"):
            return usage.model_dump()
        if hasattr(usage, "dict"):
            return usage.dict()
        if isinstance(usage, dict):
            return usage
        return None

    def _duration_s(self, start_time: Any, end_time: Any) -> float | None:
        """Return elapsed seconds, handling datetime objects and None."""
        try:
            if start_time is None or end_time is None:
                return None
            delta = end_time - start_time
            return delta.total_seconds()
        except Exception:
            return None

    # ------------------------------------------------------------------ #
    # Pre-call hook                                                        #
    # Fired synchronously before the HTTP request is dispatched.         #
    # ------------------------------------------------------------------ #

    def log_pre_api_call(
        self,
        model: str,
        messages: list[dict[str, Any]],
        kwargs: dict[str, Any],
    ) -> None:
        """Fired before the LLM API call is made (sync path)."""
        span_id = self._span_id_from_kwargs(kwargs)
        self._emit(
            "agent.model.pre_call",
            {
                "model": model,
                "messages": _safe_value(messages),
                "stream": bool(kwargs.get("stream", False)),
                "litellm_call_id": kwargs.get("litellm_call_id"),
                "context_fetched_at": _utc_now(),
            },
            causality_type="llm_pre_call",
            span_id=span_id,
            metadata=_extract_user_metadata(kwargs),
        )

    # ------------------------------------------------------------------ #
    # Post-call hook                                                       #
    # Fired after the response is received, before success/failure        #
    # callbacks.  Carries the raw response for low-level inspection.     #
    # ------------------------------------------------------------------ #

    def log_post_api_call(
        self,
        kwargs: dict[str, Any],
        response_obj: Any,
        start_time: Any,
        end_time: Any,
    ) -> None:
        """Fired after the API responds (sync path), before success/failure split."""
        span_id = self._span_id_from_kwargs(kwargs)
        self._emit(
            "agent.model.post_call",
            {
                **self._base_request_payload(kwargs),
                "response": _safe_model_dump(response_obj),
                "duration_s": self._duration_s(start_time, end_time),
            },
            causality_type="llm_post_call",
            span_id=span_id,
            metadata=_extract_user_metadata(kwargs),
        )

    # ------------------------------------------------------------------ #
    # Stream chunk hook                                                    #
    # ------------------------------------------------------------------ #

    def log_stream_event(
        self,
        kwargs: dict[str, Any],
        response_obj: Any,
        start_time: Any,
        end_time: Any,
    ) -> None:
        """Fired for each streamed chunk (sync streaming path)."""
        span_id = self._span_id_from_kwargs(kwargs)
        self._emit(
            "agent.model.stream_chunk",
            {
                "model": kwargs.get("model"),
                "chunk": _safe_model_dump(response_obj),
                "litellm_call_id": kwargs.get("litellm_call_id"),
            },
            causality_type="llm_stream_chunk",
            span_id=span_id,
        )

    # ------------------------------------------------------------------ #
    # Success hooks (sync + async)                                         #
    # ------------------------------------------------------------------ #

    def log_success_event(
        self,
        kwargs: dict[str, Any],
        response_obj: Any,
        start_time: Any,
        end_time: Any,
    ) -> None:
        """Fired when a sync completion call succeeds."""
        self._handle_success(kwargs, response_obj, start_time, end_time)

    async def async_log_success_event(
        self,
        kwargs: dict[str, Any],
        response_obj: Any,
        start_time: Any,
        end_time: Any,
    ) -> None:
        """Fired when an async completion call succeeds (acompletion / async streaming)."""
        self._handle_success(kwargs, response_obj, start_time, end_time)

    def _handle_success(
        self,
        kwargs: dict[str, Any],
        response_obj: Any,
        start_time: Any,
        end_time: Any,
    ) -> None:
        span_id = self._span_id_from_kwargs(kwargs)
        response_dump = _safe_model_dump(response_obj)

        # Surface cost and usage at the top level for easy querying
        usage = self._usage_from_response(response_obj)
        response_cost = kwargs.get("response_cost")

        self._emit(
            "agent.model.completed",
            {
                **self._base_request_payload(kwargs),
                "response": response_dump,
                "usage": usage,
                "response_cost": response_cost,
                "duration_s": self._duration_s(start_time, end_time),
                "end_time": end_time.isoformat() if hasattr(end_time, "isoformat") else str(end_time),
            },
            causality_type="llm_end",
            span_id=span_id,
            metadata=_extract_user_metadata(kwargs),
        )

    # ------------------------------------------------------------------ #
    # Failure hooks (sync + async)                                         #
    # ------------------------------------------------------------------ #

    def log_failure_event(
        self,
        kwargs: dict[str, Any],
        response_obj: Any,
        start_time: Any,
        end_time: Any,
    ) -> None:
        """Fired when a sync completion call fails."""
        self._handle_failure(kwargs, response_obj, start_time, end_time)

    async def async_log_failure_event(
        self,
        kwargs: dict[str, Any],
        response_obj: Any,
        start_time: Any,
        end_time: Any,
    ) -> None:
        """Fired when an async completion call fails."""
        self._handle_failure(kwargs, response_obj, start_time, end_time)

    def _handle_failure(
        self,
        kwargs: dict[str, Any],
        response_obj: Any,
        start_time: Any,
        end_time: Any,
    ) -> None:
        span_id = self._span_id_from_kwargs(kwargs)

        # LiteLLM stores the caught exception in kwargs["exception"]
        exception: BaseException | None = kwargs.get("exception")

        self._emit(
            "agent.model.errored",
            {
                **self._base_request_payload(kwargs),
                "response": _safe_model_dump(response_obj),
                "error_type": type(exception).__name__ if exception else None,
                "error_message": str(exception) if exception else None,
                "duration_s": self._duration_s(start_time, end_time),
            },
            causality_type="llm_error",
            span_id=span_id,
            metadata=_extract_user_metadata(kwargs),
        )


# ------------------------------------------------------------------ #
# Public factory                                                      #
# ------------------------------------------------------------------ #

def instrument_litellm(client, *, source: str = "litellm") -> BlocklogLiteLLMCallbackHandler:
    """Return a configured :class:`BlocklogLiteLLMCallbackHandler`.

    Register the returned handler before making any litellm calls::

        import litellm
        from blocklog.integrations.litellm import instrument_litellm

        handler = instrument_litellm(client)
        litellm.callbacks = [handler]

    To append without replacing existing callbacks::

        litellm.callbacks += [handler]
    """
    return BlocklogLiteLLMCallbackHandler(client, source=source)


# ------------------------------------------------------------------ #
# Private utilities                                                   #
# ------------------------------------------------------------------ #

def _safe_model_dump(value: Any) -> Any:
    """Safely serialise LiteLLM response objects (Pydantic v1 + v2)."""
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    if isinstance(value, list):
        return [_safe_model_dump(v) for v in value]
    if isinstance(value, dict):
        return {k: _safe_model_dump(v) for k, v in value.items()}
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _safe_value(value: Any) -> Any:
    """Alias kept for readability; delegates to _safe_model_dump."""
    return _safe_model_dump(value)


def _extract_user_metadata(kwargs: dict[str, Any]) -> dict[str, Any] | None:
    """Pull the user-supplied metadata dict out of litellm_params, if present."""
    litellm_params = kwargs.get("litellm_params") or {}
    meta = litellm_params.get("metadata")
    if meta and isinstance(meta, dict):
        return meta
    return None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _agent_metadata(
    *,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "framework": "litellm",
        "captured_at": _utc_now(),
    }
    if extra:
        metadata.update(extra)
    return metadata