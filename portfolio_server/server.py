"""Combined MCP server for all portfolio operations."""

from mcp.server.fastmcp import FastMCP
from portfolio_server import portfolio as portfolio_data
from portfolio_server.portfolio import (
    calculate_allocation,
    calculate_initial_value,
    get_price,
    get_price_with_source,
    get_asset_by_id,
    clear_price_cache,
    get_initial_holdings,
    reload_portfolio
)
import json
from datetime import datetime
import os

mcp = FastMCP("portfolio_mcp")

# State file for sharing between processes (in project root)
STATE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".portfolio_state.json")

# Store trades in memory for MVP
TRADES = []
CURRENT_HOLDINGS = None
ANALYSIS = {
    "portfolio_analysis": None,
    "target_allocation": None
}
# Session-level analysis snapshot (computed once, reused for consistency)
_ANALYSIS_SNAPSHOT = None


def save_state():
    """Save current state to file for cross-process sharing."""
    state = {
        "trades": TRADES,
        "holdings": CURRENT_HOLDINGS,
        "analysis": ANALYSIS
    }
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def load_state():
    """Load state from file."""
    global TRADES, CURRENT_HOLDINGS, ANALYSIS
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            state = json.load(f)
            TRADES = state.get("trades", [])
            CURRENT_HOLDINGS = state.get("holdings", {})
            ANALYSIS = state.get("analysis", {"portfolio_analysis": None, "target_allocation": None})


def reset_portfolio():
    """Reset to initial state.

    This reloads portfolio.json to ensure latest data is used.
    Note: Does NOT clear price cache to avoid rate limiting issues with Polygon API.
    """
    global CURRENT_HOLDINGS, TRADES, ANALYSIS, _ANALYSIS_SNAPSHOT
    # Reload portfolio from JSON file to get latest changes
    reload_portfolio()
    CURRENT_HOLDINGS = get_initial_holdings()
    TRADES = []
    ANALYSIS = {"portfolio_analysis": None, "target_allocation": None}
    _ANALYSIS_SNAPSHOT = None  # Clear snapshot so it's recomputed fresh
    # Don't clear price cache here - causes rate limiting issues
    save_state()


def init_portfolio():
    """Initialize portfolio - load existing state or reset to initial."""
    global CURRENT_HOLDINGS, TRADES
    if os.path.exists(STATE_FILE):
        try:
            load_state()
            if CURRENT_HOLDINGS:
                clear_price_cache()
                return
        except Exception:
            pass
    reset_portfolio()


init_portfolio()


@mcp.tool()
async def get_portfolio_state() -> dict:
    """Get current portfolio state with allocations using real-time prices.

    Returns:
        Complete portfolio data including current allocation and investor profile.
        Note: Target allocation is not included - the Financial Analyst agent
        should recommend one based on the investor profile and market conditions.
    """
    clear_price_cache()

    allocation, total_value = calculate_allocation(CURRENT_HOLDINGS)
    initial_value = calculate_initial_value()

    # Build holdings with current prices
    holdings_with_prices = {}
    for asset_id, data in CURRENT_HOLDINGS.items():
        current_price = get_price(asset_id)
        asset_def = get_asset_by_id(asset_id)
        holdings_with_prices[asset_id] = {
            **data,
            "current_price": current_price,
            "current_value": data["quantity"] * current_price,
            "tradeable": "polygon" in asset_def if asset_def else False
        }

    return {
        "name": portfolio_data.PORTFOLIO["name"],
        "initial_value": initial_value,
        "current_value": total_value,
        "holdings": holdings_with_prices,
        "current_allocation": allocation,
        "investor_profile": portfolio_data.PORTFOLIO["investor_profile"]
    }


@mcp.tool()
async def get_asset_price(asset_id: str) -> dict:
    """Get current market price for an asset.

    Args:
        asset_id: Asset identifier (e.g., 'amzn', 'paris_apt')

    Returns:
        Price info including source (Polygon API, Google Finance, Yahoo Finance, etc.)
    """
    clear_price_cache()

    asset = get_asset_by_id(asset_id)
    if not asset:
        return {"error": f"Asset '{asset_id}' not found"}

    price, source = get_price_with_source(asset_id)

    return {
        "asset_id": asset_id,
        "name": asset["name"],
        "price": price,
        "source": source,
        "ticker": asset.get("polygon", {}).get("ticker"),
        "tradeable": source in ["Polygon API", "Google Finance", "Yahoo Finance", "MarketWatch", "Brave Search"]
    }


@mcp.tool()
async def simulate_trade(
    action: str,
    asset_id: str,
    quantity: float,
    rationale: str
) -> dict:
    """Simulate a buy or sell trade.

    Args:
        action: "buy" or "sell"
        asset_id: Asset identifier (e.g., 'amzn', 'nvda', 'btc')
        quantity: Number of shares/units
        rationale: Reason for the trade

    Returns:
        Trade execution details
    """
    asset = get_asset_by_id(asset_id)
    if not asset:
        return {"error": f"Asset '{asset_id}' not found in portfolio definition"}

    clear_price_cache()

    # Get price with source to determine if tradeable
    price, source = get_price_with_source(asset_id)

    # Check if asset is tradeable (has market price from API or trusted search)
    tradeable_sources = ["Polygon API", "Google Finance", "Yahoo Finance", "MarketWatch", "Brave Search"]
    if source not in tradeable_sources:
        return {
            "error": f"Asset '{asset['name']}' cannot be traded (no market price available). "
                     f"Price source: {source}. Only assets with real-time market prices can be traded."
        }

    if action == "buy":
        cost = quantity * price
        fees = cost * portfolio_data.TRADING_FEE
        total_cost = cost + fees

        # Update holdings
        if asset_id in CURRENT_HOLDINGS:
            old_qty = CURRENT_HOLDINGS[asset_id]["quantity"]
            old_avg = CURRENT_HOLDINGS[asset_id]["avg_price"]
            new_qty = old_qty + quantity
            new_avg = ((old_qty * old_avg) + (quantity * price)) / new_qty
            CURRENT_HOLDINGS[asset_id]["quantity"] = new_qty
            CURRENT_HOLDINGS[asset_id]["avg_price"] = new_avg
        else:
            CURRENT_HOLDINGS[asset_id] = {
                "type": asset["type"],
                "quantity": quantity,
                "avg_price": price,
                "name": asset["name"]
            }

        result = {
            "action": "buy",
            "asset_id": asset_id,
            "name": asset["name"],
            "quantity": quantity,
            "price": price,
            "price_source": source,
            "fees": fees,
            "total_cost": total_cost,
            "rationale": rationale,
            "timestamp": datetime.now().isoformat()
        }

    elif action == "sell":
        if asset_id not in CURRENT_HOLDINGS:
            return {"error": f"No holdings of {asset['name']}"}
        if CURRENT_HOLDINGS[asset_id]["quantity"] < quantity:
            return {"error": f"Insufficient holdings of {asset['name']} "
                           f"(have {CURRENT_HOLDINGS[asset_id]['quantity']}, want to sell {quantity})"}

        proceeds = quantity * price
        fees = proceeds * portfolio_data.TRADING_FEE
        total_proceeds = proceeds - fees

        # Update holdings
        CURRENT_HOLDINGS[asset_id]["quantity"] -= quantity
        if CURRENT_HOLDINGS[asset_id]["quantity"] == 0:
            del CURRENT_HOLDINGS[asset_id]

        result = {
            "action": "sell",
            "asset_id": asset_id,
            "name": asset["name"],
            "quantity": quantity,
            "price": price,
            "price_source": source,
            "fees": fees,
            "total_proceeds": total_proceeds,
            "rationale": rationale,
            "timestamp": datetime.now().isoformat()
        }
    else:
        return {"error": f"Invalid action: {action}. Use 'buy' or 'sell'"}

    TRADES.append(result)
    save_state()
    print(f"Trade executed: {action.upper()} {quantity} {asset['name']} @ ${price:.2f}")
    return result


@mcp.tool()
async def get_trade_history() -> list:
    """Get all simulated trades.

    Returns:
        List of all trades executed
    """
    return TRADES


@mcp.tool()
async def reset_portfolio_state() -> dict:
    """Reset portfolio to initial state, clearing all trades.

    Returns:
        Confirmation with initial holdings
    """
    reset_portfolio()
    return {
        "status": "reset",
        "message": "Portfolio reset to initial state",
        "holdings": CURRENT_HOLDINGS
    }


@mcp.tool()
async def calculate_performance() -> dict:
    """Calculate portfolio performance metrics.

    Returns:
        Performance summary with initial vs current values
    """
    clear_price_cache()

    _, current_value = calculate_allocation(CURRENT_HOLDINGS)

    initial = calculate_initial_value()
    change = current_value - initial
    change_pct = (change / initial) * 100 if initial > 0 else 0

    total_fees = sum(t.get("fees", 0) for t in TRADES)

    return {
        "initial_value": initial,
        "current_value": current_value,
        "absolute_change": change,
        "percentage_change": change_pct,
        "total_trades": len(TRADES),
        "total_fees": total_fees,
        "net_change": change - total_fees
    }


@mcp.tool()
async def list_tradeable_assets() -> list:
    """List all assets that can be traded (have market price from Polygon or trusted sources).

    Returns:
        List of tradeable assets with their IDs, current prices, and price sources
    """
    clear_price_cache()
    tradeable_sources = ["Polygon API", "Google Finance", "Yahoo Finance", "MarketWatch", "Brave Search"]
    tradeable = []

    for asset in portfolio_data.PORTFOLIO["assets"]:
        price, source = get_price_with_source(asset["id"])
        if source in tradeable_sources:
            tradeable.append({
                "asset_id": asset["id"],
                "name": asset["name"],
                "type": asset["type"],
                "ticker": asset.get("polygon", {}).get("ticker"),
                "current_price": price,
                "price_source": source
            })
    return tradeable


@mcp.tool()
async def generate_portfolio_analysis() -> dict:
    """Generate portfolio analysis with exact computed values.

    Returns structured analysis with pre-computed numbers that should be used
    directly without recalculation. The LLM should add qualitative commentary
    to these exact values.

    This also initializes the session snapshot used by save_analysis() to ensure
    all analysis sections show consistent values.

    Returns:
        Dictionary with exact computed metrics for portfolio analysis
    """
    # Clear and recompute snapshot to ensure fresh, consistent values
    clear_analysis_snapshot()
    clear_price_cache()

    # Get or create the snapshot (this will compute fresh values)
    snapshot = get_analysis_snapshot()

    # Ensure all standard classes are present in allocation
    allocation = snapshot["allocation"].copy()
    for cls in ["stock", "bond", "crypto", "real_estate", "cash"]:
        if cls not in allocation:
            allocation[cls] = 0.0

    return {
        "total_value": snapshot["total_value"],
        "total_value_formatted": snapshot["total_value_formatted"],
        "initial_value": snapshot["initial_value"],
        "initial_value_formatted": f"€{snapshot['initial_value']:,.2f}",
        "cost_basis": snapshot["cost_basis"],
        "cost_basis_formatted": f"€{snapshot['cost_basis']:,.2f}",
        "performance": {
            "absolute_change": snapshot["performance_absolute"],
            "percentage_change": snapshot["performance_percentage"],
            "formatted": snapshot["performance_formatted"]
        },
        "allocation_by_class": allocation,
        "allocation_formatted": ", ".join(
            f"{cls}: {pct}%" for cls, pct in sorted(allocation.items(), key=lambda x: -x[1]) if pct > 0
        ),
        "holdings_count": len(CURRENT_HOLDINGS),
        "instruction": "USE THESE EXACT VALUES in your analysis. Do NOT recalculate or approximate."
    }


def get_analysis_snapshot() -> dict:
    """Get or create a consistent analysis snapshot for the current session.

    This ensures all analysis uses the same price data, avoiding inconsistencies
    when prices change between API calls.
    """
    global _ANALYSIS_SNAPSHOT

    if _ANALYSIS_SNAPSHOT is None:
        # Compute fresh snapshot (prices already in cache from generate_portfolio_analysis)
        allocation, total_value = calculate_allocation(CURRENT_HOLDINGS)
        initial_value = calculate_initial_value()

        # Also compute cost basis of current holdings for comparison
        cost_basis = sum(
            data["quantity"] * data["avg_price"]
            for data in CURRENT_HOLDINGS.values()
        )

        change_from_original = total_value - initial_value
        change_pct_original = (change_from_original / initial_value) * 100 if initial_value > 0 else 0

        # Calculate allocation by asset class
        class_allocation = {}
        for asset_id, data in CURRENT_HOLDINGS.items():
            asset_type = data.get("type", "other")
            current_price = get_price(asset_id)
            asset_value = data["quantity"] * current_price
            class_allocation[asset_type] = class_allocation.get(asset_type, 0) + asset_value

        class_percentages = {}
        for asset_type, value in class_allocation.items():
            class_percentages[asset_type] = round((value / total_value) * 100, 1) if total_value > 0 else 0

        _ANALYSIS_SNAPSHOT = {
            "total_value": round(total_value, 2),
            "total_value_formatted": f"€{total_value:,.2f}",
            "initial_value": round(initial_value, 2),
            "cost_basis": round(cost_basis, 2),
            "performance_absolute": round(change_from_original, 2),
            "performance_percentage": round(change_pct_original, 2),
            "performance_formatted": f"{'+' if change_from_original >= 0 else ''}€{change_from_original:,.2f} ({change_pct_original:+.2f}%)",
            "allocation": class_percentages
        }

    return _ANALYSIS_SNAPSHOT


def clear_analysis_snapshot():
    """Clear the analysis snapshot to force recomputation."""
    global _ANALYSIS_SNAPSHOT
    _ANALYSIS_SNAPSHOT = None


@mcp.tool()
async def save_analysis(
    analysis_type: str,
    commentary: str
) -> dict:
    """Save analysis with consistent computed metrics plus LLM commentary.

    Uses a session-level price snapshot to ensure all analysis shows consistent
    values (same total_value, allocation, performance across all sections).

    Args:
        analysis_type: Either "portfolio_analysis" or "target_allocation"
        commentary: Qualitative commentary/rationale (numbers will be auto-added)

    Returns:
        Confirmation of saved analysis with computed values
    """
    global ANALYSIS
    if analysis_type not in ["portfolio_analysis", "target_allocation"]:
        return {"error": f"Invalid analysis_type: {analysis_type}. Use 'portfolio_analysis' or 'target_allocation'"}

    # Use consistent snapshot (computed once per session)
    snapshot = get_analysis_snapshot()

    # Store structured data with consistent values
    ANALYSIS[analysis_type] = {
        "computed": snapshot.copy(),
        "commentary": commentary
    }
    save_state()
    return {"status": "saved", "analysis_type": analysis_type, "computed_values": snapshot}


@mcp.resource("portfolio://current")
async def read_portfolio_resource() -> str:
    """MCP resource to access current portfolio state."""
    state = await get_portfolio_state()
    return json.dumps(state, indent=2)


if __name__ == "__main__":
    mcp.run(transport='stdio')
