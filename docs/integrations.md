# Integrations

Blocklog comes with built-in instrumentation for LangChain, LangGraph, the OpenAI SDK, and LiteLLM. Each integration wires into the framework's native execution model and emits structured events to the Blocklog ingest API — covering LLM calls, tool use, chain and graph lifecycle, streaming, and errors.

---

## LangChain

Enable LangChain instrumentation with a single call on your client:

```python
import blocklog

client = blocklog.init(api_key="blk_...")
handler = client.instrument_langchain()
```

This returns a `BlocklogLangChainCallbackHandler` that you can attach to any chain, agent, or LLM:

```python
chain.invoke(inputs, config={"callbacks": [handler]})
```

### Events emitted

| Event | Causality type | Fired when |
|---|---|---|
| `agent.chain.started` | `chain_start` | A chain begins; includes `inputs` and `input_keys` |
| `agent.chain.completed` | `chain_end` | A chain finishes successfully; includes `outputs` |
| `agent.chain.errored` | `chain_error` | A chain raises an exception |
| `agent.model.started` | `llm_start` | An LLM call begins; includes serialized model info and `prompts` |
| `agent.model.completed` | `llm_end` | An LLM call finishes; includes the full response |
| `agent.model.errored` | `llm_error` | An LLM call raises an exception |
| `agent.tool.started` | `tool_start` | A tool begins execution; includes the raw `input` string |
| `agent.tool.completed` | `tool_end` | A tool finishes; includes `output` |
| `agent.tool.errored` | `tool_error` | A tool raises an exception |

Every event carries a `span_id` (derived from `run_id`), `parent_run_id` for causality linking, and an `agent_metadata` block containing `framework`, `captured_at`, and any LangChain-provided `metadata`.

---

## LangGraph

Enable LangGraph instrumentation the same way:

```python
import blocklog

client = blocklog.init(api_key="blk_...")
handler = client.instrument_langgraph()
```

Attach the handler when invoking a compiled graph:

```python
result = graph.invoke(state, config={"callbacks": [handler]})

# Or via RunnableConfig
from langchain_core.runnables import RunnableConfig
result = graph.invoke(state, config=RunnableConfig(callbacks=[handler]))
```

The LangGraph handler extends the LangChain handler pattern with graph-native event families. Because LangGraph routes both top-level graphs and individual nodes through `on_chain_*`, the handler inspects the serialized payload to distinguish them and emits the appropriate event.

### Events emitted

**Graph lifecycle**

| Event | Causality type | Fired when |
|---|---|---|
| `agent.graph.started` | `graph_start` | The top-level `CompiledGraph` begins; includes `graph_name`, `inputs`, and `input_keys` |
| `agent.graph.completed` | `graph_end` | The graph finishes successfully; includes `outputs` |
| `agent.graph.errored` | `graph_error` | The graph raises an unhandled exception |

**Node lifecycle**

| Event | Causality type | Fired when |
|---|---|---|
| `agent.graph.node.started` | `node_start` | A node begins; includes `node_name` and `inputs` |
| `agent.graph.node.completed` | `node_end` | A node finishes; includes `node_name` and `outputs` |
| `agent.graph.node.errored` | `node_error` | A node raises an exception; includes `node_name` and error details |

**Subgraph lifecycle**

| Event | Causality type | Fired when |
|---|---|---|
| `agent.graph.subgraph.started` | `subgraph_start` | A nested subgraph begins; includes `subgraph_name` and `inputs` |
| `agent.graph.subgraph.completed` | `subgraph_end` | A nested subgraph finishes; includes `outputs` |

**Checkpoint lifecycle**

| Event | Causality type | Fired when |
|---|---|---|
| `agent.graph.checkpoint.started` | `checkpoint_start` | LangGraph is about to write a checkpoint; includes `thread_id` and `checkpoint_ns` |
| `agent.graph.checkpoint.completed` | `checkpoint_end` | A checkpoint is successfully persisted; includes `checkpoint_id`, `thread_id`, and `checkpoint_ns` |

All LLM and tool events (`agent.model.*`, `agent.tool.*`) are also emitted for calls made inside nodes, identical to the LangChain integration.

The handler maintains a `_node_name_stack` keyed by `run_id` so that node names are correctly attributed on completion and error callbacks, which LangGraph does not re-supply. State dicts (which often contain Pydantic models) are safely serialized before emission.

---

## OpenAI SDK

Enable OpenAI instrumentation on your Blocklog client:

```python
import blocklog

client = blocklog.init(api_key="blk_...")
client.instrument_openai_agents()
```

Because the OpenAI Python SDK has no callback system, instrumentation works by monkey-patching the `create` method on the SDK's resource classes directly. This means **every** `OpenAI()`, `AsyncOpenAI()`, and `AzureOpenAI()` instance in the process — including ones already constructed — is instrumented automatically.

To instrument only a specific client instance instead:

```python
import openai
import blocklog
from blocklog.integrations.openai_agents import instrument_openai

blocklog_client = blocklog.init(api_key="blk_...")
openai_client = openai.OpenAI(api_key="...")

instrument_openai(blocklog_client, openai_client=openai_client)
```

### Events emitted

| Event | Causality type | Fired when |
|---|---|---|
| `agent.model.started` | `llm_start` | A `chat.completions.create` or `responses.create` call begins; includes `model`, `messages`, and remaining request parameters |
| `agent.model.completed` | `llm_end` | The call finishes; includes the full response, `usage`, `duration_s`, and `streamed` flag |
| `agent.model.errored` | `llm_error` | The call raises an exception |

### Streaming

Streaming responses are handled transparently for both sync and async clients. The handler wraps the returned generator/async-generator, re-yields each chunk to the caller unmodified, and emits `agent.model.completed` only after the stream is fully consumed. The completion payload aggregates streamed `ChatCompletionChunk` deltas into a single merged response object (with reconstructed `content`, `tool_calls`, and `finish_reason` per choice index) so you get a coherent record without storing every fragment.

### Async support

All async `create` methods (`AsyncCompletions`, `AsyncResponses`) are wrapped with an async-native path, including async streaming via `async for`. Sync and async variants are detected automatically via `inspect.iscoroutinefunction`.

### Span propagation

The handler uses a `contextvars.ContextVar` (`blocklog_openai_span_id`) to propagate `span_id` across nested or concurrent calls within the same async context, so causality chains are preserved even when multiple completions are in-flight simultaneously.

---

## LiteLLM

Enable LiteLLM instrumentation on your Blocklog client:

```python
import blocklog

client = blocklog.init(api_key="blk_...")
handler = client.instrument_litellm()
```

Unlike the OpenAI integration, LiteLLM has a first-class `CustomLogger` base class. The handler subclasses it and registers via `litellm.callbacks` — which is exactly how every other LiteLLM observability tool integrates, with no monkey-patching required.

Register the returned handler before making any calls:

```python
import litellm

# Replace all existing callbacks
litellm.callbacks = [handler]

# Or append alongside existing callbacks
litellm.callbacks += [handler]
```

### Events emitted

| Event | Causality type | Fired when |
|---|---|---|
| `agent.model.pre_call` | `llm_pre_call` | Before the HTTP request is dispatched; includes `model`, `messages`, `stream`, and `litellm_call_id` |
| `agent.model.post_call` | `llm_post_call` | After the API responds, before the success/failure split; includes the full request fields, raw `response`, and `duration_s` |
| `agent.model.stream_chunk` | `llm_stream_chunk` | For each individual chunk on the sync streaming path; includes `model`, `chunk`, and `litellm_call_id` |
| `agent.model.completed` | `llm_end` | A call finishes successfully (sync or async); includes `response`, `usage`, `response_cost`, `duration_s`, `stream`, and `cache_hit` |
| `agent.model.errored` | `llm_error` | A call fails (sync or async); includes `error_type`, `error_message`, and `duration_s` |

Every event carries a `span_id` derived from `litellm_call_id` (stamped onto kwargs by LiteLLM before any hook fires), so pre-call, post-call, and success/failure events for the same request share a consistent span ID without any external state.

### Cost and usage

LiteLLM calculates token usage and cost automatically. Both are promoted to the top level of `agent.model.completed` payloads — `usage` (with `prompt_tokens`, `completion_tokens`, `total_tokens`) and `response_cost` (in USD) — so they're queryable directly without unwrapping the full response object.

### Async support

`log_success_event` / `log_failure_event` handle sync calls; `async_log_success_event` / `async_log_failure_event` handle `acompletion` and async streaming. Both paths delegate to shared `_handle_success` / `_handle_failure` methods so event payloads are identical regardless of execution mode.

### User metadata passthrough

Any `metadata` dict passed via `litellm_params` is forwarded into the `agent_metadata` block on every event, so caller-defined context (tenant IDs, request tags, trace labels) arrives in Blocklog alongside the framework fields.

---

## Common behaviour across all integrations

- **Concurrent run safety.** LangChain and LangGraph handlers key internal state by `run_id` (a UUID per invocation); the LiteLLM handler uses `litellm_call_id`; the OpenAI handler uses a `contextvars.ContextVar`. In all cases, nested or parallel runs never clobber each other.
- **Context inheritance.** `trace_id`, `session_id`, `workflow_id`, and `agent_id` are pulled automatically from the active Blocklog context (`blocklog.context.vars`) — no manual threading required.
- **Safe serialization.** Pydantic v1 (`.dict()`) and v2 (`.model_dump()`) models, plain Python types, and arbitrary objects are all handled; unknown types fall back to `str()`.
- **Error events always fire.** On any exception, an `errored` event is emitted before the exception propagates, so failures are never silently dropped from your audit trail.
- **No double-wrapping.** The OpenAI patcher sets a `_blocklog_wrapped` sentinel flag so calling `instrument_openai_agents()` more than once is safe. For LiteLLM, registering the same handler instance twice via `litellm.callbacks` is safe since Python list identity prevents duplicate emissions.