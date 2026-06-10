# Configuration

The SDK can be configured either programmatically via `blocklog.init()` or via environment variables.

## Programmatic Initialization

The `blocklog.init()` function configures the global client:

```python
import blocklog

blocklog.init(
    api_key="blk_12345",
    base_url="http://localhost:8000/api/v1",
    signing_key="ed25519_private_key_here",
    timeout=5.0,
    max_retries=5,
    debug=True
)
```

## Environment Variables

Every configuration option has a corresponding environment variable fallback. 

| Setting | Environment Variable | Default | Description |
| ------- | -------------------- | ------- | ----------- |
| `api_key` | `BLOCKLOG_API_KEY` | None | Your Blocklog API Key |
| `base_url` | `BLOCKLOG_BASE_URL` | `http://127.0.0.1:8000/api/v1` | Backend API URL |
| `signing_key` | `BLOCKLOG_SDK_SIGNING_KEY` | None | Ed25519 key for event payload signing |
| `timeout` | `BLOCKLOG_TIMEOUT` | `10` | HTTP request timeout in seconds |
| `max_retries` | `BLOCKLOG_MAX_RETRIES` | `3` | Max HTTP retry attempts |
| `batch_size` | `BLOCKLOG_BATCH_SIZE` | `100` | Number of events per batch |
| `flush_interval`| `BLOCKLOG_FLUSH_INTERVAL`| `2.0` | Seconds between automatic background flushes |

## Debug Mode

Passing `debug=True` to `init()` configures the internal Python `logging` to `DEBUG` level for the `blocklog` logger, causing every outbound request to be printed to `stderr`.
