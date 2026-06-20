# Blocklog Python SDK

**Record, audit, and investigate every decision your AI agents make.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Version 0.2.0](https://img.shields.io/badge/version-0.2.0-brightgreen.svg)](https://github.com/blockloghq/blocklog-python)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Documentation](https://img.shields.io/badge/docs-available-blue.svg)](docs/index.md)

---

## Why Blocklog?

When AI agents execute actions in production, the context behind their decisions is often lost. Debugging failures, reproducing state, and maintaining compliance becomes nearly impossible without a structured audit trail. Blocklog solves this by capturing exactly what the model knew, what tools it used, and what it ultimately decided—all securely anchored and optionally requiring human approval.

---

## What Blocklog Does

- **Trace AI agents** and their execution duration automatically.
- **Trace tool calls**, capturing inputs and outputs seamlessly.
- **Record decisions** with detailed metadata, inputs, and outputs.
- **Request approvals** via non-blocking human-in-the-loop workflows.
- **Verify records** cryptographically against Ed25519 signatures.
- **Generate compliance evidence** (e.g., SOC2, GDPR).
- **Investigate failures with replay** using forensic timelines and root-cause analysis.

---

## Architecture Overview

```text
    AI Agent
       ↓
@blocklog.agent
       ↓
 Tools + Decisions
       ↓
  Event Buffer
       ↓
  Blocklog API
       ↓
Replay / Verification / Compliance
```

---

## Installation

Blocklog requires Python 3.10+. Install the SDK from PyPI:

```bash
pip install blocklog
```

For development installation or to install from source:

```bash
git clone https://github.com/blockloghq/blocklog-python.git
cd blocklog-python
pip install -e .
```

---

## Quickstart

```python
import os
import blocklog

# 1. Initialize the SDK
blocklog.init(api_key=os.environ.get("BLOCKLOG_API_KEY", "blk_demo_key"))

# 2. Record tool calls
@blocklog.tool
def check_price(ticker: str) -> float:
    return 412.50

# 3. Trace your agent
@blocklog.agent(name="simple-trader")
def run_agent():
    price = check_price("TSLA")
    
    # 4. Record the decision
    with blocklog.decision(type="BUY", asset="TSLA") as d:
        d.record_input(price=price)
        d.record_output(order_id="ord_123")
        
    print(f"Decision recorded: {d.id}")

if __name__ == "__main__":
    run_agent()
```

## Signup And Teams

```python
from blocklog import (
    AsyncBlocklogClient,
    BlocklogClient,
    can_manage_members,
    can_manage_team,
    get_primary_team,
    is_team_owner,
)

client = BlocklogClient(
    base_url="https://your-blocklog-host/api/v1",
)

signup = client.auth.signup(
    username="jane",
    email="jane@example.com",
    password="ChangeMe123!",
    workspace_name="Acme Security",
)

print(signup.team.name)
print(is_team_owner(signup.team, signup.user.user_id))
print(signup.team.owner_user_id)

client.set_access_token(signup.token)

teams = client.teams.list()
primary_team = get_primary_team(teams)

if primary_team and can_manage_team(primary_team, signup.user.user_id):
    client.teams.update(primary_team.id, default_sla_minutes=30)
    members = client.teams.members.list(primary_team.id)
    if members and can_manage_members(members[0]):
        client.teams.notify_test(primary_team.id)


async def async_example() -> None:
    async_client = AsyncBlocklogClient(base_url="https://your-blocklog-host/api/v1")
    login = await async_client.auth.login("jane@example.com", "ChangeMe123!")
    async_client.set_access_token(login.token)
    teams = await async_client.teams.list()
    print(teams)
```

---

## What Happens Under The Hood?

When you apply `@blocklog.agent`, Blocklog starts an internal session context that automatically propagates a `trace_id` to any subsequent operations. When `@blocklog.tool` is invoked, it captures the inputs and outputs, linking them to the active trace. Finally, `blocklog.decision()` bundles the agent's logic into a concrete, auditable event that is asynchronously buffered and flushed to the Blocklog backend without blocking your application.

---

## Core Concepts

- **Decision**: A structured record of an AI action, tracking the explicit inputs it considered and the outputs it generated.
- **Trace**: The end-to-end execution path of an agent, automatically correlating all tool calls and decisions via a shared `trace_id`.
- **Event**: A low-level building block representing a single state change (e.g., `TOOL_CALL`, `DECISION_INPUT`), securely buffered and dispatched.
- **Approval**: A human-in-the-loop (HITL) gate that flags high-stakes decisions for manual review.
- **Replay**: A forensic reconstruction of a trace allowing developers to understand the root cause of an agent's failure or action.

---

## Common Use Cases

- **Trading Agents**: Capturing the exact market data (inputs) that led an agent to execute a trade (output).
- **AI Copilots**: Tracing user interactions and the tools invoked to fetch internal company data.
- **Compliance-Sensitive Workflows**: Automatically generating SOC2 or GDPR reports for AI behavior.
- **Customer Support Agents**: Recording decisions to escalate to human agents vs. resolving automatically.
- **Human-in-the-Loop Systems**: Pausing execution of high-value actions (e.g., refunds > $500) until a human reviewer approves.

---

## Integrations

Blocklog seamlessly auto-instruments popular AI frameworks:
- **LangChain**: Trace chains, LLMs, and tools automatically via `client.instrument_langchain()`.
- **LangGraph**: Hook into graph states via `client.instrument_langgraph()`.
- **OpenAI Agents**: Track official SDK executions via `client.instrument_openai_agents()`.
- **LiteLLM**: Instrument any LiteLLM completion call via `client.instrument_litellm()`.

Read more in the [Integrations Guide](docs/integrations.md).

---

## Documentation

| Topic | Guide |
|-------|-------|
| **Getting Started** | [Installation](docs/installation.md) • [Quickstart](docs/quickstart.md) • [Core Concepts](docs/concepts.md) |
| **Instrumentation** | [Tracing](docs/tracing.md) • [Decisions](docs/decisions.md) • [Decorators](docs/decorators.md) |
| **Frameworks** | [Integrations](docs/integrations.md) — LangChain, LangGraph, OpenAI Agents, LiteLLM |
| **Operations** | [Async Usage](docs/async.md) • [Production](docs/production.md) • [Performance](docs/performance.md) |
| **Reference** | [API Reference](docs/api-reference.md) • [Error Handling](docs/error-handling.md) • [Troubleshooting](docs/troubleshooting.md) |
| **Misc** | [Examples](docs/examples.md) • [Changelog](docs/changelog.md) |

---

## Examples

We provide several runnable scripts in the `examples/` directory to help you understand Blocklog in practice:

- **[01_quickstart.py](examples/01_quickstart.py)**: The bare minimum needed to trace an agent, run a tool, and record a decision.
- **[02_stock_trading_agent.py](examples/02_stock_trading_agent.py)**: A simulated trading agent demonstrating tool tagging, human-in-the-loop approvals, and cryptographic verification.
- **[03_multi_agent_workflow.py](examples/03_multi_agent_workflow.py)**: A complex pipeline showing context passing across Analyst, Risk, and Executor agents, ending in a compliance report.

---

## Production Features

- **Async Support**: Native `asyncio` compatibility utilizing `contextvars` for seamless trace propagation across `await` boundaries.
- **Event Buffering**: High-volume telemetry is safely batched in-memory and flushed asynchronously.
- **Retry Handling**: Built-in exponential backoff for transient network issues.
- **Signing**: Optional Ed25519 payload signing for tamper-evident, cryptographically verifiable logs.
- **Middleware Hooks**: Add custom logic to redact PII or inject metadata before payloads leave your server.
- **Typed Team APIs**: Ownership-aware models for teams, members, and signup responses.
- **Standardized Exceptions**: Authentication, authorization, validation, conflict, rate-limit, and server error mapping.

Read our [Production Best Practices](docs/production.md) for more details.

---

## Contributing

We welcome contributions to the Blocklog Python SDK! Please read through our open issues or submit a Pull Request. Ensure you have installed the SDK in editable mode (`pip install -e .`) before running tests.

---

## Configuration

Blocklog can be configured via environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `BLOCKLOG_API_KEY` | Your Blocklog API key | `""` |
| `BLOCKLOG_ACCESS_TOKEN` | User access token for dashboard-style APIs | `""` |
| `BLOCKLOG_BASE_URL` | API base URL | `http://127.0.0.1:8000/api/v1` |
| `BLOCKLOG_SDK_SIGNING_KEY` | Optional seed key for hash signing | `""` |
| `BLOCKLOG_TIMEOUT` | Request timeout in seconds | `10` |
| `BLOCKLOG_MAX_RETRIES` | Number of retry attempts | `3` |
| `BLOCKLOG_BATCH_SIZE` | Event batch size | `100` |
| `BLOCKLOG_FLUSH_INTERVAL` | Batch flush interval in seconds | `2` |

## Troubleshooting

### Installation Issues

If you encounter installation errors:

```bash
# Upgrade pip first
pip install --upgrade pip

# Install with verbose output
pip install blocklog -v
```

### Import Errors

If you get import errors after installation:

```bash
# Verify installation
pip show blocklog

# Reinstall if needed
pip install --force-reinstall blocklog
```

### Connection Issues

If the SDK cannot connect to the Blocklog API:

1. Verify your API key is correct
2. Check that `BLOCKLOG_BASE_URL` points to the correct endpoint
3. Ensure network connectivity to the API server
4. Check firewall settings

## Teams API

```python
from blocklog import BlocklogClient

client = BlocklogClient(access_token="user-token")

teams = client.teams.list()
team = client.teams.get(teams[0].id)
members = client.teams.members.list(team.id)
result = client.teams.notify_test(team.id)
print(result.results)
```

## Links

- **Homepage**: https://blockloghq.com
- **Documentation**: https://docs.blockloghq.com
- **Repository**: https://github.com/blockloghq/blocklog-python
- **Issues**: https://github.com/blockloghq/blocklog-python/issues
- **PyPI**: https://pypi.org/project/blocklog/

---

## License

MIT License. See the LICENSE file for details.