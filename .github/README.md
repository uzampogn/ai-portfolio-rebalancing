# AI Portfolio Rebalancing

A multi-agent AI system that analyzes investment portfolios, researches market conditions, and executes simulated rebalancing trades.

[![Hugging Face Spaces](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Spaces-blue)](https://huggingface.co/spaces/UZ31/ai_portfolio_rebalancing)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

## Features

- **3-Agent Architecture**: Researcher, Financial Analyst, and Trader agents working together
- **Real-Time Pricing**: Polygon API integration for stocks, ETFs, and crypto
- **Smart Caching**: TTL-based price caching with disk persistence to avoid rate limits
- **Investor Profile Aware**: Considers risk level, time horizon, and constraints
- **Interactive UI**: Gradio web interface with before/after portfolio comparison

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Trader Agent (Orchestrator)              │
│                         gpt-4o-mini                         │
├─────────────────────────────────────────────────────────────┤
│  MCP Server: portfolio_server                               │
│  - get_portfolio_state    - simulate_trade                  │
│  - get_asset_price        - get_trade_history               │
│  - list_tradeable_assets  - calculate_performance           │
└──────────────┬────────────────────────┬─────────────────────┘
               │                        │
               ▼                        ▼
┌──────────────────────────┐  ┌──────────────────────────────┐
│    Researcher Agent      │  │   Financial Analyst Agent    │
│        gpt-4o            │  │          o4-mini             │
├──────────────────────────┤  ├──────────────────────────────┤
│ - Brave Web Search       │  │ - AnalyzeInvestorProfile     │
│ - Web Fetch              │  │ - AnalyzePortfolio           │
│                          │  │ - RecommendTargetAllocation  │
│ Researches market        │  │ - RecommendTrades            │
│ conditions & news        │  │                              │
└──────────────────────────┘  └──────────────────────────────┘
```

## How It Works

1. **Understand State**: Trader loads portfolio holdings and current prices
2. **Research**: Researcher agent investigates market conditions for each asset class
3. **Analyze**: Financial Analyst evaluates portfolio, recommends target allocation and specific trades
4. **Execute**: Trader executes simulated trades with 0.2% fee
5. **Report**: Display before/after comparison with trade history

## Quick Start

### Prerequisites

- Python 3.10+
- OpenAI API key
- Polygon API key (free tier works)
- Brave Search API key

### Installation

```bash
# Clone the repository
git clone https://github.com/uzampogn/ai-portfolio-rebalancing.git
cd ai-portfolio-rebalancing

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Environment Setup

Create a `.env` file:

```env
OPENAI_API_KEY=your_openai_key
POLYGON_API_KEY=your_polygon_key
BRAVE_SEARCH_API_KEY=your_brave_key
```

### Run

```bash
# Launch Gradio UI
python app.py

# Or run CLI mode
python -m rebalancer.trader
```

## Project Structure

```
ai_portfolio_rebalancing/
├── app.py                      # Gradio UI entry point
├── portfolio.json              # Portfolio definition (editable)
├── rebalancer/                 # Agent definitions
│   ├── trader.py               # Orchestrator agent
│   ├── researcher.py           # Market research agent
│   └── analyst.py              # Financial analysis agent
├── portfolio_server/           # MCP server + data layer
│   ├── server.py               # MCP server with portfolio tools
│   └── portfolio.py            # Portfolio data & pricing logic
└── tests/                      # Test scripts
```

## Portfolio Configuration

Edit `portfolio.json` to customize your portfolio:

```json
{
  "name": "My Portfolio",
  "trading_fee": 0.002,
  "investor_profile": {
    "risk_level": "moderate",
    "time_horizon": 20,
    "constraints": ["no_leverage", "keep_some_cash"],
    "philosophy": "Long-term growth focus..."
  },
  "assets": [
    {
      "id": "amzn",
      "name": "Amazon",
      "type": "stock",
      "quantity": 100,
      "unit_purchase_price": 150.0,
      "unit_current_price": 185.0,
      "currency": "EUR",
      "polygon": { "ticker": "AMZN" }
    }
  ]
}
```

**Asset Types**: `stock`, `bond`, `crypto`, `cash`

**Tradeable Assets**: Only assets with `polygon.ticker` can be traded. Others (bonds, real estate) are included in allocation calculations but cannot be bought/sold.

## Demo

Try the live demo on [Hugging Face Spaces](https://huggingface.co/spaces/UZ31/ai_portfolio_rebalancing).

## Tech Stack

- **Agents**: OpenAI Agents SDK
- **Tools**: MCP (Model Context Protocol) via FastMCP
- **Pricing**: Polygon.io API
- **Research**: Brave Search API
- **UI**: Gradio
- **Visualization**: Plotly

## License

Apache 2.0 - See [LICENSE](LICENSE) for details.
