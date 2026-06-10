# Error Handling

Blocklog is designed to be resilient, failing gracefully so that your AI agents are not interrupted by telemetry or logging issues. However, when explicitly interacting with Layer 2 APIs or encountering terminal network conditions, you may need to handle exceptions.

## Exception Hierarchy

The Blocklog SDK relies heavily on the `httpx` HTTP client. Thus, the majority of network and authentication errors will surface as `httpx` exceptions (or `requests` exceptions if falling back to synchronous execution without `httpx`).

1. **`httpx.HTTPStatusError`**: Raised when the API returns a 4xx or 5xx status code (e.g., Authentication failure).
2. **`httpx.RequestError`**: Base class for network-related failures (DNS resolution, connection refused).
3. **`RuntimeError`**: Raised by the internal `RetryPolicy` if all retry attempts are exhausted.

## Common Errors

### Authentication Failures
If your `BLOCKLOG_API_KEY` is missing or invalid, any direct API call will fail with a `401 Unauthorized` or `403 Forbidden`.

```python
import httpx
import blocklog

try:
    blocklog.init(api_key="invalid_key")
    # This might fail immediately or on first flush depending on the endpoint
    result = blocklog.verify.decision("some_id")
except httpx.HTTPStatusError as exc:
    if exc.response.status_code == 401:
        print("Invalid Blocklog API Key!")
```

### Network Failures & Retries
By default, the SDK employs a `RetryPolicy` with exponential backoff (base delay of 0.25s) and up to 3 automatic retries for transient HTTP errors. If all 3 attempts fail, a `RuntimeError("retry failed")` will be raised.

### Recommended Try/Except Patterns
When calling blocking Layer 2 APIs like `.verify()` or `.compliance.generate()`, wrap them in appropriate error handling:

```python
import blocklog
import httpx

try:
    report = blocklog.compliance.generate(framework="SOC2")
except RuntimeError as exc:
    print(f"Failed to generate report after retries: {exc}")
except httpx.RequestError as exc:
    print(f"Network error communicating with Blocklog: {exc}")
```

> [!NOTE]
> Event ingestion (like `d.record_input()`) is handled asynchronously via an internal event buffer. Failures during buffer flushing do not crash your main application flow, ensuring tracing doesn't break production applications.
