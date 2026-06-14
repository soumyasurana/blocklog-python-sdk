# Blocklog Python SDK

**Infrastructure for AI Decision-Making**

Blocklog provides the infrastructure to record, audit, and investigate AI decisions. It allows you to wrap your AI agents, capture their context and tool calls, and record structured decisions that are cryptographically signed and verifiable.

## What problem it solves

When AI agents make decisions in production—like executing a trade, granting access, or synthesizing data—it is difficult to track exactly *why* a decision was made. Logs are scattered, context is lost, and inputs/outputs are hard to correlate. 

Blocklog solves this by:
1. **Tracing AI Agents**: Capturing the exact state, tool inputs/outputs, and prompts.
2. **Recording Decisions**: Creating a structured, auditable record of AI actions.
3. **Providing Verifiability**: Signing decisions cryptographically with Ed25519.
4. **Enabling Human-in-the-Loop (HITL)**: Requesting approvals for high-stakes decisions seamlessly.

## Documentation Index

Please navigate the documentation in the following logical flow:

1. [Installation](installation.md)
2. [Quickstart](quickstart.md)
3. [Core Concepts](concepts.md)
4. [Tracing](tracing.md)
5. [Decisions](decisions.md)
6. [Decorators](decorators.md)
7. [Integrations](integrations.md)
8. [Examples](examples.md)
9. [Configuration](configuration.md)
10. [Production Best Practices](production.md)
11. [Performance & Behavior](performance.md)
12. [Error Handling](error-handling.md)
13. [Async Usage](async.md)
14. [Migration Guides](migration.md)
15. [API Reference](api-reference.md)
16. [Troubleshooting](troubleshooting.md)
17. [Changelog](changelog.md)
