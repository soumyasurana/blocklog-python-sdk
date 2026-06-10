# Decorators

Blocklog provides two primary decorators to easily instrument your AI workflows without boilerplate code.

## `@blocklog.agent`

**Purpose:** Traces the top-level execution of an AI agent or orchestrator.

**Signature:**
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

**Parameters:**
- `name`: Human-readable identifier. Defaults to the function name.
- `version`: Useful for tracking performance across prompt or logic updates.
- `tags` / `metadata`: Arbitrary categorizations.

**Example:**
```python
@blocklog.agent(name="market-analyst", version="2.1", tags=["prod"])
def market_analyst():
    # Code in here inherits the active trace ID
    pass
```
Note: Can also be used to decorate classes. It will wrap the `__init__` method to establish the session.

---

## `@blocklog.tool`

**Purpose:** Records a specific function call as a `TOOL_CALL` event. Captures arguments, return values, duration, and any exceptions. Inherits context from `@agent`.

**Signature:**
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

**Parameters:**
- `name`: Identifier for the tool.
- `schema`: A dictionary detailing the expected inputs, largely for dashboard documentation.

**Example:**
```python
@blocklog.tool(name="fetch-market-price", schema={"ticker": "str"})
def fetch_price(ticker: str) -> float:
    return 100.0
```
