# Core Concepts

Understanding how Blocklog structures data is key to utilizing the SDK effectively.

## Decisions
A **Decision** is the highest-level primitive in Blocklog. It represents a concrete action taken by an AI agent (e.g., executing a trade, denying a loan, generating an email). A decision is tracked via the `blocklog.decision()` context manager, capturing:
- `type` and `asset`
- Structured `inputs` (what the model knew)
- Structured `outputs` (what the model did)
- Approvals (`d.request_approval()`)
- Automatic completion or error handling on exceptions.

## Traces and Context
When you use `@blocklog.agent`, Blocklog automatically creates a **Session Context**. This context maintains a `trace_id` and a `session_id`. Any tools (`@blocklog.tool`) or decisions (`blocklog.decision`) invoked within the agent's execution flow automatically inherit this context, correlating them together in the Blocklog dashboard.

## Events
An **Event** is a low-level building block. Every time an agent starts (`AGENT_START`), a tool completes (`TOOL_CALL`), or a decision is formed (`DECISION_INPUT`, `DECISION_COMPLETE`), an Event is created. Events are buffered, optionally signed, and batched to the Blocklog backend.

## Managers
Managers like the `DecisionContext` provide a live handle to a resource. While inside a `with blocklog.decision(...) as d:` block, `d` is the manager instance. It handles dispatching events sequentially and committing the final record to the API.

## Transport Layer
Blocklog uses a `SyncTransport` built on `httpx` and features a `RetryPolicy` and `EventBuffer`. 
- **Buffering**: High-volume events (like tool traces) are batched.
- **Retries**: Automatic retries on transient failures.

## Signing
If initialized with a `signing_key` (Ed25519), Blocklog will cryptographically sign the payload of every event before transmitting it to the backend. This provides tamper-evident logs that can later be cryptographically verified using `blocklog.verify`.

## Middleware Hooks
You can add custom middleware to mutate or filter outgoing event payloads using `client.add_hook(hook_function)`. This is useful for PII redaction or adding custom environment metadata to every event.
