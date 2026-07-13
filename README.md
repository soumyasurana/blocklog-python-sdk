<div align="center">
  <h1>Official Python SDK for Blocklog</h1>
  <p><strong>Typed Python SDK for integrating Blocklog into AI applications with structured audit logging, execution tracing, and cryptographic verification.
  </strong></p>

  [![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
  ![CI](https://github.com/soumyasurana/blocklog-python-sdk/actions/workflows/ci.yml/badge.svg)
  [![PyPI Version](https://img.shields.io/pypi/v/blocklog)](https://pypi.org/project/blocklog/)
  [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
  [![Documentation](https://img.shields.io/badge/docs-available-blue.svg)](docs/index.md)
</div>

---

Blocklog Python SDK is the official Python client for Blocklog. It enables Python applications to record AI execution traces, manage decision records, verify audit integrity, and interact with Blocklog's APIs through a clean, typed, and developer-friendly interface.

## Features

- **Client & Transport**: Synchronous and asynchronous (`AsyncBlocklogClient`) support, connection pooling, exponential backoff retries, and background event batching.
- **Observability**: Decorator-based tracing for agents (`@blocklog.agent`) and tools (`@blocklog.tool`).
- **Governance**: Human-in-the-loop (HITL) approval workflows and incident management.
- **Security & Compliance**: Ed25519 cryptographic payload signing, timeline verification, and automated SOC2/GDPR compliance reports.
- **Integrations**: Auto-instrumentation for LangChain, LangGraph, OpenAI, and LiteLLM.

---

## Installation

The SDK requires **Python 3.10+**.

### pip

```bash
pip install blocklog
```

*(Optional)* Install with all integrations (LangChain, LangGraph, OpenAI, LiteLLM):

```bash
pip install blocklog[all]
```

### uv

```bash
uv pip install blocklog
```

### poetry

```bash
poetry add blocklog
```

---

## Quick Start

The fastest way to get started is to initialize the client and record a single decision.

```python
import os
from blocklog import BlocklogClient

# 1. Initialize the client
client = BlocklogClient(api_key=os.environ.get("BLOCKLOG_API_KEY"))

# 2. Record an AI decision
response = client.decisions.create(
    decision_type="BUY_ORDER",
    asset="TSLA",
    confidence=0.91,
    inputs={"price": 412.50, "signals": ["momentum"]},
    outputs={"order_id": "ord_123984"}
)

print(f"Decision recorded: {response.get('id')}")
```

For advanced tracing, Blocklog provides decorators (`@blocklog.agent`, `@blocklog.tool`) to automatically capture inputs and outputs within a shared execution context.

---

## Authentication

Blocklog primarily authenticates using API Keys for server-to-server communication. For user-specific or dashboard actions, an Access Token is used.

### API Keys (Server-to-Server)

API keys are required to record logs, decisions, and traces. Set it via environment variable:

```bash
export BLOCKLOG_API_KEY="blk_..."
```

Then instantiate the client:

```python
from blocklog import BlocklogClient

# Automatically loads from BLOCKLOG_API_KEY
client = BlocklogClient()
```

### Access Tokens (User Context)

If you are interacting with team management or dashboard APIs on behalf of a specific user, provide an access token:

```python
client.set_access_token("user_access_token_here")
```

---

## Examples

### Human-in-the-Loop (HITL) Approval

Flag a high-stakes decision for human review before allowing the system to proceed.

```python
# Request approval (non-blocking in the SDK, triggers webhook in backend)
response = client.approval.request(
    decision_id="dec_abc123",
    reason="Trade exceeds $500k automated threshold",
    reviewer="risk-team@fund.com"
)
print("Approval requested successfully.")
```

### Cryptographic Verification

Verify that an agent's decision and its underlying evidence have not been tampered with.

```python
verification = client.verify.decision("dec_abc123")

if verification["status"] == "verified":
    print("Decision integrity mathematically proven.")
else:
    print("WARNING: Tampering detected!")
```

### Incident Management

Create an incident based on an anomalous trace and assign it to an investigator.

```python
incident = client.incidents.create(
    title="Unexpected SELL order for AAPL",
    trace_id="trace-xyz",
    severity="high"
)

incident.assign("alice@fund.com", notes="Please investigate this immediately.")
incident.resolve(summary="False positive - corrected upstream model weights.")
```

### Export Compliance Evidence

Generate a SOC2 compliance report scoped to a specific AI trace.

```python
report = client.compliance.generate(
    trace_id="trace-xyz",
    framework="SOC2"
)

# Create a secure shareable link valid for 24 hours
link = client.compliance.share(report["id"], expires_in=86400)
print(f"Compliance report available at: {link['share_url']}")
```

---

## SDK Architecture

The SDK is organized into intuitive, domain-specific resource layers accessible directly from the `BlocklogClient`:

- `client.decisions`: Manage AI decision records and evidence timelines.
- `client.approval`: Human-in-the-Loop (HITL) workflow management.
- `client.incidents`: Incident response lifecycle (assign, annotate, resolve).
- `client.replay`: Forensic replay sessions and root-cause analysis.
- `client.compliance`: Compliance dashboard and report generation.
- `client.verify`: Cryptographic verification of logs and batches.
- `client.traces`: Query trace and session execution paths.
- `client.teams`: Manage organizations, users, and SLA rules.
- `client.auth`: User signups and authentication flows.

For modern asynchronous applications (e.g., FastAPI), use `AsyncBlocklogClient` which provides the exact same architecture but with `async/await` semantics.

---

## Error Handling

The SDK raises specific typed exceptions (inheriting from `BlocklogError`) mapped to underlying HTTP status codes, allowing you to gracefully handle failures.

```python
from blocklog.exceptions import (
    BlocklogError,
    AuthenticationError,
    RateLimitError,
    ValidationError
)

try:
    client.decisions.get("invalid_id")
except AuthenticationError:
    print("Invalid API Key provided.")
except RateLimitError:
    print("Throttled by Blocklog backend. Backing off.")
except ValidationError as e:
    print(f"Malformed request data: {e}")
except BlocklogError as e:
    print(f"An unexpected error occurred: {e}")
```

---

## Configuration

You can customize the SDK's behavior using the `BlocklogConfig` object or via environment variables:

| Environment Variable | Description | Default |
|----------------------|-------------|---------|
| `BLOCKLOG_API_KEY` | Your Blocklog API key | `""` |
| `BLOCKLOG_BASE_URL` | API base URL | `https://blocklogsecurity.com/api/v1` |
| `BLOCKLOG_TIMEOUT` | Request timeout in seconds | `10` |
| `BLOCKLOG_MAX_RETRIES` | Max exponential backoff retries | `3` |
| `BLOCKLOG_BATCH_SIZE` | Telemetry event batch size | `100` |
| `BLOCKLOG_FLUSH_INTERVAL` | Batch flush interval in seconds | `2` |
| `BLOCKLOG_SDK_SIGNING_KEY` | Optional seed key for Ed25519 signing | `""` |

---

## Why Use the Python SDK?

While you could interact with the Blocklog API using raw HTTP requests, the SDK provides significant developer experience improvements:

1. **Context Propagation**: Leveraging `contextvars`, the SDK automatically propagates `trace_id` and `session_id` across your application boundaries without passing variables manually.
2. **Background Batching**: High-volume telemetry (logs, tool inputs) are safely buffered in-memory and asynchronously flushed to prevent blocking your application's critical path.
3. **Resilience**: Built-in exponential backoff and automatic retry logic for transient network failures.
4. **Auto-Instrumentation**: One-line integrations to automatically trace LangChain, LangGraph, OpenAI SDK, and LiteLLM executions.
5. **Ed25519 Signing**: The SDK handles the cryptographic signing of payloads natively when `BLOCKLOG_SDK_SIGNING_KEY` is provided.

---

## API Coverage

The SDK implements comprehensive support for the Blocklog REST API:

- ✅ **Decisions** (`create`, `list`, `get`, `timeline`, `evidence`)
- ✅ **Approvals** (`request`, `reject`, `escalate`, `audit_trail`)
- ✅ **Incidents** (`create`, `assign`, `resolve`, `close`, `report`, `annotate`)
- ✅ **Forensics & Replay** (`create`, `timeline`, `root_cause`, `causal_graph`, `counterfactual`, `compare`)
- ✅ **Compliance** (`generate`, `list`, `dashboard`, `share`, `export`)
- ✅ **Verification** (`log`, `batch`, `decision`)
- ✅ **Teams & Auth** (`signup`, `login`, `teams.list`, `teams.update`)

---

## Development & Testing

We welcome contributions to the Blocklog Python SDK!

1. Clone the repository.
2. Install the package in editable mode with development dependencies:

```bash
pip install -e ".[dev]"
```

3. Run the test suite using `pytest`:

```bash
pytest tests/ -v
```

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.