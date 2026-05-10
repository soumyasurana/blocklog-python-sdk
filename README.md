# Blocklog SDKs

This repository now includes first-party reference SDKs:

- `SDKs/node/index.ts`
- `SDKs/python/blocklog_sdk.py`

Both clients:

- add a UTC timestamp when one is omitted
- retry transient failures
- chunk batch ingestion safely
- validate the log schema before sending
- promote explicit `idempotency_key` usage by default
