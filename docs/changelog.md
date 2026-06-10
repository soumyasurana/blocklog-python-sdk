# Changelog

All notable changes to the Blocklog Python SDK will be documented in this file.

## [0.2.0] - Initial Public Release

### Added
- Core agent instrumentation decorators (`@blocklog.agent`, `@blocklog.tool`).
- `blocklog.decision()` context manager for recording AI decision outcomes.
- HTTP transport layer with automatic retry (`RetryPolicy`) and batched event buffering (`EventBuffer`).
- Integrations module with auto-instrumentation for LangChain, LangGraph, and OpenAI Agents.
- HITL Approval workflows (`blocklog.approval.request`).
- Forensic Replay factory (`blocklog.replay`).
- Incident management lifecycle API (`blocklog.incident`).
- Cryptographic verification helpers (`blocklog.verify`).
- Compliance report generators (`blocklog.compliance`).
- Code examples (`01_quickstart.py`, `02_stock_trading_agent.py`, `03_multi_agent_workflow.py`).

### Dependencies
- Requires Python >= 3.11
- `httpx` >= 0.27, < 1.0
- `pydantic` >= 2.8, < 3.0
