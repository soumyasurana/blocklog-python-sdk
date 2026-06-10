# Blocklog Python SDK

**Infrastructure for AI Decision-Making.**

Record every decision your AI agents make.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

---

## Installation

### From GitHub

```bash
pip install git+https://github.com/blockloghq/blocklog-python.git
```

### Verify Installation

```python
import blocklog

print("Blocklog installed successfully")
```

---

## Quick Start: Time to First Trace

The Blocklog SDK is designed around a simple workflow:

**Initialize → Trace → Tool → Decide**

### 1. Initialize

Configure the SDK once at startup.

```python
import blocklog

blocklog.init(api_key="blk_...")
```

### 2. Tool

Record every tool call automatically.

```python
@blocklog.tool
def fetch_price(ticker: str) -> float:
    return 412.50
```

Blocklog automatically captures:

* Tool inputs
* Tool outputs
* Execution timing
* Trace relationships

### 3. Agent

Trace your agent's execution lifecycle.

```python
@blocklog.agent(name="stock-trader")
def run_agent():
    price = fetch_price("TSLA")
```

### 4. Decision

Record the decision and its supporting evidence.

```python
with blocklog.decision(type="BUY", asset="TSLA") as d:
    d.record_input(price=price)

    # Trading logic here

    d.record_output(order_id="ord_123")
```

---

## What Blocklog Records

Every decision can be linked to:

* Inputs used by the agent
* Tool calls executed
* Outputs generated
* Human approvals
* Incidents and investigations
* Compliance reports
* Cryptographic verification records
* Replay timelines

This creates a complete audit trail for AI-driven systems.

---

## Examples

See the `examples/` directory for runnable examples:

```text
examples/
├── 01_quickstart.py
├── 02_stock_trading_agent.py
├── 03_multi_agent_workflow.py
└── advanced/
    ├── 01_human_approval_workflow.py
    ├── 02_incident_investigation.py
    ├── 03_decision_comparison.py
    └── langchain_alert_demo.py
```

---

## Documentation

* Documentation: https://blocklogsecurity.com/docs
* Website: https://blocklogsecurity.com
* Issues: https://github.com/blockloghq/blocklog-python/issues

---

## License

MIT License. See the LICENSE file for details.
