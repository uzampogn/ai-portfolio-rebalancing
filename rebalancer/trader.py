"""Trader agent - main orchestrator."""

from contextlib import AsyncExitStack
from agents import Agent, Runner
from agents.mcp import MCPServerStdio
from rebalancer.researcher import create_researcher_agent
from rebalancer.analyst import create_analyst_agent
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv(override=True)

# Path to state file (for reset)
STATE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".portfolio_state.json")

brave_env = {"BRAVE_API_KEY": os.getenv("BRAVE_SEARCH_API_KEY")}

# MCP server configurations - run from project root
portfolio_mcp_params = {"command": "python", "args": ["-m", "portfolio_server.server"]}
search_mcp_params = {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-brave-search"],
    "env": brave_env,
}
fetch_mcp_params = {"command": "uvx", "args": ["mcp-server-fetch"]}

# =============================================================================
# MODEL CONFIGURATION
# =============================================================================

DEFAULT_AGENT_MODELS = {
      "trader": "gpt-4o-mini",      # Fast orchestration
      "researcher": "gpt-4o",        # Good general reasoning  
      "analyst": "o4-mini",          # Strong math/reasoning
  }

def get_trader_instructions() -> str:
    """Instructions for the Trader agent (orchestrator)."""
    return f"""You are the Head Trader AI agent responsible for orchestrating portfolio rebalancing.

Current Date: {datetime.now().strftime("%Y-%m-%d")}

You coordinate specialist agents using focused tools to execute portfolio rebalancing systematically.

## Your Workflow (Follow in Order):

### Phase 1: Understand Current State
1. Use `get_portfolio_state()` to get current holdings and investor profile
2. Use `list_tradeable_assets()` to see which assets can be traded

### Phase 2: Gather Market Intelligence
3. Use `Researcher` tool to get market conditions:
   - "Research current market conditions for stocks, bonds, and crypto affecting portfolio rebalancing."

### Phase 3: Analyze with Financial Analyst (Use These Tools in Order)

4. **AnalyzeInvestorProfile**: First, understand the investor
   - "Analyze the investor profile and summarize their investment requirements."

5. **AnalyzePortfolio**: Then, analyze current state
   - "Analyze the current portfolio allocation and identify imbalances."
   - **IMPORTANT**: After receiving the analysis, save the QUALITATIVE commentary only:
     `save_analysis(analysis_type="portfolio_analysis", commentary="<qualitative issues and observations>")`
     Note: The exact numbers are auto-computed by the system - just save the commentary.

6. **RecommendTargetAllocation**: Get target recommendation
   - "Based on the investor profile and current analysis, recommend a target allocation."
   - **IMPORTANT**: After receiving the recommendation, save the RATIONALE only:
     `save_analysis(analysis_type="target_allocation", commentary="<the rationale and reasoning>")`
     Note: The exact numbers are auto-computed by the system - just save the rationale.

7. **RecommendTrades**: Get specific trades
   - "Recommend specific trades to move from current allocation to target allocation."

### Phase 4: Execute Trades
8. Execute each recommended trade using `simulate_trade(action, asset_id, quantity, rationale)`
   - Only tradeable assets can be bought/sold
   - Verify each trade succeeds before proceeding

### Phase 5: Report Results
9. Use `get_trade_history()` and `calculate_performance()` to generate final report

## Available Tools:

**Research:**
- `Researcher`: Market research on asset classes, conditions, trends

**Financial Analysis (use in sequence):**
- `AnalyzeInvestorProfile`: Analyze risk level, time horizon, philosophy, constraints
- `AnalyzePortfolio`: Analyze current allocation, identify over/underweight positions
- `RecommendTargetAllocation`: Propose target allocation percentages
- `RecommendTrades`: Specific trade recommendations (asset_id, action, quantity)

**Portfolio Operations:**
- `get_portfolio_state`: Current holdings, allocation, investor profile
- `get_asset_price`: Get price for specific asset
- `list_tradeable_assets`: Assets that can be traded (have Polygon ticker)
- `generate_portfolio_analysis`: Get exact computed values (total value, allocation %, performance)
- `simulate_trade`: Execute buy/sell trade
- `get_trade_history`: List executed trades
- `calculate_performance`: Performance metrics
- `save_analysis`: Save qualitative commentary for UI (numbers are auto-computed)

## Important Guidelines:
- Follow the workflow phases in order
- Use Financial Analyst tools sequentially for best results
- Only trade assets marked as tradeable
- Verify each trade executes successfully

Work systematically through all phases.
"""

async def run_rebalancing(agent_models: dict | None = None):
    """Run the three-agent portfolio rebalancing system.

    Args:
        agent_models: Dict specifying model for each agent. Keys: "trader", "researcher", "analyst"
                     If None, uses DEFAULT_AGENT_MODELS.
                     Example: {"trader": "gpt-4o-mini", "researcher": "claude-sonnet-4-5-20250514", "analyst": "gemini-2.0-flash"}

    Returns:
        Result of the rebalancing process
    """
    # Merge with defaults
    models = {**DEFAULT_AGENT_MODELS, **(agent_models or {})}

    # Reset state file to ensure fresh start with original portfolio
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)
        print("Cleared stale state file")

    print("Starting 3-Agent Portfolio Rebalancing System")
    print("=" * 70)
    print("Agents and Models:")
    print(f"  1. Researcher - {models['researcher']}")
    print(f"  2. Financial Analyst - {models['analyst']}")
    print(f"  3. Trader - {models['trader']}")
    print("\nUsing REAL-TIME prices from Polygon API")
    print("=" * 70)

    # Set up MCP servers
    async with AsyncExitStack() as stack:
        # Start all MCP servers
        print("\nConnecting to MCP servers...")

        portfolio_mcp = await stack.enter_async_context(
            MCPServerStdio(portfolio_mcp_params, client_session_timeout_seconds=120)
        )
        search_mcp = await stack.enter_async_context(
            MCPServerStdio(search_mcp_params, client_session_timeout_seconds=120)
        )
        fetch_mcp = await stack.enter_async_context(
            MCPServerStdio(fetch_mcp_params, client_session_timeout_seconds=120)
        )

        print("  Portfolio MCP connected (with Polygon API)")
        print("  Brave Search MCP connected")
        print("  Fetch MCP connected")

        # Create specialist agents with explicit MCP server assignments
        print("\nCreating specialist agents...")

        # Researcher: has web search and fetch tools
        researcher = create_researcher_agent(
            model_name=models["researcher"],
            mcp_servers=[search_mcp, fetch_mcp]  # brave_web_search, fetch
        )
        researcher_tool = researcher.as_tool(
            tool_name="Researcher",
            tool_description="Delegate market research tasks to the Researcher agent. Ask for research on asset classes, market conditions, trends, and news.",
            max_turns=10  # Prevent infinite loops in sub-agent
        )
        print(f"  Researcher agent created ({models['researcher']})")

        # Financial Analyst: has read-only portfolio tools (no simulate_trade)
        # Create multiple focused tools from the same analyst agent
        analyst = create_analyst_agent(
            model_name=models["analyst"],
            mcp_servers=[portfolio_mcp]
        )

        # Tool 1: Analyze Investor Profile
        analyze_profile_tool = analyst.as_tool(
            tool_name="AnalyzeInvestorProfile",
            tool_description="Analyze the investor profile (risk level, time horizon, philosophy, constraints) and summarize their investment requirements and risk tolerance.",
            max_turns=5
        )

        # Tool 2: Analyze Portfolio Allocation
        analyze_portfolio_tool = analyst.as_tool(
            tool_name="AnalyzePortfolio",
            tool_description="Analyze current portfolio allocation by asset class, identify over/underweight positions, and assess overall portfolio health.",
            max_turns=5
        )

        # Tool 3: Recommend Target Allocation
        recommend_target_tool = analyst.as_tool(
            tool_name="RecommendTargetAllocation",
            tool_description="Based on investor profile analysis, recommend a target allocation with specific percentages for each asset class (stock, bond, crypto, real_estate).",
            max_turns=5
        )

        # Tool 4: Recommend Specific Trades
        recommend_trades_tool = analyst.as_tool(
            tool_name="RecommendTrades",
            tool_description="Given current allocation and target allocation, recommend specific trades (asset_id, action buy/sell, quantity) to rebalance the portfolio. Only recommend trades for tradeable assets.",
            max_turns=5
        )

        print(f"  Financial Analyst created ({models['analyst']}) with 4 focused tools:")
        print("    - AnalyzeInvestorProfile")
        print("    - AnalyzePortfolio")
        print("    - RecommendTargetAllocation")
        print("    - RecommendTrades")

        # Trader (orchestrator): has sub-agents + all portfolio tools including simulate_trade
        trader = Agent(
            name="Trader",
            instructions=get_trader_instructions(),
            model=models["trader"],
            tools=[
                researcher_tool,
                analyze_profile_tool,
                analyze_portfolio_tool,
                recommend_target_tool,
                recommend_trades_tool
            ],
            mcp_servers=[portfolio_mcp],
        )
        print(f"  Trader agent created ({models['trader']}) with all tools")

        # Run the orchestrator
        print("\n" + "=" * 70)
        print("Starting rebalancing process...")
        print("=" * 70 + "\n")

        result = await Runner.run(
            trader,
            "Please rebalance the portfolio following your defined workflow. Work through all phases systematically.",
            max_turns=30
        )

        print("\n" + "=" * 70)
        print("Rebalancing process completed!")
        print("=" * 70)

        return result

if __name__ == "__main__":
    import asyncio
    asyncio.run(run_rebalancing())
