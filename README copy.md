# MVP - Portfolio Rebalancing Tool

A multi-agent AI system where three specialized agents (Researcher, Financial Analyst, and Trader) collaborate to analyze portfolios, research market conditions, and execute rebalancing trades using real-time Polygon API pricing through a Gradio web interface.

## Features

- **Three specialized AI agents** with explicit tool assignments
- **Real-time pricing** via Polygon API (with fallback prices)
- Visual portfolio comparison (before/after)
- Trade simulation with realistic fees (0.2%)
- Trade history with totals (bought/sold/fees)
- Gradio web interface

## Architecture

```
Trader Agent (Orchestrator) - gpt-4o-mini
├── MCP: portfolio_server (all tools including simulate_trade)
├── Researcher Agent (as tool, max_turns=10) - gpt-4o
│   └── MCP: Brave Search, Fetch
└── Financial Analyst Agent (4 focused tools) - o4-mini
    ├── AnalyzeInvestorProfile
    ├── AnalyzePortfolio
    ├── RecommendTargetAllocation
    ├── RecommendTrades
    └── MCP: portfolio_server (read-only: no simulate_trade)
```

## Quick Start

### Prerequisites

- Python 3.10+
- uv package manager
- Node.js (for Brave Search MCP)
- API keys: OpenAI, Brave Search, Polygon.io

### Setup

```bash
cd trader_app
uv venv
source .venv/bin/activate  # macOS/Linux
uv pip install polygon-api-client python-dotenv fastmcp openai-agents gradio pandas plotly
```

Configure API keys in `.env`:
```
OPENAI_API_KEY=your_openai_key
BRAVE_SEARCH_API_KEY=your_brave_key
POLYGON_API_KEY=your_polygon_key
```

### Run

```bash
# Test Polygon API
python tests/test_polygon.py

# Test MCP tools
python tests/test_mcp.py

# Run 3-agent system (CLI)
python -m rebalancer.trader

# Launch Gradio UI
python app.py
```

Open browser to http://localhost:7860

## Sample Portfolio

| Asset | Type | Ticker | Quantity |
|-------|------|--------|----------|
| Amazon | stock | AMZN | 700 |
| NVIDIA | stock | NVDA | 45 |
| Microsoft | stock | MSFT | 40 |
| Vanguard S&P 500 ETF | stock | VOO | 130 |
| Bitcoin | crypto | X:BTCEUR | 0.05 |
| US Government Bonds | bond | - | 100 |
| Savings Account | cash | - | 1 |

**Investor Profile:** Moderate risk, 20-year horizon

## Project Structure

```
trader_app/
├── app.py                      # Gradio web interface
├── portfolio.json              # Portfolio definition (editable)
├── rebalancer/                 # Agent definitions
│   ├── trader.py               # Orchestrator + run_rebalancing()
│   ├── researcher.py           # Market research agent
│   └── analyst.py              # Portfolio analysis agent
├── portfolio_server/           # MCP server + data layer
│   ├── server.py               # MCP server with portfolio tools
│   └── portfolio.py            # Portfolio data + Polygon integration
├── tests/                      # Test scripts
└── docs/                       # Planning documentation
```

## How the Agents Work

1. **Phase 1 - Understanding**: Trader gets current portfolio state with real-time prices
2. **Phase 2 - Research**: Trader delegates to Researcher for market intelligence
3. **Phase 3 - Analysis**: Trader uses Analyst tools in sequence (Profile → Portfolio → Target → Trades)
4. **Phase 4 - Execution**: Trader executes recommended trades at current prices
5. **Phase 5 - Reporting**: Trader generates trade history and performance report

## MCP Tools

| Tool | Description | Available To |
|------|-------------|--------------|
| `get_portfolio_state` | Current holdings, allocations, investor profile | Trader, Analyst |
| `get_asset_price` | Real-time price from Polygon API | Trader, Analyst |
| `list_tradeable_assets` | Assets with Polygon tickers | Trader, Analyst |
| `simulate_trade` | Execute buy/sell with 0.2% fees | **Trader only** |
| `get_trade_history` | List of all executed trades | Trader |
| `calculate_performance` | Initial vs current value metrics | Trader, Analyst |
| `generate_portfolio_analysis` | Computed values for consistency | Trader, Analyst |
| `save_analysis` | Store analysis commentary for UI | Trader |

## Polygon API Notes

- **Ticker symbols**: Uses symbols like AMZN, NVDA (not ISINs)
- **Crypto format**: Uses `X:BTCEUR` for BTC-EUR
- **Free tier**: Limited access, uses fallback prices
- **Caching**: LRU cache minimizes API calls

## MVP Limitations

- Single portfolio defined in `portfolio.json` (resets on reload)
- In-memory state with file-based cross-process sharing
- Free Polygon tier uses fallback prices
- Manual refresh (no real-time updates)
