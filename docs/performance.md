# Performance & Behavior

The Blocklog Python SDK is built for high-throughput AI infrastructure. It minimizes performance overhead on your agents through batching, buffering, and retries.

## Event Buffering and Batching

To avoid degrading your application's performance with a high volume of HTTP requests, Blocklog uses an in-memory `EventBuffer`. 

- Every `TOOL_CALL`, `AGENT_START`, and `DECISION_INPUT` creates an `EventEnvelope`.
- These events are pushed to the `EventBuffer` locally.
- **Batch Behavior:** When the buffer reaches `batch_size` (default: `100`), the SDK automatically triggers a `.flush()`, sending the events in a single bulk `POST /logs/batch` request.
- **Flush Strategy:** Events are also flushed continuously based on the `flush_interval` (default: `2.0` seconds), ensuring events aren't held indefinitely if traffic is low.

## Retry Strategy

Blocklog ensures durability using a deterministic `RetryPolicy` wrapped around transport calls.

- **Max Retries:** 3 attempts.
- **Backoff:** Exponential backoff calculated as `base_delay * (2 ** attempt) + random() * 0.1`
- **Base Delay:** 0.25 seconds.
- A failure after 3 attempts will raise a `RuntimeError("retry failed")`.

## Signing Overhead

If you initialize Blocklog with a `signing_key` (an Ed25519 private key), the SDK will perform a cryptographic signature of the event payload (`pseudo_sign`) before adding it to the buffer. 

- This happens **locally** in memory.
- The `log_signature` field is injected.
- The performance overhead of Ed25519 signing is negligible, typically in the sub-millisecond range per event, but can slightly increase CPU utilization in extreme high-throughput scenarios.

## Serialization Behavior

When you pass complex objects to `@blocklog.tool` or `d.record_input()`, the SDK invokes a `_safe_repr` truncation.

- Standard types (`str`, `int`, `float`, `bool`) are kept intact.
- Complex types are safely converted to a string representation.
- Strings longer than 512 characters are truncated to 509 characters followed by `...` to prevent memory bloat and massive payload sizes over the network.
