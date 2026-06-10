# Examples

The `examples/` directory in the Blocklog Python SDK contains runnable scripts demonstrating the core usage patterns. They reflect the current public APIs and are actively tested.

## 01_quickstart.py
**Purpose:** Demonstrates the bare minimum to trace an agent and record a decision.
**Features demonstrated:** 
- SDK Initialization (`blocklog.init()`)
- Decorating a tool (`@blocklog.tool`)
- Decorating an agent (`@blocklog.agent`)
- Recording a decision (`blocklog.decision()`)
**Expected Output:** 
Logs demonstrating the initialization of the agent. The output will conclude with a success message containing the decision UUID generated:
```
Decision recorded: <uuid>
Done. Check your Blocklog dashboard.
```

## 02_stock_trading_agent.py
**Purpose:** Simulates a fully functional trading agent that fetches market data, evaluates momentum, and conditionally executes a trade.
**Features demonstrated:**
- Advanced tool metadata and tagging (`tags=["market-data"]`)
- Contextual tracking of outputs: Requesting human approval for trades exceeding $8k threshold via `d.request_approval()`
- Immediate cryptographic verification of the recorded decision via `blocklog.verify.decision(decision_id)`
**Expected Output:** 
A detailed execution trace printed to the terminal of the `stock-trader` agent checking the market price and placing an order. A decision record is produced and verified:
```
  ✓ Decision recorded: <uuid>
  Verifying decision against blockchain anchor...
  ✓ Verification status: verified
```

## 03_multi_agent_workflow.py
**Purpose:** Demonstrates a complex, multi-agent pipeline sharing a common `workflow_id`.
**Features demonstrated:**
- Multi-agent correlation (Analyst → Risk Manager → Execution Engine)
- Passing context dynamically using `metadata={"workflow_id": WORKFLOW_ID}`
- Generating a compliance report for the entire workflow via `blocklog.compliance.generate()`
**Expected Output:** 
Three distinct agent executions logging their steps to the console. A chain of decisions is created sequentially (`SIGNAL` → `RISK_APPROVAL` → `TRADE_EXECUTION`). Finally, the terminal outputs the `report_id` of the SOC2 compliance report:
```
[Orchestrator] Generating compliance report...
[Orchestrator] Compliance report: <report_id>
```
