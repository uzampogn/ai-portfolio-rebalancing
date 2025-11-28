# Portfolio Rebalancing MVP - Simplified 3-Agent Plan

## Goal: Working MVP in 5.5-6.5 hours (with 1 hour buffer for debugging)

## Core MVP Features (Must Have)
1. ✅ Three-agent system (Researcher, Financial Analyst, Trader)
2. ✅ Single portfolio with assets (stocks, bonds, crypto, real estate)
3. ✅ Investor profile (risk level, time horizon, constraints)
4. ✅ **Real-time pricing via Polygon API**
5. ✅ Web research for market conditions
6. ✅ Financial analysis with rebalancing recommendations
7. ✅ Simulate trades with fees
8. ✅ Report trading activity and performance change
9. ✅ Simple Gradio UI showing before/after comparison

## Deferred to V2 (Nice to Have)
- ❌ Database-backed tracing/logging (use print statements)
- ❌ Real-time UI updates (use manual refresh)
- ❌ Multiple portfolios
- ❌ Chat interface with agents
- ❌ Formal pytest suite (manual testing)
- ❌ CLI tool

---

## Simplified 3-Agent Architecture

```
┌─────────────────────────────────────────────┐
│           Trader Agent (Orchestrator)        │
│                                              │
│  Tools:                                      │
│  - Researcher (agent as tool)                │
│  - FinancialAnalyst (agent as tool)          │
│  - Portfolio tools (buy/sell/get state)     │
│  - Polygon API (real-time prices)           │
│                                              │
│  ┌────────────────────────────────────────┐ │
│  │   Researcher Agent                     │ │
│  │   - Web search (Brave)                 │ │
│  │   - Content fetching                   │ │
│  │   - Market research                    │ │
│  └────────────────────────────────────────┘ │
│                                              │
│  ┌────────────────────────────────────────┐ │
│  │   Financial Analyst Agent              │ │
│  │   - Portfolio analysis tools           │ │
│  │   - Calculate deviations               │ │
│  │   - Recommend strategy                 │ │
│  └────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘

Data Strategy:
- Static portfolio composition (mock_data.py)
- Real prices from Polygon API
- In-memory state (no database)
```

### Agent Roles:
1. **Researcher**: Searches web for market conditions, news, trends for specific asset classes
2. **Financial Analyst**: Analyzes portfolio state, calculates deviations, recommends rebalancing strategy
3. **Trader**: Main orchestrator that coordinates the other two agents and executes trades

---

## Phase 1: Minimal Setup (35 minutes)

### 1.1 Project Structure
```
trader_app/
├── agents/
│   ├── __init__.py
│   ├── researcher.py         # Researcher agent
│   ├── financial_analyst.py  # Financial analyst agent
│   └── trader.py             # Main trader agent (orchestrator)
├── portfolio_mcp.py          # Single MCP server (all tools)
├── app.py                    # Gradio UI
├── mock_data.py              # Sample portfolio data + Polygon integration
├── .env                      # API keys
└── README.md                 # Basic docs
```

### 1.2 Mock Data with Polygon API (`mock_data.py`)

```python
"""Sample portfolio data for MVP with real Polygon API pricing."""

from polygon import RESTClient
from functools import lru_cache
import os
from dotenv import load_dotenv

load_dotenv(override=True)

# Initialize Polygon client
polygon_client = RESTClient(api_key=os.getenv("POLYGON_API_KEY"))

SAMPLE_PORTFOLIO = {
    "name": "Balanced Portfolio",
    "initial_value": 100000.0,
    "assets": [
        {"symbol": "VTI", "type": "stock", "quantity": 200, "purchase_price": 220.0},
        {"symbol": "AGG", "type": "bond", "quantity": 300, "purchase_price": 103.0},
        {"symbol": "BTC-USD", "type": "crypto", "quantity": 0.3, "purchase_price": 45000.0},
        {"symbol": "VNQ", "type": "real_estate", "quantity": 100, "purchase_price": 115.0}  # REIT ETF
    ],
    "investor_profile": {
        "risk_level": "moderate",
        "time_horizon": 10,  # years
        "constraints": ["no_leverage", "keep_some_cash"],
        "target_allocation": {
            "stock": 50,
            "bond": 30,
            "crypto": 10,
            "real_estate": 10
        }
    }
}

TRADING_FEE = 0.002  # 0.2% per trade

@lru_cache(maxsize=100)
def get_price(symbol: str) -> float:
    """Get real-time price from Polygon API.

    Args:
        symbol: Asset symbol (VTI, AGG, BTC-USD, VNQ)

    Returns:
        Current price from Polygon API

    Note:
        Uses LRU cache to avoid excessive API calls
    """
    try:
        # Handle crypto differently (uses X: prefix)
        if symbol.endswith("-USD"):
            # Crypto ticker format for Polygon
            ticker = f"X:{symbol.replace('-USD', 'USD')}"
        else:
            # Stock/ETF ticker format
            ticker = symbol

        # Get last trade
        last_trade = polygon_client.get_last_trade(ticker)

        if last_trade:
            return last_trade.price
        else:
            print(f"⚠️  Warning: No price data for {symbol}, using fallback")
            return get_fallback_price(symbol)

    except Exception as e:
        print(f"⚠️  Error fetching price for {symbol}: {e}")
        return get_fallback_price(symbol)

def get_fallback_price(symbol: str) -> float:
    """Fallback prices if Polygon API fails.

    Args:
        symbol: Asset symbol

    Returns:
        Estimated price based on typical ranges
    """
    fallback_prices = {
        "VTI": 225.0,
        "AGG": 102.0,
        "BTC-USD": 48000.0,
        "VNQ": 90.0,
    }
    return fallback_prices.get(symbol, 100.0)

def calculate_allocation(assets):
    """Calculate current allocation percentages using real prices.

    Args:
        assets: List of asset dictionaries with symbol, type, quantity

    Returns:
        Tuple of (allocation_dict, total_value)
    """
    total_value = 0.0
    allocation = {}

    # Calculate total value
    for asset in assets:
        current_price = get_price(asset["symbol"])
        asset_value = asset["quantity"] * current_price
        total_value += asset_value

    # Calculate percentages by type
    for asset in assets:
        current_price = get_price(asset["symbol"])
        asset_value = asset["quantity"] * current_price
        asset_type = asset["type"]

        if asset_type in allocation:
            allocation[asset_type] += (asset_value / total_value) * 100
        else:
            allocation[asset_type] = (asset_value / total_value) * 100

    return allocation, total_value

def clear_price_cache():
    """Clear the price cache to force fresh API calls."""
    get_price.cache_clear()
```

### 1.3 Environment Setup

```bash
# .env
ANTHROPIC_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
BRAVE_API_KEY=your_key_here
POLYGON_API_KEY=your_polygon_key_here
```

### 1.4 Install Dependencies

```bash
# Install required packages
uv pip install agents fastmcp gradio pandas plotly python-dotenv polygon-api-client
```

### 1.5 Checklist
- [ ] Create project structure with agents/ folder
- [ ] Create mock_data.py with Polygon integration
- [ ] Create .env with all API keys (including Polygon)
- [ ] Verify uv environment is ready
- [ ] Test Polygon API connection with a simple script

---

## Phase 2: Single MCP Server (45 minutes)

### 2.1 Combined Portfolio MCP (`portfolio_mcp.py`)

```python
"""Combined MCP server for all portfolio operations."""

from mcp.server.fastmcp import FastMCP
from mock_data import (
    SAMPLE_PORTFOLIO,
    calculate_allocation,
    get_price,
    clear_price_cache,
    TRADING_FEE
)
import json
from datetime import datetime

mcp = FastMCP("portfolio_mcp")

# Store trades in memory for MVP
TRADES = []
CURRENT_HOLDINGS = None

def reset_portfolio():
    """Reset to initial state and clear price cache."""
    global CURRENT_HOLDINGS, TRADES
    CURRENT_HOLDINGS = {
        asset["symbol"]: {
            "type": asset["type"],
            "quantity": asset["quantity"],
            "avg_price": asset["purchase_price"]
        }
        for asset in SAMPLE_PORTFOLIO["assets"]
    }
    TRADES = []
    # Clear price cache to get fresh prices
    clear_price_cache()

reset_portfolio()

@mcp.tool()
async def get_portfolio_state() -> dict:
    """Get current portfolio state with allocations using real-time prices.

    Returns:
        Complete portfolio data including current allocation vs target
    """
    # Force fresh price fetch for accurate state
    clear_price_cache()

    allocation, total_value = calculate_allocation([
        {
            "symbol": symbol,
            "type": data["type"],
            "quantity": data["quantity"]
        }
        for symbol, data in CURRENT_HOLDINGS.items()
    ])

    target = SAMPLE_PORTFOLIO["investor_profile"]["target_allocation"]

    return {
        "name": SAMPLE_PORTFOLIO["name"],
        "initial_value": SAMPLE_PORTFOLIO["initial_value"],
        "current_value": total_value,
        "holdings": CURRENT_HOLDINGS,
        "current_allocation": allocation,
        "target_allocation": target,
        "investor_profile": SAMPLE_PORTFOLIO["investor_profile"],
        "deviation": {
            asset_type: target.get(asset_type, 0) - allocation.get(asset_type, 0)
            for asset_type in set(list(target.keys()) + list(allocation.keys()))
        }
    }

@mcp.tool()
async def get_asset_price(symbol: str) -> float:
    """Get current market price for an asset from Polygon API.

    Args:
        symbol: Asset symbol (VTI, AGG, BTC-USD, VNQ)

    Returns:
        Current real-time price from Polygon
    """
    # Don't use cache for explicit price checks
    clear_price_cache()
    price = get_price(symbol)
    print(f"💰 Current price for {symbol}: ${price:.2f}")
    return price

@mcp.tool()
async def simulate_trade(
    action: str,
    symbol: str,
    quantity: float,
    rationale: str
) -> dict:
    """Simulate a buy or sell trade using real-time prices.

    Args:
        action: "buy" or "sell"
        symbol: Asset symbol
        quantity: Number of shares/units
        rationale: Reason for the trade

    Returns:
        Trade execution details
    """
    # Get fresh price for trade execution
    clear_price_cache()
    price = get_price(symbol)

    if action == "buy":
        cost = quantity * price
        fees = cost * TRADING_FEE
        total_cost = cost + fees

        # Update holdings
        if symbol in CURRENT_HOLDINGS:
            old_qty = CURRENT_HOLDINGS[symbol]["quantity"]
            old_avg = CURRENT_HOLDINGS[symbol]["avg_price"]
            new_qty = old_qty + quantity
            new_avg = ((old_qty * old_avg) + (quantity * price)) / new_qty
            CURRENT_HOLDINGS[symbol]["quantity"] = new_qty
            CURRENT_HOLDINGS[symbol]["avg_price"] = new_avg
        else:
            asset_type = next(
                (a["type"] for a in SAMPLE_PORTFOLIO["assets"] if a["symbol"] == symbol),
                "unknown"
            )
            CURRENT_HOLDINGS[symbol] = {
                "type": asset_type,
                "quantity": quantity,
                "avg_price": price
            }

        result = {
            "action": "buy",
            "symbol": symbol,
            "quantity": quantity,
            "price": price,
            "fees": fees,
            "total_cost": total_cost,
            "rationale": rationale,
            "timestamp": datetime.now().isoformat()
        }

    elif action == "sell":
        if symbol not in CURRENT_HOLDINGS or CURRENT_HOLDINGS[symbol]["quantity"] < quantity:
            return {"error": f"Insufficient holdings of {symbol}"}

        proceeds = quantity * price
        fees = proceeds * TRADING_FEE
        total_proceeds = proceeds - fees

        # Update holdings
        CURRENT_HOLDINGS[symbol]["quantity"] -= quantity
        if CURRENT_HOLDINGS[symbol]["quantity"] == 0:
            del CURRENT_HOLDINGS[symbol]

        result = {
            "action": "sell",
            "symbol": symbol,
            "quantity": quantity,
            "price": price,
            "fees": fees,
            "total_proceeds": total_proceeds,
            "rationale": rationale,
            "timestamp": datetime.now().isoformat()
        }
    else:
        return {"error": f"Invalid action: {action}"}

    TRADES.append(result)
    print(f"✅ Trade executed: {action.upper()} {quantity} {symbol} @ ${price:.2f}")
    return result

@mcp.tool()
async def get_trade_history() -> list:
    """Get all simulated trades.

    Returns:
        List of all trades executed
    """
    return TRADES

@mcp.tool()
async def calculate_performance() -> dict:
    """Calculate portfolio performance metrics using real-time prices.

    Returns:
        Performance summary with initial vs current values
    """
    clear_price_cache()

    _, current_value = calculate_allocation([
        {
            "symbol": symbol,
            "type": data["type"],
            "quantity": data["quantity"]
        }
        for symbol, data in CURRENT_HOLDINGS.items()
    ])

    initial = SAMPLE_PORTFOLIO["initial_value"]
    change = current_value - initial
    change_pct = (change / initial) * 100

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

@mcp.resource("portfolio://current")
async def read_portfolio_resource() -> str:
    """MCP resource to access current portfolio state."""
    state = await get_portfolio_state()
    return json.dumps(state, indent=2)

if __name__ == "__main__":
    mcp.run(transport='stdio')
```

### 2.2 Test MCP Server with Real Prices

```bash
# Test the server and verify Polygon API connection
uv run portfolio_mcp.py
```

**Manual Test Script** (`test_polygon.py`):
```python
"""Quick test to verify Polygon API integration."""
from mock_data import get_price, SAMPLE_PORTFOLIO

print("Testing Polygon API integration...")
print("=" * 50)

for asset in SAMPLE_PORTFOLIO["assets"]:
    symbol = asset["symbol"]
    price = get_price(symbol)
    print(f"{symbol:12} ${price:>10,.2f}")

print("=" * 50)
print("✓ Polygon API integration working!")
```

Run: `uv run test_polygon.py`

### 2.3 Checklist
- [ ] Implement portfolio_mcp.py with Polygon integration
- [ ] Test MCP server starts without errors
- [ ] Verify Polygon API returns real prices
- [ ] Test price caching works correctly
- [ ] Verify fallback prices work if API fails
- [ ] Test get_portfolio_state returns correct data with real prices

---

## Phase 3: Three-Agent System (75 minutes)

### 3.1 Researcher Agent (`agents/researcher.py`)

```python
"""Researcher agent for market research."""

from agents import Agent
from datetime import datetime

def get_researcher_instructions() -> str:
    """Instructions for the Researcher agent."""
    return f"""You are a Market Research Specialist AI agent.

Current Date: {datetime.now().strftime("%Y-%m-%d")}

Your role is to research market conditions, trends, and news for specific asset classes to inform investment decisions.

## Your Responsibilities:

1. **Research Asset Classes**: When asked about stocks, bonds, crypto, or real estate:
   - Search for current market conditions
   - Find recent news and trends
   - Identify key risks and opportunities
   - Look for macroeconomic factors affecting the asset class

2. **Provide Evidence-Based Insights**:
   - Cite sources when possible
   - Focus on recent information (last 30 days preferred)
   - Distinguish between facts and opinions
   - Highlight both positive and negative factors

3. **Be Concise**: Summarize findings in clear, actionable insights

## Available Tools:
- Web search (Brave Search)
- Content fetching from URLs

## Example Questions You'll Receive:
- "Research current market conditions for technology stocks and bonds"
- "What are the trends in cryptocurrency markets?"
- "Are there any major events affecting real estate investments?"

Provide thorough but concise research that helps inform rebalancing decisions.
"""

def create_researcher_agent(model_name: str = "gpt-4o-mini") -> Agent:
    """Create the Researcher agent.

    Args:
        model_name: LLM model to use

    Returns:
        Configured Researcher agent
    """
    return Agent(
        name="Researcher",
        instructions=get_researcher_instructions(),
        model=model_name,
    )
```

### 3.2 Financial Analyst Agent (`agents/financial_analyst.py`)

```python
"""Financial Analyst agent for portfolio analysis."""

from agents import Agent
from datetime import datetime

def get_analyst_instructions() -> str:
    """Instructions for the Financial Analyst agent."""
    return f"""You are an expert Financial Analyst AI agent specializing in portfolio analysis and rebalancing strategies.

Current Date: {datetime.now().strftime("%Y-%m-%d")}

Your role is to analyze portfolios and recommend optimal rebalancing strategies based on investor profiles and market research.

## Your Responsibilities:

1. **Portfolio Analysis**:
   - Analyze current allocation vs target allocation
   - Calculate deviations for each asset class
   - Assess portfolio performance
   - Identify overweight and underweight positions

2. **Strategy Recommendations**:
   - Recommend specific buy/sell actions to reach target allocation
   - Respect investor constraints (risk level, time horizon, restrictions)
   - Consider transaction fees (0.2% per trade)
   - Optimize for minimal trading while achieving rebalancing goals

3. **Risk Assessment**:
   - Evaluate if current allocation matches investor risk profile
   - Consider market conditions from research findings
   - Balance short-term market conditions with long-term strategy

## Available Tools:
- get_portfolio_state: See current portfolio, allocations, and deviations (uses REAL-TIME prices)
- get_asset_price: Check current real-time prices for assets from Polygon API
- calculate_performance: Get performance metrics

## Guidelines:
- Aim to get within 2% of target allocation for each asset class
- Minimize number of trades (fewer trades = lower fees)
- Larger rebalancing trades are more efficient than many small trades
- Always provide clear rationale for recommendations
- Consider the investor's time horizon (longer = can tolerate more volatility)
- Prices are fetched in real-time from Polygon API, so your analysis reflects current market conditions

Provide specific, actionable trade recommendations with clear reasoning.
"""

def create_analyst_agent(model_name: str = "gpt-4o-mini") -> Agent:
    """Create the Financial Analyst agent.

    Args:
        model_name: LLM model to use

    Returns:
        Configured Financial Analyst agent
    """
    return Agent(
        name="FinancialAnalyst",
        instructions=get_analyst_instructions(),
        model=model_name,
    )
```

### 3.3 Trader Agent (Orchestrator) (`agents/trader.py`)

```python
"""Trader agent - main orchestrator."""

from contextlib import AsyncExitStack
from agents import Agent, Runner
from agents.mcp import MCPServerStdio
from agents.researcher import create_researcher_agent
from agents.financial_analyst import create_analyst_agent
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv(override=True)

brave_env = {"BRAVE_API_KEY": os.getenv("BRAVE_API_KEY")}

# MCP server configurations
portfolio_mcp_params = {"command": "uv", "args": ["run", "portfolio_mcp.py"]}
search_mcp_params = {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-brave-search"],
    "env": brave_env,
}
fetch_mcp_params = {"command": "uvx", "args": ["mcp-server-fetch"]}

def get_trader_instructions() -> str:
    """Instructions for the Trader agent (orchestrator)."""
    return f"""You are the Head Trader AI agent responsible for orchestrating portfolio rebalancing.

Current Date: {datetime.now().strftime("%Y-%m-%d")}

You coordinate with two specialist agents to execute portfolio rebalancing:
1. **Researcher**: Provides market research and insights
2. **FinancialAnalyst**: Analyzes portfolio and recommends strategies

## Your Workflow:

### Phase 1: Understand Current State
1. Use get_portfolio_state() to understand:
   - Current holdings and allocations (using REAL-TIME prices from Polygon API)
   - Target allocations
   - Investor profile (risk level, constraints, time horizon)
   - Deviations from target

### Phase 2: Gather Intelligence
2. Delegate to the **Researcher** agent:
   - Ask for research on relevant asset classes in the portfolio
   - Request market conditions and trends
   - Get insights on risks and opportunities

   Example: "Research current market conditions for stocks, bonds, and crypto. Focus on any major trends or events that might affect rebalancing decisions."

### Phase 3: Get Strategy Recommendations
3. Delegate to the **FinancialAnalyst** agent:
   - Share portfolio state and research findings
   - Ask for specific rebalancing recommendations
   - Request trade-by-trade strategy with rationale

   Example: "Based on the current portfolio state and market research, recommend specific trades to rebalance the portfolio toward our target allocation."

### Phase 4: Execute Trades
4. Execute the recommended trades:
   - Use simulate_trade() for each recommended action
   - Trades execute at REAL-TIME prices from Polygon API
   - Verify each trade executes successfully
   - Track progress toward target allocation

### Phase 5: Report Results
5. Generate final report:
   - Use get_trade_history() to list all trades
   - Use calculate_performance() to show performance impact
   - Summarize the rebalancing strategy and outcomes

## Important Guidelines:
- Always delegate research to the Researcher agent (don't search yourself)
- Always delegate analysis to the FinancialAnalyst agent (don't analyze yourself)
- You focus on coordination and trade execution
- Respect investor constraints at all times
- Provide clear status updates as you progress through phases
- All prices are fetched in real-time from Polygon API

## Available Tools:
- Researcher (agent): For market research
- FinancialAnalyst (agent): For portfolio analysis and recommendations
- get_portfolio_state: Check current state with real-time prices
- get_asset_price: Get current real-time prices from Polygon API
- simulate_trade: Execute buy/sell trades at real-time prices
- get_trade_history: See executed trades
- calculate_performance: Get performance metrics

Work systematically through all phases and coordinate effectively with your specialist agents.
"""

async def run_rebalancing(model_name: str = "gpt-4o-mini"):
    """Run the three-agent portfolio rebalancing system.

    Args:
        model_name: LLM model to use for all agents

    Returns:
        Result of the rebalancing process
    """
    print("🚀 Starting 3-Agent Portfolio Rebalancing System")
    print("=" * 70)
    print("Agents:")
    print("  1. Researcher - Market research specialist")
    print("  2. Financial Analyst - Portfolio analysis expert")
    print("  3. Trader - Orchestrator and executor")
    print("\n💰 Using REAL-TIME prices from Polygon API")
    print("=" * 70)

    # Set up MCP servers
    async with AsyncExitStack() as stack:
        # Start all MCP servers
        print("\n📡 Connecting to MCP servers...")

        portfolio_mcp = await stack.enter_async_context(
            MCPServerStdio(portfolio_mcp_params, client_session_timeout_seconds=120)
        )
        search_mcp = await stack.enter_async_context(
            MCPServerStdio(search_mcp_params, client_session_timeout_seconds=120)
        )
        fetch_mcp = await stack.enter_async_context(
            MCPServerStdio(fetch_mcp_params, client_session_timeout_seconds=120)
        )

        print("  ✓ Portfolio MCP connected (with Polygon API)")
        print("  ✓ Brave Search MCP connected")
        print("  ✓ Fetch MCP connected")

        # Create specialist agents
        print("\n🤖 Creating specialist agents...")

        researcher = create_researcher_agent(model_name)
        researcher.mcp_servers = [search_mcp, fetch_mcp]
        researcher_tool = researcher.as_tool(
            tool_name="Researcher",
            tool_description="Delegate market research tasks to the Researcher agent. Ask for research on asset classes, market conditions, trends, and news."
        )
        print("  ✓ Researcher agent created")

        analyst = create_analyst_agent(model_name)
        analyst.mcp_servers = [portfolio_mcp]
        analyst_tool = analyst.as_tool(
            tool_name="FinancialAnalyst",
            tool_description="Delegate portfolio analysis and strategy recommendations to the Financial Analyst agent. Ask for rebalancing recommendations and trade strategies."
        )
        print("  ✓ Financial Analyst agent created")

        # Create main trader agent with specialist agents as tools
        trader = Agent(
            name="Trader",
            instructions=get_trader_instructions(),
            model=model_name,
            tools=[researcher_tool, analyst_tool],
            mcp_servers=[portfolio_mcp],
        )
        print("  ✓ Trader (orchestrator) agent created")

        # Run the orchestrator
        print("\n" + "=" * 70)
        print("🎯 Starting rebalancing process...")
        print("=" * 70 + "\n")

        result = await Runner.run(
            trader,
            "Please rebalance the portfolio following your defined workflow. Work through all phases systematically.",
            max_turns=30
        )

        print("\n" + "=" * 70)
        print("✅ Rebalancing process completed!")
        print("=" * 70)

        return result

if __name__ == "__main__":
    import asyncio
    asyncio.run(run_rebalancing())
```

### 3.4 Init File (`agents/__init__.py`)

```python
"""Agents package for portfolio rebalancing."""

from agents.researcher import create_researcher_agent
from agents.financial_analyst import create_analyst_agent
from agents.trader import run_rebalancing

__all__ = [
    "create_researcher_agent",
    "create_analyst_agent",
    "run_rebalancing",
]
```

### 3.5 Test Three-Agent System
```bash
# Run the agent system
uv run agents/trader.py
```

### 3.6 Checklist
- [ ] Implement researcher.py
- [ ] Implement financial_analyst.py
- [ ] Implement trader.py (orchestrator)
- [ ] Create agents/__init__.py
- [ ] Test each agent independently
- [ ] Test full 3-agent coordination
- [ ] Verify Polygon API is called for prices during rebalancing
- [ ] Verify delegation works (Trader → Researcher/Analyst)
- [ ] Verify trades are executed at real-time prices

---

## Phase 4: Simple Gradio UI (45 minutes)

### 4.1 Gradio App (`app.py`)

```python
"""Simple Gradio UI for portfolio rebalancing."""

import gradio as gr
import plotly.graph_objects as go
import pandas as pd
from mock_data import SAMPLE_PORTFOLIO, calculate_allocation, get_price, clear_price_cache
import json
import asyncio
from agents.trader import run_rebalancing
import portfolio_mcp

def get_initial_data():
    """Get initial portfolio data with real-time prices."""
    clear_price_cache()  # Get fresh prices
    assets = SAMPLE_PORTFOLIO["assets"]
    allocation, total_value = calculate_allocation(assets)

    return {
        "name": SAMPLE_PORTFOLIO["name"],
        "initial_value": SAMPLE_PORTFOLIO["initial_value"],
        "current_value": total_value,
        "allocation": allocation,
        "target": SAMPLE_PORTFOLIO["investor_profile"]["target_allocation"],
        "profile": SAMPLE_PORTFOLIO["investor_profile"]
    }

def create_allocation_pie_chart(allocation, title="Portfolio Allocation"):
    """Create a pie chart for allocation."""
    fig = go.Figure(data=[go.Pie(
        labels=list(allocation.keys()),
        values=list(allocation.values()),
        hole=.4,
        marker=dict(colors=['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A'])
    )])

    fig.update_layout(
        title=title,
        height=350,
        margin=dict(l=20, r=20, t=40, b=20),
        showlegend=True
    )

    return fig

def format_portfolio_summary(data):
    """Format portfolio summary as HTML."""
    html = f"""
    <div style='padding: 20px; background: #f0f0f0; border-radius: 10px;'>
        <h2 style='text-align: center; color: #333;'>{data['name']}</h2>
        <div style='text-align: center; font-size: 24px; margin: 20px 0;'>
            <span style='color: #666;'>Total Value:</span>
            <span style='color: #2c3e50; font-weight: bold;'>${data['current_value']:,.2f}</span>
        </div>
        <div style='text-align: center; font-size: 16px;'>
            <span style='color: #666;'>Risk Level:</span>
            <span style='color: #e74c3c; font-weight: bold;'>{data['profile']['risk_level'].upper()}</span>
            <span style='margin: 0 20px;'>|</span>
            <span style='color: #666;'>Time Horizon:</span>
            <span style='color: #3498db; font-weight: bold;'>{data['profile']['time_horizon']} years</span>
        </div>
        <div style='text-align: center; font-size: 12px; margin-top: 10px; color: #27ae60;'>
            💰 Using real-time prices from Polygon API
        </div>
    </div>
    """
    return html

def format_performance(initial_value, current_value, fees):
    """Format performance metrics as HTML."""
    change = current_value - initial_value
    change_pct = (change / initial_value) * 100
    net_change = change - fees

    color = "green" if net_change >= 0 else "red"
    emoji = "📈" if net_change >= 0 else "📉"

    html = f"""
    <div style='padding: 20px; background: #f9f9f9; border-radius: 10px; text-align: center;'>
        <h3 style='color: #333; margin-bottom: 15px;'>Performance Summary</h3>
        <div style='font-size: 18px; margin: 10px 0;'>
            <span style='color: #666;'>Initial Value:</span>
            <span style='font-weight: bold;'>${initial_value:,.2f}</span>
        </div>
        <div style='font-size: 18px; margin: 10px 0;'>
            <span style='color: #666;'>Final Value:</span>
            <span style='font-weight: bold;'>${current_value:,.2f}</span>
        </div>
        <div style='font-size: 18px; margin: 10px 0;'>
            <span style='color: #666;'>Trading Fees:</span>
            <span style='color: #e74c3c; font-weight: bold;'>${fees:,.2f}</span>
        </div>
        <div style='font-size: 24px; margin: 20px 0; color: {color};'>
            {emoji} <span style='font-weight: bold;'>${abs(net_change):,.2f}</span>
            (<span style='font-weight: bold;'>{change_pct:+.2f}%</span>)
        </div>
    </div>
    """
    return html

def run_rebalancing_sync():
    """Synchronous wrapper for async rebalancing."""
    # Reset portfolio to initial state
    portfolio_mcp.reset_portfolio()

    # Run 3-agent system
    print("\n" + "="*70)
    print("STARTING 3-AGENT REBALANCING SYSTEM")
    print("="*70)
    asyncio.run(run_rebalancing())

    # Get results
    trades = portfolio_mcp.TRADES

    # Calculate final allocation with real-time prices
    clear_price_cache()
    holdings = portfolio_mcp.CURRENT_HOLDINGS
    assets = [
        {
            "symbol": symbol,
            "type": data["type"],
            "quantity": data["quantity"]
        }
        for symbol, data in holdings.items()
    ]

    final_allocation, final_value = calculate_allocation(assets)

    # Create outputs
    initial_data = get_initial_data()

    initial_chart = create_allocation_pie_chart(
        initial_data["allocation"],
        "Initial Allocation"
    )

    final_chart = create_allocation_pie_chart(
        final_allocation,
        "Rebalanced Allocation"
    )

    target_chart = create_allocation_pie_chart(
        initial_data["target"],
        "Target Allocation"
    )

    # Create trades dataframe
    if trades:
        trades_df = pd.DataFrame(trades)
        trades_df = trades_df.sort_values('timestamp', ascending=False)
        trades_df = trades_df[['timestamp', 'action', 'symbol', 'quantity', 'price', 'fees', 'rationale']]
    else:
        trades_df = pd.DataFrame(columns=['timestamp', 'action', 'symbol', 'quantity', 'price', 'fees', 'rationale'])

    # Calculate performance
    total_fees = sum(t.get("fees", 0) for t in trades)
    performance_html = format_performance(
        initial_data["initial_value"],
        final_value,
        total_fees
    )

    return (
        initial_chart,
        target_chart,
        final_chart,
        performance_html,
        trades_df,
        f"✅ Rebalancing completed! {len(trades)} trades executed by 3-agent system using real-time Polygon prices."
    )

def create_ui():
    """Create the Gradio interface."""

    initial_data = get_initial_data()

    with gr.Blocks(
        title="3-Agent Portfolio Rebalancer",
        theme=gr.themes.Soft(primary_hue="blue")
    ) as app:

        gr.Markdown("# 💼 AI Portfolio Rebalancer (3-Agent System)")
        gr.Markdown("**Researcher** → **Financial Analyst** → **Trader** working together with **real-time Polygon API prices**")

        # Portfolio info
        summary_html = gr.HTML(format_portfolio_summary(initial_data))

        # Action button
        with gr.Row():
            run_btn = gr.Button(
                "🚀 Run 3-Agent Rebalancing",
                variant="primary",
                size="lg",
                scale=1
            )
            status_text = gr.Textbox(
                label="Status",
                value="Ready to rebalance",
                interactive=False,
                scale=2
            )

        gr.Markdown("---")
        gr.Markdown("## 📊 Portfolio Comparison")

        # Charts row
        with gr.Row():
            with gr.Column():
                initial_chart = gr.Plot(
                    create_allocation_pie_chart(initial_data["allocation"], "Initial Allocation"),
                    label="Initial Portfolio"
                )
            with gr.Column():
                target_chart = gr.Plot(
                    create_allocation_pie_chart(initial_data["target"], "Target Allocation"),
                    label="Target Portfolio"
                )
            with gr.Column():
                final_chart = gr.Plot(
                    create_allocation_pie_chart(initial_data["allocation"], "Rebalanced Allocation"),
                    label="Rebalanced Portfolio"
                )

        gr.Markdown("---")
        gr.Markdown("## 📈 Performance Metrics")

        performance_html = gr.HTML(format_performance(
            initial_data["initial_value"],
            initial_data["current_value"],
            0
        ))

        gr.Markdown("---")
        gr.Markdown("## 💰 Trade History")

        trades_table = gr.Dataframe(
            value=pd.DataFrame(columns=['timestamp', 'action', 'symbol', 'quantity', 'price', 'fees', 'rationale']),
            label="Simulated Trades (Executed by Trader Agent at Real-Time Prices)",
            wrap=True,
            interactive=False
        )

        gr.Markdown("---")
        gr.Markdown("""
        ### 🤖 How the 3-Agent System Works:
        1. **Trader Agent** (Orchestrator) coordinates the entire process
        2. **Researcher Agent** investigates market conditions for each asset class
        3. **Financial Analyst Agent** analyzes portfolio using real-time prices and recommends specific trades
        4. **Trader Agent** executes the recommended trades at real-time Polygon prices and reports results

        ### 💰 Real-Time Pricing:
        - All prices fetched from **Polygon API**
        - Stocks: VTI (Total Stock Market ETF)
        - Bonds: AGG (Aggregate Bond ETF)
        - Crypto: BTC-USD (Bitcoin)
        - Real Estate: VNQ (Real Estate REIT ETF)
        """)

        # Event handler
        run_btn.click(
            fn=run_rebalancing_sync,
            inputs=[],
            outputs=[
                initial_chart,
                target_chart,
                final_chart,
                performance_html,
                trades_table,
                status_text
            ]
        )

    return app

if __name__ == "__main__":
    app = create_ui()
    app.launch(inbrowser=True, share=False)
```

### 4.2 Checklist
- [ ] Implement app.py with Gradio UI
- [ ] Test UI launches correctly
- [ ] Verify real-time prices display in UI
- [ ] Test rebalancing button triggers 3-agent system
- [ ] Verify charts display correctly with real prices
- [ ] Verify trades table shows real execution prices
- [ ] Check console logs show Polygon API calls

---

## Phase 5: Integration & Testing (45 minutes)

### 5.1 End-to-End Manual Testing

Test checklist:
1. **Initial State with Real Prices**
   - [ ] Load Gradio UI
   - [ ] Verify initial portfolio displays with real-time prices
   - [ ] Check that prices are fetched from Polygon API (check console)
   - [ ] Verify portfolio value reflects current market prices
   - [ ] Check target allocation chart shows correct percentages

2. **Run 3-Agent Rebalancing**
   - [ ] Click "Run 3-Agent Rebalancing" button
   - [ ] Monitor console for:
     - [ ] Polygon API price fetches
     - [ ] Trader agent starts orchestration
     - [ ] Researcher agent is called for market research
     - [ ] Financial Analyst agent analyzes with real prices
     - [ ] Trader agent executes trades at real prices
   - [ ] Verify all three agents communicate properly
   - [ ] Verify trades are executed at current market prices

3. **Results Verification**
   - [ ] Check rebalanced portfolio chart updates with real prices
   - [ ] Verify trades table shows actual execution prices from Polygon
   - [ ] Check performance metrics reflect real price changes
   - [ ] Verify final allocation is closer to target
   - [ ] Confirm agent coordination worked as expected

4. **Polygon API Edge Cases**
   - [ ] Test with Polygon API rate limits (if hit)
   - [ ] Verify fallback prices work if API fails
   - [ ] Test price caching reduces redundant API calls
   - [ ] Verify error messages are clear for API issues

### 5.2 Updated README (`README.md`)

```markdown
# AI Portfolio Rebalancer - 3-Agent MVP

Multi-agent AI system for portfolio rebalancing using specialized agents for research, analysis, and trade execution with **real-time Polygon API pricing**.

## Features
- 🤖 **Three specialized AI agents**:
  - **Researcher**: Market research and trend analysis
  - **Financial Analyst**: Portfolio analysis and strategy recommendations
  - **Trader**: Orchestration and trade execution
- 💰 **Real-time pricing** via Polygon API
- 📊 Visual portfolio comparison (before/after/target)
- 💵 Trade simulation with realistic fees (0.2%)
- 📈 Performance metrics and reporting
- 🔍 Market research via web search

## Architecture

```
┌─────────────────────────────────────────────┐
│           Trader Agent (Orchestrator)        │
│  - Coordinates workflow                      │
│  - Executes trades at real-time prices      │
│  - Reports results                           │
│                                              │
│  ┌────────────────────────────────────────┐ │
│  │   Researcher Agent (Tool)              │ │
│  │   - Web search (Brave)                 │ │
│  │   - Content fetching                   │ │
│  │   - Market intelligence                │ │
│  └────────────────────────────────────────┘ │
│                                              │
│  ┌────────────────────────────────────────┐ │
│  │   Financial Analyst Agent (Tool)       │ │
│  │   - Portfolio analysis (real prices)   │ │
│  │   - Deviation calculation              │ │
│  │   - Strategy recommendations           │ │
│  └────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
                    ↓
         💰 Polygon API (Real-Time Prices)
```

## Quick Start

### Prerequisites
- Python 3.10+
- uv package manager
- Node.js (for Brave search MCP)
- Polygon.io API key (free tier works!)

### Setup

1. Install dependencies:
```bash
cd trader_app
uv venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
uv pip install agents fastmcp gradio pandas plotly python-dotenv polygon-api-client
```

2. Configure API keys:
```bash
cp .env.example .env
# Edit .env with your keys:
# - OPENAI_API_KEY (required)
# - BRAVE_API_KEY (required for research)
# - POLYGON_API_KEY (required for real-time prices)
```

**Get Polygon API Key:**
- Sign up at https://polygon.io
- Free tier includes 5 API calls/minute
- Copy your API key to .env

3. Test Polygon connection:
```bash
uv run test_polygon.py
```

4. Launch the app:
```bash
uv run app.py
```

5. Open browser to http://localhost:7860

## Usage

1. Review the initial portfolio state (with real-time prices)
2. Click "Run 3-Agent Rebalancing" button
3. Watch the console to see agent coordination:
   - Trader orchestrates the process
   - Researcher gathers market intelligence
   - Analyst recommends trades using real-time prices
   - Trader executes trades at current market prices
4. Review results:
   - Rebalanced portfolio allocation
   - List of executed trades with actual prices
   - Performance metrics based on real market data

## Sample Portfolio

Initial Portfolio Composition ($100,000):
- VTI (Total Stock Market ETF): 200 shares
- AGG (Aggregate Bond ETF): 300 shares
- BTC-USD (Bitcoin): 0.3 BTC
- VNQ (Real Estate REIT ETF): 100 shares

**Prices are fetched in real-time from Polygon API**

Target Allocation:
- Stocks: 50%
- Bonds: 30%
- Crypto: 10%
- Real Estate: 10%

The three agents work together to research market conditions, analyze the portfolio using real-time prices, and execute trades at current market rates.

## How the Agents Work Together

1. **Phase 1 - Understanding**: Trader gets current portfolio state with real-time prices
2. **Phase 2 - Research**: Trader delegates to Researcher for market intelligence
3. **Phase 3 - Analysis**: Trader delegates to Analyst for rebalancing strategy (using real prices)
4. **Phase 4 - Execution**: Trader executes recommended trades at real-time Polygon prices
5. **Phase 5 - Reporting**: Trader generates performance report based on actual market data

## Real-Time Pricing Details

- **Data Source**: Polygon.io REST API
- **Update Frequency**: Real-time (on-demand)
- **Asset Coverage**:
  - Stocks/ETFs: Last trade price
  - Crypto: Last trade price (X:BTCUSD format)
- **Caching**: LRU cache to minimize API calls
- **Fallback**: Estimated prices if API fails
- **Rate Limits**: Free tier = 5 calls/min (sufficient for MVP)

## MVP Limitations

This is an MVP with the following limitations:
- Single hardcoded portfolio (not persistent)
- No database (state resets on reload)
- Manual refresh (no auto-updates)
- Simple error handling
- Free tier Polygon API (rate limited)

## Future Enhancements
- Database persistence for multiple portfolios
- Historical price tracking and backtesting
- Real-time UI updates with streaming prices
- Chat interface with agents
- Advanced charting with price history
- Tax-loss harvesting optimization
- Support for more asset types
```

### 5.3 Final Integration Checklist
- [ ] Run full end-to-end test with real Polygon API
- [ ] Verify all three agents work together
- [ ] Verify Polygon prices are fetched correctly
- [ ] Verify agent delegation (Trader → Researcher/Analyst)
- [ ] Test error handling for API failures
- [ ] Create comprehensive README with Polygon setup
- [ ] Clean up console output
- [ ] Add helpful logging for price fetches
- [ ] Test on fresh Python environment
- [ ] Verify API rate limits are respected

---

## Time Estimate Summary

| Phase | Task | Time |
|-------|------|------|
| 1 | Minimal Setup + Polygon Integration | 35 min (+5 min) |
| 2 | Single MCP Server with Real Prices | 45 min |
| 3 | Three-Agent System | 75 min |
| 4 | Simple Gradio UI | 45 min |
| 5 | Integration & Testing | 45 min |
| **Total** | **Core MVP** | **~4.25 hours** |
| | **Buffer for debugging** | **1.75 hours** |
| | **Total with buffer** | **6 hours** |

---

## Polygon API Integration Notes

### API Call Optimization
- **Caching**: `@lru_cache` on `get_price()` reduces redundant calls
- **Batch Operations**: Clear cache before major operations (portfolio state, trades)
- **Rate Limits**: Free tier = 5 calls/min (sufficient for 4 assets + occasional checks)

### Error Handling
```python
try:
    price = polygon_client.get_last_trade(ticker).price
except Exception as e:
    # Falls back to estimated prices
    price = get_fallback_price(symbol)
```

### Asset Symbol Mapping
- Stocks/ETFs: Direct symbol (e.g., "VTI")
- Crypto: Polygon format "X:BTCUSD" for "BTC-USD"
- Bonds: ETF symbols (e.g., "AGG")
- Real Estate: REIT ETF symbols (e.g., "VNQ")

---

## Success Criteria for MVP

After 6 hours, you should have:

1. ✅ **Three working AI agents** (Researcher, Analyst, Trader)
2. ✅ **Agent coordination** via agent-as-tool pattern
3. ✅ **Real-time Polygon API integration** for all asset prices
4. ✅ **Web research integration** via Brave search
5. ✅ **Portfolio analysis** with real-time price data
6. ✅ **Trade simulation** at actual market prices
7. ✅ **Visual Gradio app** showing before/after comparison
8. ✅ **Performance metrics** based on real market data
9. ✅ **Trade history** with actual execution prices
10. ✅ **Working coordination** between all agents
11. ✅ **Basic README** with Polygon setup instructions

---

## Risk Mitigation

**Highest Risk Areas:**
1. Polygon API rate limits → Use caching, batch operations
2. API authentication issues → Test connection early with test_polygon.py
3. Crypto symbol formatting → Use X:BTCUSD format for Polygon
4. Agent coordination complexity → Test agent delegation early
5. MCP server connection issues → Test each server independently first

**Fallback Plan:**
If Polygon API issues:
- Use fallback prices (hardcoded estimates)
- Reduce API calls (more aggressive caching)
- Focus on getting one successful rebalancing working
- Add Polygon integration as final polish

---

End of Simplified 3-Agent MVP Plan with Real Polygon Pricing
