# API Reference

This document provides a comprehensive API reference derived from the Blocklog SDK source code. It covers all public modules, method signatures, parameters, return types, exceptions, and usage examples.

## Initialization

### `blocklog.init`
```python
def init(
    api_key: str | None = None,
    *,
    base_url: str | None = None,
    signing_key: str | None = None,
    timeout: float | None = None,
    max_retries: int | None = None,
    debug: bool = False,
) -> "BlocklogClient"
```
**Purpose:** Initializes the Blocklog SDK. Call once at application startup.
**Parameters:**
- `api_key` (str, optional): Your Blocklog API key. Falls back to `BLOCKLOG_API_KEY`.
- `base_url` (str, optional): Override the default API base URL. Falls back to `BLOCKLOG_BASE_URL`.
- `signing_key` (str, optional): Optional seed key for deterministic hash signing of log payloads. Falls back to `BLOCKLOG_SDK_SIGNING_KEY`. Note: This is NOT cryptographic Ed25519 signing - it generates a deterministic SHA256 hash for tamper-evidence purposes.
- `timeout` (float, optional): Per-request timeout in seconds (default: 10). Falls back to `BLOCKLOG_TIMEOUT`.
- `max_retries` (int, optional): Number of automatic retries (default: 3). Falls back to `BLOCKLOG_MAX_RETRIES`.
- `debug` (bool, optional): If `True`, logs every outbound request to stderr.
**Returns:** `BlocklogClient`
**Exceptions:** None directly, though misconfigurations may cause failures later.
**Example:**
```python
client = blocklog.init(api_key="blk_live_...")
```

---

## Decorators

### `@blocklog.agent`
```python
def agent(
    func=None,
    *,
    name: str | None = None,
    version: str = "1.0",
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
)
```
**Purpose:** Decorator that traces an AI agent function or class, linking it to a Blocklog session. Automatically handles async functions.
**Parameters:**
- `name`: Human-readable agent name.
- `version`: Semver-style version string.
- `tags`: Optional list of string tags.
- `metadata`: Arbitrary extra data.
**Returns:** Decorated callable or class.
**Example:**
```python
@blocklog.agent(name="analyst", version="1.0")
def run_analyst():
    pass
```

### `@blocklog.tool`
```python
def tool(
    func=None,
    *,
    name: str | None = None,
    schema: dict[str, Any] | None = None,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
)
```
**Purpose:** Decorator that records a tool call as a Blocklog event, tracking inputs, outputs, and duration. Inherits the trace from `@agent`. Handles async functions automatically.
**Parameters:**
- `name`: Human-readable tool name.
- `schema`: Optional dict describing the input schema.
- `tags`: Optional string tags.
- `metadata`: Arbitrary extra data.
**Returns:** Decorated callable.
**Example:**
```python
@blocklog.tool(name="fetch-price")
def get_price(ticker: str):
    return 100.0
```

---

## Context Managers

### `blocklog.decision`
```python
def decision(
    *,
    type: str,
    asset: str | None = None,
    confidence: float | None = None,
    metadata: dict[str, Any] | None = None,
    agent_id: str | None = None,
    trace_id: str | None = None,
) -> Generator[DecisionContext, None, None]
```
**Purpose:** Context manager for recording an AI decision. Yields a `DecisionContext`.
**Parameters:**
- `type` (str): Decision type identifier (e.g. "BUY").
- `asset` (str, optional): Asset this decision is about.
- `confidence` (float, optional): Model confidence score (0 to 1).
- `metadata` (dict, optional): Extra fields.
**Returns:** Yields `DecisionContext`.
**Example:**
```python
with blocklog.decision(type="BUY", asset="TSLA") as d:
    d.record_output(status="executed")
```

### `DecisionContext`
Live handle to a decision being recorded.
- **`record_input(**kwargs)`**: Record structured inputs. Returns `self`.
- **`record_output(**kwargs)`**: Record structured outputs. Returns `self`.
- **`tag(*tags)`**: Attach string labels. Returns `self`.
- **`request_approval(reason: str, reviewer: str | None = None)`**: Non-blocking request for human approval. Returns `self`.
- **`verify() -> dict`**: Immediately verify the decision. Raises `RuntimeError` if called before the decision is committed (i.e. before the `with` block begins).

---

## Clients

### `BlocklogClient`
**Purpose:** The synchronous core client. Usually instantiated via `blocklog.init()`.

**Methods:**
- `from_env() -> BlocklogClient`: Class method to create a client solely from env vars.
- `add_hook(hook: Callable) -> BlocklogClient`: Register a middleware hook.
- `instrument_openai_agents() -> BlocklogClient`
- `instrument_langchain() -> BlocklogClient`
- `instrument_langgraph() -> BlocklogClient`
- `event(event_type: str, payload: dict, **kwargs) -> IngestResponse`: Emit synchronous event.
- `enqueue(event_type: str, payload: dict, **kwargs)`: Enqueue batched event.
- `flush(batch=None)`: Flush event buffer.

### `AsyncBlocklogClient`
**Purpose:** The asynchronous client for manual async flushing and event dispatch.
**Methods:** Inherits from `BlocklogClient` but overrides network calls to be async:
- `async event(event_type: str, payload: dict, **kwargs) -> IngestResponse`
- `async flush(batch=None)`

### `BlocklogConfig`
**Purpose:** Configuration Pydantic model.
**Fields:**
- `base_url`: str
- `api_key`: str
- `signing_key`: str (seed key for hash-based signing, NOT Ed25519)
- `timeout`: float
- `max_retries`: int
- `batch_size`: int
- `flush_interval`: float

---

## Layer 2 Sub-modules

*(Available via `blocklog.module.*` or `client.module.*`)*

### `blocklog.api.decisions.DecisionsClient`
**Purpose:** Manage AI Decision records natively.
- `create(decision_type, asset, confidence, metadata, trace_id, session_id, agent_id) -> dict`
- `list() -> list[dict]`
- `get(decision_id: str) -> dict`
- `verify(decision_id: str) -> dict`
- `timeline(decision_id: str) -> list[dict]`
- `evidence(decision_id: str) -> dict`
- `replay(decision_id: str) -> dict`

### `blocklog.approval`
**Purpose:** Human-in-the-loop (HITL) workflows.
- `request(decision_id, reason, reviewer, log_id, metadata) -> dict`
- `reject(reviewer, reason, decision_id) -> dict`
- `escalate(from_reviewer, to_reviewer, reason) -> dict`
- `list_overrides() -> list[dict]`
- `audit_trail() -> list[dict]`

### `blocklog.incident`
**Purpose:** Incident management API.
- `create(title, trace_id, severity, description, metadata) -> IncidentHandle`
- `get(incident_id) -> IncidentHandle`
- `list_all() -> list[IncidentHandle]`

### `blocklog.replay`
**Purpose:** Forensic replays.
- `replay(trace_id, token_id, metadata) -> ReplaySession`

### `blocklog.verify`
**Purpose:** Cryptographic verification against blockchain anchors.
- `log(log_id: str) -> dict`
- `batch(batch_id: str) -> dict`
- `decision(decision_id: str) -> dict`

### `blocklog.compliance`
**Purpose:** Compliance report generation.
- `generate(trace_id, framework, date_from, date_to, metadata) -> dict`
- `get(report_id) -> dict`
- `list() -> list[dict]`
- `dashboard() -> dict`
- `share(report_id, expires_in, recipient_email) -> dict`
- `export(report_id, download) -> dict`
