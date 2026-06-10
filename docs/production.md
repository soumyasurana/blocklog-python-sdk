# Production Best Practices

Deploying Blocklog to production requires securing your API keys, managing secrets, and ensuring sensitive data is not leaked.

## Environment Variables and Secrets

Never hardcode your `BLOCKLOG_API_KEY` or `BLOCKLOG_SDK_SIGNING_KEY` directly in your Python code.

1. **API Key:** Use the `BLOCKLOG_API_KEY` environment variable.
2. **Signing Key:** If you are enabling cryptographic guarantees, use the `BLOCKLOG_SDK_SIGNING_KEY` environment variable to securely load your Ed25519 private key.

```bash
# Example .env or CI/CD secrets configuration
export BLOCKLOG_API_KEY="blk_live_..."
export BLOCKLOG_SDK_SIGNING_KEY="ed25519_..."
```

By doing this, your initialization code remains clean and environment-agnostic:
```python
import blocklog

# Automatically picks up environment variables
blocklog.init()
```

## PII Redaction and Middleware Hooks

If your agents process Personally Identifiable Information (PII) or secrets, you must prevent them from being sent to Blocklog.

You can use the `.add_hook()` method on the BlocklogClient to define a middleware that sanitizes every outbound event payload.

```python
import blocklog

client = blocklog.init()

def pii_redactor(payload: dict) -> dict:
    """A middleware hook to redact sensitive keys."""
    # Example logic: redact any value in the payload that might be a password
    if "data" in payload and isinstance(payload["data"], dict):
        if "password" in payload["data"]:
            payload["data"]["password"] = "[REDACTED]"
            
    return payload

# Register the hook
client.add_hook(pii_redactor)
```

## Retry and Timeout Configuration

In production, ensure your network operations are tuned to your infrastructure's requirements. If your agents run in strict serverless environments (like AWS Lambda or Vercel Edge functions), you might need to lower timeouts to prevent hanging functions.

```python
blocklog.init(
    timeout=5.0,       # Fail fast instead of waiting 10s
    max_retries=1,     # Reduce retries to prevent blocking lambda execution
)
```

## Deployment Recommendations

- **Serverless/Lambda**: Be aware that background buffer flushing might be suspended when a lambda goes to sleep. Explicitly call `client.flush()` at the end of your handler if necessary to ensure all events are sent before the environment is frozen.
- **Docker/Kubernetes**: Set `BLOCKLOG_BATCH_SIZE=100` and let the background buffering handle ingestion seamlessly.
