"""Simple Gradio UI for portfolio rebalancing."""

import gradio as gr
import plotly.graph_objects as go
import pandas as pd
from portfolio_server import portfolio as portfolio_data
from portfolio_server.portfolio import calculate_allocation, get_pre_rebalancing_holdings, reload_portfolio
import asyncio
import os
from rebalancer.trader import run_rebalancing
from portfolio_server import server as portfolio_mcp

# =============================================================================
# AUTO-RESET STATE ON APP STARTUP
# =============================================================================
# Delete stale state file to ensure fresh prices on each app start
STATE_FILE = os.path.join(os.path.dirname(__file__), ".portfolio_state.json")
if os.path.exists(STATE_FILE):
    os.remove(STATE_FILE)
    print("Cleared stale state file on app startup")

def get_pre_rebalancing_data():
    """Get pre-rebalancing portfolio data with real-time prices.

    This represents the portfolio state BEFORE any trades are executed.
    Reloads portfolio.json to ensure latest data is used.

    Note: Uses TTL-based price cache - prices refresh automatically when expired.
    """
    reload_portfolio()  # Reload from JSON file to get latest changes
    # TTL-based cache handles freshness - no need to force clear
    holdings = get_pre_rebalancing_holdings()
    allocation, total_value = calculate_allocation(holdings)

    return {
        "name": portfolio_data.PORTFOLIO["name"],
        "current_value": total_value,
        "allocation": allocation,
        "profile": portfolio_data.PORTFOLIO["investor_profile"]
    }

# Fixed color mapping for asset classes (distinct colors)
ASSET_COLORS = {
    "stock": "#2ECC71",      # Green
    "bond": "#3498DB",       # Blue
    "crypto": "#F39C12",     # Orange/Gold
    "real_estate": "#9B59B6", # Purple
    "cash": "#95A5A6"        # Gray
}

def create_allocation_pie_chart(allocation, title="Portfolio Allocation"):
    """Create a pie chart for allocation with consistent colors per asset class."""
    if not allocation:
        # Empty chart placeholder
        fig = go.Figure()
        fig.add_annotation(
            text="No data yet",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="gray")
        )
        fig.update_layout(title=title, height=350)
        return fig

    # Get colors in the same order as labels
    labels = list(allocation.keys())
    colors = [ASSET_COLORS.get(label, "#98D8C8") for label in labels]

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=list(allocation.values()),
        hole=.4,
        marker=dict(colors=colors)
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
    philosophy = data['profile'].get('philosophy', 'Not specified')
    html = f"""
    <div style='padding: 20px; background: #f0f0f0; border-radius: 10px;'>
        <h2 style='text-align: center; color: #333;'>{data['name']}</h2>
        <div style='text-align: center; font-size: 24px; margin: 20px 0;'>
            <span style='color: #666;'>Current Value:</span>
            <span style='color: #2c3e50; font-weight: bold;'>{data['current_value']:,.2f} EUR</span>
        </div>
        <div style='text-align: center; font-size: 16px;'>
            <span style='color: #666;'>Risk Level:</span>
            <span style='color: #e74c3c; font-weight: bold;'>{data['profile']['risk_level'].upper()}</span>
            <span style='margin: 0 20px;'>|</span>
            <span style='color: #666;'>Time Horizon:</span>
            <span style='color: #3498db; font-weight: bold;'>{data['profile']['time_horizon']} years</span>
        </div>
        <div style='text-align: center; font-size: 14px; margin-top: 15px; color: #555; font-style: italic;'>
            "{philosophy}"
        </div>
        <div style='text-align: center; font-size: 12px; margin-top: 10px; color: #27ae60;'>
            Prices from Polygon API (tradeable) + manual valuations
        </div>
    </div>
    """
    return html

def run_rebalancing_sync():
    """Synchronous wrapper for async rebalancing."""
    # 1. Capture PRE-REBALANCING state FIRST (before any trades)
    # TTL-based cache handles freshness automatically
    pre_rebalancing_data = get_pre_rebalancing_data()
    pre_rebalancing_allocation = pre_rebalancing_data["allocation"]

    # 2. Reset portfolio and run agent (trades happen here)
    portfolio_mcp.reset_portfolio()

    print("\n" + "="*70)
    print("STARTING 3-AGENT REBALANCING SYSTEM")
    print("="*70)
    asyncio.run(run_rebalancing())

    # 3. Load POST-REBALANCING state from shared file (updated by MCP subprocess)
    portfolio_mcp.load_state()

    # Get results
    trades = portfolio_mcp.TRADES
    analysis = portfolio_mcp.ANALYSIS

    # 4. Calculate POST-REBALANCING allocation
    # TTL-based cache handles freshness - no need to clear
    post_rebalancing_holdings = portfolio_mcp.CURRENT_HOLDINGS
    post_rebalancing_allocation, _ = calculate_allocation(post_rebalancing_holdings)

    # 5. Create charts with clear naming
    before_chart = create_allocation_pie_chart(
        pre_rebalancing_allocation,
        "Before Rebalancing"
    )

    after_chart = create_allocation_pie_chart(
        post_rebalancing_allocation,
        "After Rebalancing"
    )

    # Create trades dataframe
    if trades:
        trades_df = pd.DataFrame(trades)
        trades_df = trades_df.sort_values('timestamp', ascending=False)
        # Handle both old (symbol) and new (asset_id/name) formats
        if 'name' in trades_df.columns:
            trades_df = trades_df[['timestamp', 'action', 'name', 'quantity', 'price', 'fees', 'rationale']]
            trades_df = trades_df.rename(columns={'name': 'asset'})
        else:
            trades_df = trades_df[['timestamp', 'action', 'symbol', 'quantity', 'price', 'fees', 'rationale']]
            trades_df = trades_df.rename(columns={'symbol': 'asset'})

        # Add total value column (quantity × price)
        trades_df['total'] = trades_df['quantity'] * trades_df['price']

        # Calculate totals by action
        total_bought = trades_df[trades_df['action'] == 'buy']['total'].sum()
        total_sold = trades_df[trades_df['action'] == 'sell']['total'].sum()
        total_fees = trades_df['fees'].sum()

        # Add summary rows
        summary_rows = pd.DataFrame([
            {'timestamp': '', 'action': '', 'asset': '', 'quantity': '', 'price': '', 'fees': '', 'rationale': '', 'total': ''},
            {'timestamp': '', 'action': 'TOTAL SOLD', 'asset': '', 'quantity': '', 'price': '', 'fees': '', 'rationale': '', 'total': total_sold},
            {'timestamp': '', 'action': 'TOTAL BOUGHT', 'asset': '', 'quantity': '', 'price': '', 'fees': '', 'rationale': '', 'total': total_bought},
            {'timestamp': '', 'action': 'TOTAL FEES', 'asset': '', 'quantity': '', 'price': '', 'fees': total_fees, 'rationale': '', 'total': ''},
        ])
        trades_df = pd.concat([trades_df, summary_rows], ignore_index=True)

        # Reorder columns to put total after price
        trades_df = trades_df[['timestamp', 'action', 'asset', 'quantity', 'price', 'total', 'fees', 'rationale']]
    else:
        trades_df = pd.DataFrame(columns=['timestamp', 'action', 'asset', 'quantity', 'price', 'total', 'fees', 'rationale'])

    # Format analysis for display (handles both old string format and new structured format)
    portfolio_analysis_data = analysis.get("portfolio_analysis")
    if isinstance(portfolio_analysis_data, dict):
        # New structured format with computed values (PRE-REBALANCING)
        computed = portfolio_analysis_data.get("computed", {})
        commentary = portfolio_analysis_data.get("commentary", "")
        allocation = computed.get("allocation", {})
        allocation_str = ", ".join(f"{k}: {v}%" for k, v in sorted(allocation.items(), key=lambda x: -x[1]) if v > 0)

        original_investment = computed.get('original_investment', 0)

        portfolio_analysis = f"""**PRE-REBALANCING PORTFOLIO ANALYSIS**

- **Current Value:** {computed.get('total_value_formatted', 'N/A')}
- **Original Investment:** €{original_investment:,.2f}
- **Total Return:** {computed.get('performance_formatted', 'N/A')}
- **Allocation:** {allocation_str}

**Analysis:**
{commentary}"""
    else:
        portfolio_analysis = portfolio_analysis_data or "No analysis available"

    target_allocation_data = analysis.get("target_allocation")
    if isinstance(target_allocation_data, dict):
        # Show only the recommendation/rationale
        commentary = target_allocation_data.get("commentary", "")
        target_allocation_rationale = f"""**TARGET ALLOCATION RECOMMENDATION**

{commentary}"""
    else:
        target_allocation_rationale = target_allocation_data or "No rationale available"

    return (
        before_chart,
        after_chart,
        trades_df,
        portfolio_analysis,
        target_allocation_rationale,
        f"Rebalancing completed! {len(trades)} trades executed."
    )

def create_ui():
    """Create the Gradio interface."""

    pre_rebalancing_data = get_pre_rebalancing_data()

    with gr.Blocks() as app:

        gr.Markdown("# MVP - Portfolio Rebalancing Tool (3-Agent System)")
        gr.Markdown("**Researcher** -> **Financial Analyst** -> **Trader** working together")

        # Portfolio info and system explanation side by side
        with gr.Row():
            with gr.Column():
                gr.HTML(format_portfolio_summary(pre_rebalancing_data))
            with gr.Column():
                gr.Markdown("""
                ### How the 3-Agent System Works:
                1. **Trader Agent** (Orchestrator) coordinates the entire process
                2. **Researcher Agent** investigates market conditions for each asset class
                3. **Financial Analyst Agent** analyzes portfolio, recommends **target allocation** and specific trades
                4. **Trader Agent** executes the recommended trades and reports results

                ### Asset Types:
                - **Tradeable** (Polygon API): Stocks, ETFs, Crypto - can be bought/sold
                - **Manual Valuation**: Real estate, Bonds - included in allocation but cannot be traded
                """)

        # Action button
        with gr.Row():
            with gr.Column():
                status_text = gr.Textbox(
                    label="Status",
                    value="Ready - Financial Analyst will recommend target allocation",
                    interactive=False
                )
            with gr.Column():
                run_btn = gr.Button(
                    "Run 3-Agent Rebalancing",
                    variant="primary",
                    size="lg"
                )

        gr.Markdown("---")
        gr.Markdown("## Portfolio Comparison")

        # Charts row - before and after rebalancing
        with gr.Row():
            with gr.Column():
                before_chart = gr.Plot(
                    create_allocation_pie_chart(pre_rebalancing_data["allocation"], "Before Rebalancing"),
                    label="Before Rebalancing"
                )
            with gr.Column():
                after_chart = gr.Plot(
                    create_allocation_pie_chart({}, "After Rebalancing"),
                    label="After Rebalancing (run agent to see)"
                )

        gr.Markdown("---")
        gr.Markdown("## Financial Analyst Rationale")

        with gr.Row(equal_height=True):
            with gr.Column():
                gr.Markdown("**Portfolio Analysis**")
                portfolio_analysis_text = gr.Markdown(
                    value="*Run rebalancing to see analysis...*"
                )
            with gr.Column():
                gr.Markdown("**Target Allocation Recommendation**")
                target_allocation_text = gr.Markdown(
                    value="*Run rebalancing to see recommendation...*"
                )

        gr.Markdown("---")
        gr.Markdown("## Trade History")

        trades_table = gr.Dataframe(
            value=pd.DataFrame(columns=['timestamp', 'action', 'asset', 'quantity', 'price', 'total', 'fees', 'rationale']),
            label="Simulated Trades (Only tradeable assets with Polygon tickers)",
            wrap=True,
            interactive=False
        )

        # Event handler
        run_btn.click(
            fn=run_rebalancing_sync,
            inputs=[],
            outputs=[
                before_chart,
                after_chart,
                trades_table,
                portfolio_analysis_text,
                target_allocation_text,
                status_text
            ]
        )

    return app

if __name__ == "__main__":
    app = create_ui()
    app.launch(inbrowser=True, share=False)
