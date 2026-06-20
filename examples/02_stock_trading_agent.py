"""
Example 1: Stock Trading Agent
================================
Demonstrates the core Blocklog SDK workflow for a simple AI trading agent:

    blocklog.init()       → configure SDK
    @blocklog.agent       → trace the agent
    @blocklog.tool        → record tool calls
    blocklog.decision()   → record a BUY decision with inputs/outputs
    blocklog.verify       → cryptographically verify the recorded decision

Run:
    BLOCKLOG_API_KEY=blk_... python 01_stock_trading_agent.py
"""
import os
import random
from datetime import datetime

import blocklog

# ── 1. Initialise the SDK ──────────────────────────────────────────────────────
blocklog.init(api_key=os.environ.get("BLOCKLOG_API_KEY", "blk_demo_key"))

print("✦ Blocklog SDK initialized")
print(f"  version: {blocklog.__version__}")
print()


# ── 2. Define tools ────────────────────────────────────────────────────────────
@blocklog.tool(name="fetch-market-price", tags=["market-data"])
def fetch_price(ticker: str) -> float:
    """Simulated price feed."""
    prices = {"TSLA": 412.50, "AAPL": 189.30, "NVDA": 875.10}
    return prices.get(ticker, random.uniform(100, 500))


@blocklog.tool(name="fetch-volume", tags=["market-data"])
def fetch_volume(ticker: str) -> int:
    """Simulated volume data."""
    return random.randint(500_000, 5_000_000)


@blocklog.tool(name="place-order", tags=["execution"])
def place_order(ticker: str, qty: int, price: float) -> dict:
    """Simulated order placement."""
    order_id = f"ord_{random.randint(10000, 99999)}"
    print(f"  → Placing {qty}x {ticker} @ ${price:.2f} → Order {order_id}")
    return {
        "order_id": order_id,
        "ticker": ticker,
        "qty": qty,
        "filled_at": price * 1.001,   # slippage
        "value": price * qty,
        "filled_at_ts": datetime.utcnow().isoformat(),
    }


# ── 3. Define the agent ────────────────────────────────────────────────────────
@blocklog.agent(name="stock-trader", version="1.0", tags=["prod", "equities"])
def run_trading_agent(ticker: str = "TSLA") -> dict:
    """AI trading agent that analyses market conditions and places orders."""
    print(f"  Agent started for: {ticker}")

    # Fetch market data (recorded as TOOL_CALL events)
    price  = fetch_price(ticker)
    volume = fetch_volume(ticker)

    # Momentum signal (simplified)
    momentum_signal = "BUY" if volume > 2_000_000 else "HOLD"
    confidence      = round(random.uniform(0.7, 0.98), 2)

    print(f"  Price: ${price:.2f} | Volume: {volume:,} | Signal: {momentum_signal} | Confidence: {confidence}")

    if momentum_signal != "BUY":
        print("  No BUY signal — holding position.")
        return {"action": "HOLD", "ticker": ticker}

    # ── 4. Record the decision ─────────────────────────────────────────────────
    with blocklog.decision(
        type="BUY",
        asset=ticker,
        confidence=confidence,
        metadata={"strategy": "momentum", "market_regime": "bull"},
    ) as d:
        # Record what the model considered
        d.record_input(
            price=price,
            volume=volume,
            momentum_signal=momentum_signal,
            market_open=True,
        )
        d.tag("high-conviction", "momentum-strategy")

        # Execute the trade
        qty   = int(10_000 / price)   # invest ~$10k
        order = place_order(ticker, qty, price)

        # Record what happened
        d.record_output(
            order_id=order["order_id"],
            filled_at=order["filled_at"],
            qty=order["qty"],
            total_value=order["value"],
        )

        # Request approval for large trades
        if order["value"] > 8_000:
            print("  ⚠️  Large trade — requesting approval...")
            d.request_approval(
                reason=f"Trade value ${order['value']:.2f} exceeds $8k threshold",
                reviewer="risk-team@fund.com",
            )

        decision_id = d.id
        print(f"  ✓ Decision recorded: {decision_id}")

    # ── 5. Verify the decision ────────────────────────────────────────────────
    print("\n  Verifying decision ")
    try:
        result = blocklog.verify.decision(decision_id)
        print(f"  ✓ Verification status: {result.get('status', 'verified')}")
    except Exception as e:
        print(f"  (verification skipped in demo mode: {e})")

    return {"action": "BUY", "ticker": ticker, "order": order, "decision_id": decision_id}


# ── 6. Run the agent ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("  Blocklog Example 1: Stock Trading Agent")
    print("=" * 60)
    print()

    result = run_trading_agent("TSLA")

    print()
    print("=" * 60)
    print("  Result:", result)
    print()
    print("  ✦ Open your Blocklog dashboard to see:")
    print("    - The decision record with inputs/outputs")
    print("    - The tool calls (fetch-market-price, fetch-volume, place-order)")
    print("    - The full agent trace")
    print("=" * 60)
