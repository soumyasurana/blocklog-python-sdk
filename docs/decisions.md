# Decision Workflow

Blocklog revolves around the concept of a **Decision**. A decision captures a holistic snapshot of an AI agent's action, grouping inputs, outputs, approvals, and context into an auditable record.

## Creation

To create a decision, use the `blocklog.decision()` context manager. This sets up an execution boundary. If the block completes successfully, the decision is marked `complete`. If an exception occurs, it is marked `error`.

```python
import blocklog

with blocklog.decision(type="BUY", asset="TSLA", confidence=0.87) as d:
    # Model execution goes here
    pass
```

## Inputs

Before your agent or model makes its final determination, you should record the inputs it considered. This makes root-cause analysis significantly easier.

```python
d.record_input(
    price=412.50, 
    volume=1_200_000, 
    signal="rsi_oversold"
)
```

## Outputs

Once the model produces a result, record it as an output.

```python
d.record_output(
    order_id="ord_88", 
    filled_at=413.10, 
    qty=100
)
```

## Context Management

Decisions inherit the trace context automatically if they are executed inside an `@agent` decorator. This links the decision to the specific agent execution, its tool calls, and trace IDs.

You can also attach tags to the decision for filtering in your dashboard:
```python
d.tag("high-value", "momentum-strategy")
```

## Approvals (Human-in-the-Loop)

You can seamlessly request human approval for high-risk decisions. The `request_approval` method is non-blocking. It notifies the assigned reviewer but lets the python code continue.

```python
if order_value > 500_000:
    d.request_approval(
        reason="Trade exceeds $500k threshold",
        reviewer="risk-team@fund.com"
    )
```

## Best Practices

- **Use narrow decision boundaries**: Only wrap the specific logic where the action takes place in the `with` block.
- **Pass structured kwargs**: Avoid passing large JSON strings to `record_input`/`record_output`; use kwargs to maintain structure.
- **Leverage Tags**: Use `.tag()` generously to categorize decisions across different market regimes, users, or workflows.
