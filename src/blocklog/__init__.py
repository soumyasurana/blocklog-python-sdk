"""
blocklog — Infrastructure for AI Decision-Making
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Record every decision your AI agents make.

Quick start::

    import blocklog

    blocklog.init(api_key="blk_...")

    @blocklog.agent(name="stock-trader")
    def run():
        with blocklog.decision(type="BUY", asset="TSLA") as d:
            price = fetch_price("TSLA")
            d.record_input(price=price)

            order = place_order("TSLA", qty=100)
            d.record_output(order_id=order.id)

Public API
----------
``blocklog.init()``         — configure the SDK
``@blocklog.agent``         — trace an AI agent function or class
``@blocklog.tool``          — record a tool call with inputs/outputs
``blocklog.decision()``     — context manager for AI decision recording
"""
from __future__ import annotations

# ── Tier 1: Getting Started ───────────────────────────────────────────────────
from blocklog._init_fn import init
from blocklog.decorators.agent import agent
from blocklog.decorators.tool import tool
from blocklog.managers.decision import decision, DecisionContext

# ── Tier 2: Governance & Investigation ────────────────────────────────────────
from blocklog import approval      # noqa: E402
from blocklog.replay import replay # noqa: E402

__version__ = "0.2.2"

# Expose only the minimum concepts required to understand Blocklog.
# Advanced features (incident, verify, compliance, clients) are hidden
# from quickstart autocomplete but remain accessible via their submodules.
__all__ = [
    # Tier 1
    "init",
    "agent",
    "tool",
    "decision",
    "DecisionContext",
    # Tier 2
    "approval",
    "replay",
]

def __getattr__(name: str):
    # Backward compatibility for direct client access (hidden from autocomplete)
    if name == "BlocklogClient":
        from blocklog.client import BlocklogClient
        return BlocklogClient
    if name == "AsyncBlocklogClient":
        from blocklog.async_client import AsyncBlocklogClient
        return AsyncBlocklogClient
    if name == "BlocklogConfig":
        from blocklog.config import BlocklogConfig
        return BlocklogConfig
    if name == "agent_session":
        from blocklog.context.managers import agent_session
        return agent_session
    if name == "get_context":
        from blocklog.context.vars import get_context
        return get_context
    if name == "set_context":
        from blocklog.context.vars import set_context
        return set_context
    raise AttributeError(f"module 'blocklog' has no attribute {name!r}")
