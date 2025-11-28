# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Portfolio rebalancing MVP using a 3-agent system (Researcher, Financial Analyst, Trader) that analyzes investment portfolios, researches market conditions, and simulates rebalancing trades with Polygon API pricing and a Gradio web interface.

## Project Structure

```
trader_app/
├── app.py                      # Gradio UI entry point
├── portfolio.json              # Portfolio definition (user-editable)
├── rebalancer/                 # Agent definitions (named to avoid conflict with 'agents' package)
│   ├── trader.py               # Orchestrator agent
│   ├── researcher.py           # Market research agent
│   └── analyst.py              # Financial analysis agent
├── portfolio_server/           # MCP server + data layer
│   ├── server.py               # MCP server with portfolio tools
│   └── portfolio.py            # Portfolio data loading/pricing
├── tests/                      # Test scripts
│   ├── test_polygon.py         # Polygon API test
│   └── test_mcp.py             # MCP tools test
└── docs/                       # Planning docs
```

## Commands

```bash
# Setup
uv venv && source .venv/bin/activate
uv pip install polygon-api-client python-dotenv fastmcp openai-agents gradio pandas plotly

# Test Polygon API
python tests/test_polygon.py

# Test MCP tools
python tests/test_mcp.py

# Run 3-agent system (CLI)
python -m rebalancer.trader

# Launch Gradio UI
python app.py
```

## Architecture

### Three-Agent Hierarchy with Focused Tools

```
Trader Agent (Orchestrator) - gpt-4o-mini
├── MCP: portfolio_server (all tools including simulate_trade)
├── Researcher Agent (as tool, max_turns=10) - gpt-4o
│   ├── Tools: brave_web_search, fetch
│   └── MCP: Brave Search, Fetch
└── Financial Analyst Agent (4 focused tools, max_turns=5 each) - o4-mini
    ├── AnalyzeInvestorProfile - risk level, time horizon, constraints
    ├── AnalyzePortfolio - current allocation, identify imbalances
    ├── RecommendTargetAllocation - target percentages by asset class
    ├── RecommendTrades - specific buy/sell with quantities
    └── MCP: portfolio_server (read-only: no simulate_trade)
```

Models are configurable via `run_rebalancing(agent_models={"trader": "...", "researcher": "...", "analyst": "..."})`.

### MCP Server (`portfolio_server/server.py`)

Tools with cross-process state sharing via `.portfolio_state.json`:
- `get_portfolio_state`: Holdings, allocations, investor profile (real-time prices)
- `get_asset_price`: Current price from Polygon API
- `list_tradeable_assets`: Assets with Polygon tickers (can be traded)
- `simulate_trade`: Buy/sell with 0.2% fee, updates holdings
- `get_trade_history`: All executed trades
- `calculate_performance`: Initial vs current value, fees, net change
- `generate_portfolio_analysis`: Returns exact computed values (ensures consistency)
- `save_analysis`: Store qualitative commentary for UI (numbers auto-computed via session snapshot)

**Session-level snapshot**: `_ANALYSIS_SNAPSHOT` ensures all analysis sections use the same computed values within a single rebalancing run.

### Data Flow

1. Portfolio defined in `portfolio.json` (EUR-based with investor profile)
2. Prices fetched from Polygon API with USD→EUR conversion
3. MCP server runs as subprocess, shares state via JSON file
4. Gradio UI calls `portfolio_server.server.load_state()` after rebalancing to read results

### Portfolio Configuration (`portfolio.json`)

```json
{
  "name": "...",
  "trading_fee": 0.002,
  "investor_profile": { "risk_level", "time_horizon", "constraints", "philosophy" },
  "assets": [
    { "id", "name", "type", "quantity", "unit_purchase_price", "currency", "polygon": { "ticker" } }
  ]
}
```

Asset types: `stock`, `bond`, `crypto`, `cash`. Only assets with `polygon.ticker` are tradeable.

## Key Patterns

**Agent Creation**: Pass MCP servers explicitly at creation time:
```python
from rebalancer.researcher import create_researcher_agent
researcher = create_researcher_agent(
    model_name=model_name,
    mcp_servers=[search_mcp, fetch_mcp]
)
```

**Multi-Tool from Single Agent**: Financial Analyst exposes 4 focused tools via multiple `as_tool()` calls:
```python
from rebalancer.analyst import create_analyst_agent
analyst = create_analyst_agent(model_name, mcp_servers=[portfolio_mcp])
analyze_profile_tool = analyst.as_tool(tool_name="AnalyzeInvestorProfile", max_turns=5)
analyze_portfolio_tool = analyst.as_tool(tool_name="AnalyzePortfolio", max_turns=5)
```

**Cross-Process State**: MCP subprocess writes to `.portfolio_state.json`, main app loads it:
```python
# In portfolio_server/server.py after trades
save_state()

# In app.py after rebalancing
from portfolio_server import server as portfolio_mcp
portfolio_mcp.load_state()
```

**Polygon API**: Uses ticker symbols. Crypto format is `X:BTCEUR` for BTC-EUR. USD prices converted to EUR automatically.

## Environment Variables

Required in `.env`:
```
OPENAI_API_KEY=...          # For agents (OpenAI)
BRAVE_SEARCH_API_KEY=...    # For Researcher web search
POLYGON_API_KEY=...         # For real-time prices
```

## Agent Workflow (5 Phases)

1. **Understand State**: `get_portfolio_state()`, `list_tradeable_assets()`
2. **Research**: Delegate to Researcher for market intelligence
3. **Analyze**: Use Analyst tools in sequence: AnalyzeInvestorProfile → AnalyzePortfolio → RecommendTargetAllocation → RecommendTrades
4. **Execute**: Run `simulate_trade()` for each recommendation
5. **Report**: `get_trade_history()`, `calculate_performance()`

## Important: Folder Naming

- `rebalancer/` (not `agents/`) - avoids conflict with `openai-agents` package
- `portfolio_server/` (not `mcp/`) - avoids conflict with `mcp` package
- MCP server runs as module: `python -m portfolio_server.server`
