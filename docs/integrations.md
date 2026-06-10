# Integrations

Blocklog comes with built-in instrumentation for popular AI frameworks. You can easily plug these into your Blocklog Client instance to trace execution flows, LLM calls, and tool usage across frameworks.

## LangChain

Blocklog provides a LangChain callback handler that automatically hooks into chains, LLMs, and tool executions.

```python
import blocklog

# 1. Initialize Blocklog
client = blocklog.init(api_key="blk_...")

# 2. Add LangChain instrumentation
client.instrument_langchain()
```

Under the hood, this sets up the `BlocklogLangChainCallbackHandler` which emits events for `agent.chain.started`, `agent.model.started`, `agent.tool.started`, and their respective completion events.

## LangGraph

LangGraph instrumentation can be enabled with a single method call:

```python
import blocklog

client = blocklog.init(api_key="blk_...")
client.instrument_langgraph()
```

*Note: LangGraph instrumentation currently sets up basic hooks and forwards payloads to the Blocklog ingest API.*

## OpenAI Agents

If you are using the OpenAI Agents SDK, you can instrument it automatically:

```python
import blocklog

client = blocklog.init(api_key="blk_...")
client.instrument_openai_agents()
```

*Note: Like LangGraph, this feature is currently in basic hook-forwarding mode.*
