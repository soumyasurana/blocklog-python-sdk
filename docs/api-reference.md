```markdown
# API Reference

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `BLOCKLOG_API_KEY` | Yes | — | Your Blocklog API key |
| `BLOCKLOG_BASE_URL` | No | `https://blocklogsecurity.com/api/v1` | API endpoint |
| `BLOCKLOG_SDK_SIGNING_KEY` | No | `""` | HMAC-SHA256 signing key |
| `BLOCKLOG_TIMEOUT` | No | `10` | Request timeout in seconds |
| `BLOCKLOG_MAX_RETRIES` | No | `3` | Retry attempts on failure |
| `BLOCKLOG_BATCH_SIZE` | No | `100` | Events per batch flush |
| `BLOCKLOG_FLUSH_INTERVAL` | No | `2` | Seconds between auto-flushes |

---

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
- `signing_key` (str, optional): HMAC-SHA256 key for tamper-evident log signatures. Falls back to `BLOCKLOG_SDK_SIGNING_KEY`. Note: this is not asymmetric Ed25519 signing.
- `timeout` (float, optional): Per-request timeout in seconds (default: 10). Falls back to `BLOCKLOG_TIMEOUT`.
- `max_retries` (int, optional): Number of automatic retries (default: 3). Falls back to `BLOCKLOG_MAX_RETRIES`.
- `debug` (bool, optional): If `True`, logs every outbound request to stderr.

**Returns:** `BlocklogClient`

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
**Purpose:** Traces an AI agent function, linking it to a Blocklog session. Automatically handles sync and async functions.

> **Warning:** Class decoration only emits `AGENT_START`. For full lifecycle tracing, decorate the specific method (e.g. `run`, `execute`) rather than the class itself.

**Parameters:**
- `name`: Human-readable agent name. Defaults to `func.__name__`.
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

---

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
**Purpose:** Records a tool call as a Blocklog event, capturing inputs, outputs, duration, and errors. Inherits trace context from the surrounding `@agent`.

**Parameters:**
- `name`: Human-readable tool name. Defaults to `func.__name__`.
- `schema`: Optional dict describing the input schema.
- `tags`: Optional string tags.
- `metadata`: Arbitrary extra data.

**Returns:** Decorated callable.

**Example:**
```python
@blocklog.tool(name="fetch-price")
def get_price(ticker: str) -> float:
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
**Purpose:** Context manager for recording an AI decision.

**Parameters:**
- `type` (str): Decision type identifier (e.g. `"BUY"`).
- `asset` (str, optional): Asset this decision is about.
- `confidence` (float, optional): Model confidence score (0 to 1).
- `metadata` (dict, optional): Extra fields.

**Returns:** Yields `DecisionContext`.

**Example:**
```python
with blocklog.decision(type="BUY", asset="TSLA") as d:
    d.record_input(price=412.50)
    d.record_output(status="executed")
```

### `DecisionContext`
Live handle to a decision being recorded.

- **`record_input(**kwargs)`**: Record structured inputs. Returns `self`.
- **`record_output(**kwargs)`**: Record structured outputs. Returns `self`.
- **`tag(*tags)`**: Attach string labels. Returns `self`.
- **`request_approval(reason, reviewer=None)`**: Non-blocking request for human approval. Returns `self`.
- **`verify() -> dict`**: Verify the decision after the `with` block has exited. Raises `RuntimeError` if called before the decision is committed.

---

## Clients

### `BlocklogClient`
**Purpose:** Synchronous core client. Usually instantiated via `blocklog.init()`.

**Methods:**
- `from_env() -> BlocklogClient`: Create a client from environment variables.
- `add_hook(hook: Callable) -> BlocklogClient`: Register a middleware hook applied to every outbound event.
- `instrument_openai_agents() -> BlocklogClient`: Auto-instrument the OpenAI Agents SDK.
- `instrument_langchain() -> BlocklogClient`: Auto-instrument LangChain.
- `instrument_langgraph() -> BlocklogClient`: Auto-instrument LangGraph.
- `event(event_type, payload, **kwargs) -> IngestResponse`: Emit a single event immediately.
- `enqueue(event_type, payload, **kwargs)`: Enqueue an event for batched delivery.
- `flush(batch=None)`: Flush the event buffer.

### `AsyncBlocklogClient`
**Purpose:** Async client for use in async applications.

**Methods:** Same as `BlocklogClient` with async overrides:
- `async event(event_type, payload, **kwargs) -> IngestResponse`
- `async flush(batch=None)`

### `BlocklogConfig`
**Purpose:** Configuration Pydantic model.

**Fields:**
- `base_url`: str
- `api_key`: str
- `signing_key`: str — HMAC-SHA256 key, not Ed25519
- `timeout`: float
- `max_retries`: int
- `batch_size`: int
- `flush_interval`: float

---

## Layer 2 Sub-modules

*Available via `client.module.method()` or imported directly from `blocklog.api.*`.*

### `blocklog.api.decisions`
- `create(decision_type, asset, confidence, metadata, trace_id, session_id, agent_id) -> dict`
- `list() -> list[dict]`
- `get(decision_id) -> dict`
- `verify(decision_id) -> dict`
- `timeline(decision_id) -> list[dict]`
- `evidence(decision_id) -> dict`
- `replay(decision_id) -> dict`

### `blocklog.approval`
Human-in-the-loop workflows.
- `request(decision_id, reason, reviewer, log_id, metadata) -> dict`
- `reject(reviewer, reason, decision_id) -> dict`
- `escalate(from_reviewer, to_reviewer, reason) -> dict`
- `list_overrides() -> list[dict]`
- `audit_trail() -> list[dict]`

### `blocklog.api.incidents`
Incident management. Not exported from the top-level `blocklog` namespace — import via `from blocklog.api.incidents import IncidentsClient` or access via `client.incidents`.
- `create(title, trace_id, severity, description, metadata) -> IncidentHandle`
- `get(incident_id) -> IncidentHandle`
- `list_all() -> list[IncidentHandle]`

### `blocklog.replay`
Forensic replay sessions.
- `replay(trace_id, token_id, metadata) -> ReplaySession`

### `blocklog.api.verify`
Access via `client.verify` to avoid naming conflict with `DecisionContext.verify()`.
- `log(log_id) -> dict`
- `batch(batch_id) -> dict`
- `decision(decision_id) -> dict`

### `blocklog.compliance`
Compliance report generation.
- `generate(trace_id, framework, date_from, date_to, metadata) -> dict`
- `get(report_id) -> dict`
- `list() -> list[dict]`
- `dashboard() -> dict`
- `share(report_id, expires_in, recipient_email) -> dict`
- `export(report_id, download) -> dict`
```