"""Agents package for portfolio rebalancing.

Three-agent system with explicit tool assignments:

1. Researcher Agent
   - Tools: brave_web_search, fetch (from MCP servers)
   - Purpose: Market research and trend analysis

2. Financial Analyst Agent
   - Tools: get_portfolio_state, get_asset_price, calculate_performance (read-only)
   - Purpose: Portfolio analysis and trade recommendations
   - Note: Does NOT have simulate_trade

3. Trader Agent (Orchestrator)
   - Tools: Researcher (agent), FinancialAnalyst (agent),
            get_portfolio_state, get_asset_price, simulate_trade,
            get_trade_history, calculate_performance
   - Purpose: Coordination and trade execution
"""

from rebalancer.researcher import create_researcher_agent
from rebalancer.analyst import create_analyst_agent
from rebalancer.trader import run_rebalancing

__all__ = [
    "create_researcher_agent",
    "create_analyst_agent",
    "run_rebalancing",
]
