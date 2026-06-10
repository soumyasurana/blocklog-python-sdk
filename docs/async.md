# Async Usage

The Blocklog Python SDK fully supports asynchronous Python (`asyncio`). You can seamlessly trace async agents, invoke async tools, and execute async decision workflows.

## Initializing the Async Client

If you need direct access to the low-level client for async operations (like manual event flushing), you can instantiate the `AsyncBlocklogClient`. However, the module-level functions (`blocklog.init()`) automatically support async wrappers, so you typically do not need to manage the client yourself.

```python
from blocklog.async_client import AsyncBlocklogClient
from blocklog.config import BlocklogConfig

async def setup():
    config = BlocklogConfig(api_key="blk_...")
    client = AsyncBlocklogClient(config)
    await client.flush()
```

## Async Agents and Tools

The `@blocklog.agent` and `@blocklog.tool` decorators intelligently detect if the wrapped function is a coroutine and will safely await it, while still maintaining the context, duration, and error handling.

```python
import asyncio
import blocklog

blocklog.init()

@blocklog.tool
async def fetch_async_data(url: str) -> dict:
    # Simulate async network request
    await asyncio.sleep(0.5)
    return {"status": 200, "data": "async payload"}

@blocklog.agent(name="async-agent")
async def main_agent():
    data = await fetch_async_data("https://api.example.com")
    
    # Decisions work perfectly within async contexts
    with blocklog.decision(type="EVALUATE", asset="url") as d:
        d.record_input(data=data)
        d.record_output(valid=True)
        
    return data

if __name__ == "__main__":
    asyncio.run(main_agent())
```

## Context Management in Async
The SDK uses Python's native `contextvars` to maintain the `trace_id` and `session_id`. Because `contextvars` natively support `asyncio`, the context is perfectly maintained across `await` boundaries.

> [!WARNING]
> If you manually spawn background tasks using `asyncio.create_task()` or thread pools, the `contextvars` might not naturally propagate depending on your exact pattern. Ensure that tools and decisions are executed within the correct `contextvar` propagation chain.
