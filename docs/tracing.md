# Tracing

Tracing tracks an AI agent's entire execution flow, including nested operations and tool invocations.

## Trace Lifecycle

When you use the `@blocklog.agent` decorator on a function or class, Blocklog automatically opens an `agent_session`. 
This session generates a `trace_id` and a `session_id`.

The lifecycle consists of:
1. `AGENT_START`: Emitted when the decorated function begins, including agent name, version, and metadata.
2. `AGENT_COMPLETE`: Emitted when the function exits cleanly, capturing the total duration.
3. `AGENT_ERROR`: Emitted if the function throws an exception, capturing the error type, message, and traceback.

## Parent-Child Relationships & Correlation

Any tool calls decorated with `@blocklog.tool` or decisions made with `blocklog.decision()` within the agent's function will automatically detect the active `agent_session` via context variables.

They will pull the `trace_id` and `session_id` from this context, stamping every subsequent event with the same correlation IDs. This allows the backend to reconstruct a precise causal graph of execution.

## Event Capture

Blocklog buffers high-frequency tracing events locally. 
- A `TOOL_CALL` event captures `inputs` (arguments), `output` (return value), `duration_ms`, and `status`.
- Large objects are safely truncated via a best-effort `_safe_repr` to prevent payload bloat.
- Events are enqueued in an `EventBuffer` and flushed efficiently.
