# Troubleshooting

This guide covers common issues encountered while using the Blocklog SDK.

## Authentication Issues

**Symptom:** API calls return HTTP 401 Unauthorized or 403 Forbidden.
**Resolution:** Ensure that `BLOCKLOG_API_KEY` is set in your environment variables, or passed directly to `blocklog.init(api_key="...")`. Check that your API key is active in the Blocklog Dashboard.

## Network and Connectivity Issues

**Symptom:** `httpx.ConnectError` or timeouts.
**Resolution:** 
- If you are running Blocklog self-hosted, ensure `BLOCKLOG_BASE_URL` is pointing to the correct ingest server.
- The default timeout is 10 seconds. You can increase this by passing `timeout=30.0` to `blocklog.init()`.
- The SDK utilizes a `RetryPolicy` with exponential backoff (default 3 retries). Ensure you have reliable internet connectivity.

## Import Errors

**Symptom:** `ModuleNotFoundError: No module named 'blocklog'`
**Resolution:** Make sure the SDK is installed in your active virtual environment:
```bash
pip install blocklog
```
Verify the installation by running `python -c "import blocklog; print(blocklog.__version__)"`.

## Context Loss in Async Workflows

**Symptom:** Decisions or tool calls are not inheriting the agent's `trace_id` or `session_id`.
**Resolution:** Blocklog relies on Python `contextvars` to maintain session state across execution boundaries. If you manually spin off background tasks or use threading, the context might be lost. Ensure you utilize native `async/await` which natively supports `contextvars`.

## Debugging Mode

If events are silently dropping, enable debug mode to see exactly what the transport layer is doing:
```python
blocklog.init(debug=True)
```
This will print all serialization and transport errors to `stderr`.
