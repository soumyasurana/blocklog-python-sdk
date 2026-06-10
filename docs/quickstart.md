# Quickstart

This is the shortest possible example demonstrating how to initialize the SDK, use a tool, and record a decision.

## The Code

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

## What Happens Here?

1. **`blocklog.init`**: Configures the global client and sets the API key.
2. **`@blocklog.tool`**: Intercepts the `check_price` function, recording inputs (`ticker="TSLA"`) and outputs (`412.50`) as an event.
3. **`@blocklog.agent`**: Wraps the `run_agent` execution in a context, establishing a unique session and trace ID.
4. **`blocklog.decision`**: A context manager that creates a `DecisionContext`. Inside this block, we explicitly record the state (inputs) prior to our action, and the result (outputs) of the action. When the block exits, the decision is marked complete and submitted to the Blocklog backend.
