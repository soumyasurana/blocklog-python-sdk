from __future__ import annotations

import contextvars
import inspect
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable

# In-process contextvar for linking a streamed/nested OpenAI call to whatever
# Blocklog span is "current" when it starts. This is separate from
# blocklog.context.vars (which carries trace_id/session_id/workflow_id) —
# this one only tracks span_id parentage for causality_type chains.
_current_span_id: "contextvars.ContextVar[uuid.UUID | None]" = contextvars.ContextVar(
    "blocklog_openai_span_id", default=None
)


class BlocklogOpenAIInstrumentation:
    """Patches the OpenAI SDK so chat completions (and, where available,
    the Responses API) emit Blocklog events — sync, async, streaming, or not.

    openai-python has no callback/handler system like LangChain's, so
    instrumentation works by wrapping `create` on the SDK's resource
    classes (global instrumentation) or on a specific client instance
    (scoped instrumentation), rather than registering a handler.
    """

    def __init__(self, client, *, source: str = "openai") -> None:
        self.client = client
        self.source = source

    # ---------- public API ----------

    def instrument_globally(self) -> None:
        """Patch the OpenAI SDK's resource classes directly, so every
        `OpenAI()` / `AsyncOpenAI()` instance created anywhere in the
        process — including ones already constructed — is instrumented.
        This mirrors `instrument_langchain(client)` / `instrument_langgraph(client)`,
        which also don't require you to hand in an SDK instance.
        """
        patched_any = False

        try:
            from openai.resources.chat.completions import AsyncCompletions, Completions

            self._patch_class_method(Completions, "create", event_prefix="agent.model")
            self._patch_class_method(AsyncCompletions, "create", event_prefix="agent.model")
            patched_any = True
        except ImportError:
            pass

        try:
            from openai.resources.responses import AsyncResponses, Responses

            self._patch_class_method(Responses, "create", event_prefix="agent.model")
            self._patch_class_method(AsyncResponses, "create", event_prefix="agent.model")
            patched_any = True
        except ImportError:
            pass

        if not patched_any:
            raise ImportError(
                "Could not import any OpenAI SDK resource classes. Is `openai` "
                "installed? (`pip install openai`). Note: very old (<1.0) "
                "versions of the SDK are not supported."
            )

    def instrument_instance(self, openai_client: Any) -> Any:
        """Patch only this specific client instance (e.g. when you want to
        log calls made through one client but not another). Returns the
        same instance for chaining.
        """
        self._patch_instance_endpoint(openai_client, ("chat", "completions"), event_prefix="agent.model")
        self._patch_instance_endpoint(openai_client, ("responses",), event_prefix="agent.model")
        return openai_client

    # ---------- patching: class-level (global) ----------

    def _patch_class_method(self, cls: type, method_name: str, *, event_prefix: str) -> None:
        original = getattr(cls, method_name, None)
        if original is None:
            return
        if getattr(original, "_blocklog_wrapped", False):
            return  # already instrumented, avoid double-wrapping

        if _is_coroutine_function(original):
            wrapped = self._wrap_async(original, event_prefix=event_prefix)
        else:
            wrapped = self._wrap_sync(original, event_prefix=event_prefix)

        wrapped._blocklog_wrapped = True  # type: ignore[attr-defined]
        setattr(cls, method_name, wrapped)

    # ---------- patching: instance-level (scoped) ----------

    def _patch_instance_endpoint(self, openai_client: Any, path: tuple[str, ...], *, event_prefix: str) -> None:
        target = openai_client
        for attr in path:
            target = getattr(target, attr, None)
            if target is None:
                return  # endpoint not present on this client/SDK version, skip

        if not hasattr(target, "create"):
            return

        original_create = target.create
        if getattr(original_create, "_blocklog_wrapped", False):
            return

        if _is_coroutine_function(original_create):
            wrapped = self._wrap_async(original_create, event_prefix=event_prefix)
        else:
            wrapped = self._wrap_sync(original_create, event_prefix=event_prefix)

        wrapped._blocklog_wrapped = True  # type: ignore[attr-defined]
        target.create = wrapped

    # ---------- the actual wrapping logic (shared by both patch modes) ----------
    #
    # Note: when `original` is an unbound class method (global patch), calling
    # it as `wrapped(*args, **kwargs)` works unmodified — Python's descriptor
    # protocol passes the resource instance as args[0] automatically when the
    # wrapper is looked up on the class. When `original` is an already-bound
    # method (instance patch), args never includes `self`. Either way,
    # `original(*args, **kwargs)` forwards correctly.

    def _wrap_sync(self, original_create: Callable, *, event_prefix: str) -> Callable:
        def wrapped(*args, **kwargs):
            run_id = uuid.uuid4()
            parent_run_id = _current_span_id.get()
            stream = bool(kwargs.get("stream", False))

            self._emit_start(event_prefix, kwargs, run_id=run_id, parent_run_id=parent_run_id)
            token = _current_span_id.set(run_id)
            start = time.monotonic()

            try:
                result = original_create(*args, **kwargs)
            except BaseException as error:
                _current_span_id.reset(token)
                self._emit_error(event_prefix, error, run_id=run_id, parent_run_id=parent_run_id)
                raise

            if stream:
                return self._consume_sync_stream(
                    result, run_id=run_id, parent_run_id=parent_run_id, start=start,
                    token=token, event_prefix=event_prefix,
                )

            _current_span_id.reset(token)
            self._emit_end(
                event_prefix, result, run_id=run_id, parent_run_id=parent_run_id,
                duration_s=time.monotonic() - start,
            )
            return result

        return wrapped

    def _wrap_async(self, original_create: Callable, *, event_prefix: str) -> Callable:
        async def wrapped(*args, **kwargs):
            run_id = uuid.uuid4()
            parent_run_id = _current_span_id.get()
            stream = bool(kwargs.get("stream", False))

            self._emit_start(event_prefix, kwargs, run_id=run_id, parent_run_id=parent_run_id)
            token = _current_span_id.set(run_id)
            start = time.monotonic()

            try:
                result = await original_create(*args, **kwargs)
            except BaseException as error:
                _current_span_id.reset(token)
                self._emit_error(event_prefix, error, run_id=run_id, parent_run_id=parent_run_id)
                raise

            if stream:
                return self._consume_async_stream(
                    result, run_id=run_id, parent_run_id=parent_run_id, start=start,
                    token=token, event_prefix=event_prefix,
                )

            _current_span_id.reset(token)
            self._emit_end(
                event_prefix, result, run_id=run_id, parent_run_id=parent_run_id,
                duration_s=time.monotonic() - start,
            )
            return result

        return wrapped

    # ---------- streaming ----------

    def _consume_sync_stream(self, stream_obj, *, run_id, parent_run_id, start, token, event_prefix):
        chunks: list[Any] = []
        try:
            for chunk in stream_obj:
                chunks.append(chunk)
                yield chunk
        except BaseException as error:
            _current_span_id.reset(token)
            self._emit_error(event_prefix, error, run_id=run_id, parent_run_id=parent_run_id)
            raise
        else:
            _current_span_id.reset(token)
            self._emit_end(
                event_prefix, _aggregate_stream_chunks(chunks), run_id=run_id,
                parent_run_id=parent_run_id, duration_s=time.monotonic() - start, streamed=True,
            )

    async def _consume_async_stream(self, stream_obj, *, run_id, parent_run_id, start, token, event_prefix):
        chunks: list[Any] = []
        try:
            async for chunk in stream_obj:
                chunks.append(chunk)
                yield chunk
        except BaseException as error:
            _current_span_id.reset(token)
            self._emit_error(event_prefix, error, run_id=run_id, parent_run_id=parent_run_id)
            raise
        else:
            _current_span_id.reset(token)
            self._emit_end(
                event_prefix, _aggregate_stream_chunks(chunks), run_id=run_id,
                parent_run_id=parent_run_id, duration_s=time.monotonic() - start, streamed=True,
            )

    # ---------- event emission ----------
    #
    # client.event() pulls trace_id/session_id/workflow_id/agent_id/source
    # from blocklog.context.vars.get_context() automatically — we only need
    # to pass span_id, causality_type, and agent_metadata ourselves.

    def _emit_start(self, event_prefix: str, kwargs: dict[str, Any], *, run_id, parent_run_id) -> None:
        messages = kwargs.get("messages") or kwargs.get("input")
        request = {k: v for k, v in kwargs.items() if k not in ("messages", "input")}
        self.client.event(
            f"{event_prefix}.started",
            {
                "model": kwargs.get("model"),
                "messages": _safe_model_dump(messages),
                "request": _safe_model_dump(request),
                "parent_run_id": str(parent_run_id) if parent_run_id else None,
            },
            source=self.source,
            span_id=str(run_id),
            causality_type="llm_start",
            agent_metadata=_agent_metadata(parent_run_id=parent_run_id),
        )

    def _emit_end(self, event_prefix: str, response: Any, *, run_id, parent_run_id, duration_s: float, streamed: bool = False) -> None:
        dumped = _safe_model_dump(response)
        usage = dumped.get("usage") if isinstance(dumped, dict) else None
        self.client.event(
            f"{event_prefix}.completed",
            {
                "response": dumped,
                "usage": usage,
                "duration_s": duration_s,
                "streamed": streamed,
                "parent_run_id": str(parent_run_id) if parent_run_id else None,
            },
            source=self.source,
            span_id=str(run_id),
            causality_type="llm_end",
            agent_metadata=_agent_metadata(parent_run_id=parent_run_id),
        )

    def _emit_error(self, event_prefix: str, error: BaseException, *, run_id, parent_run_id) -> None:
        self.client.event(
            f"{event_prefix}.errored",
            {**_error_payload(error), "parent_run_id": str(parent_run_id) if parent_run_id else None},
            source=self.source,
            span_id=str(run_id),
            causality_type="llm_error",
            agent_metadata=_agent_metadata(parent_run_id=parent_run_id),
        )


def instrument_openai(client, openai_client: Any | None = None, *, source: str = "openai") -> Any:
    """Instrument the OpenAI SDK so chat completions / responses calls emit
    Blocklog events.

    With no `openai_client` argument (the common case — matches
    `client.instrument_langchain()`), this patches the SDK's resource
    classes directly, so every `OpenAI()` / `AsyncOpenAI()` (and
    `AzureOpenAI()`, which subclasses it) instance is instrumented
    automatically, including ones already constructed.

    Pass a specific `openai_client` instance if you only want that one
    client logged (e.g. in tests, or when only some of several clients
    in your process should be tracked). Returns that instance for chaining.
    """
    instrumentation = BlocklogOpenAIInstrumentation(client, source=source)
    if openai_client is not None:
        return instrumentation.instrument_instance(openai_client)
    instrumentation.instrument_globally()
    return None


# ---------- helpers ----------

def _safe_model_dump(value: Any) -> Any:
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


def _error_payload(error: BaseException) -> dict[str, Any]:
    return {
        "error_type": type(error).__name__,
        "error_message": str(error),
    }


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _agent_metadata(*, parent_run_id=None, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    metadata = {
        "framework": "openai",
        "captured_at": _utc_now(),
        "parent_run_id": str(parent_run_id) if parent_run_id else None,
    }
    if extra:
        metadata.update(extra)
    return metadata


def _is_coroutine_function(fn: Callable) -> bool:
    return inspect.iscoroutinefunction(fn) or inspect.iscoroutinefunction(getattr(fn, "__wrapped__", None))


def _aggregate_stream_chunks(chunks: list[Any]) -> dict[str, Any]:
    """Best-effort merge of streamed ChatCompletionChunk deltas into one
    summary dict so the completed event has real content instead of a list
    of fragments. Falls back to the raw dumped chunks if the shape isn't
    recognized (e.g. Responses API streaming events).
    """
    if not chunks:
        return {"chunks": []}

    dumped = [_safe_model_dump(c) for c in chunks]

    if all(isinstance(d, dict) and "choices" in d for d in dumped):
        merged: dict[int, dict[str, Any]] = {}
        model = dumped[0].get("model")
        for d in dumped:
            for choice in d.get("choices", []):
                idx = choice.get("index", 0)
                slot = merged.setdefault(idx, {"index": idx, "content": "", "tool_calls": None, "finish_reason": None})
                delta = choice.get("delta") or {}
                if delta.get("content"):
                    slot["content"] += delta["content"]
                if delta.get("tool_calls"):
                    slot["tool_calls"] = delta["tool_calls"]  # last write wins; refine if you need a full merge
                if choice.get("finish_reason"):
                    slot["finish_reason"] = choice["finish_reason"]
        return {
            "model": model,
            "choices": [merged[i] for i in sorted(merged)],
            "chunk_count": len(dumped),
        }

    return {"chunks": dumped[-50:], "chunk_count": len(dumped)}