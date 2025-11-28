"""Test trade persistence across MCP subprocess restarts."""

import asyncio
import json
import os

STATE_FILE = ".portfolio_state.json"

def parse_mcp_result(result):
    """Parse MCP call_tool result to get JSON data."""
    # Result could be CallToolResult with content attribute
    if hasattr(result, 'content'):
        content = result.content
        if isinstance(content, list) and len(content) > 0:
            item = content[0]
            if hasattr(item, 'text'):
                return json.loads(item.text)
    # Or it could be a list directly
    if isinstance(result, list) and len(result) > 0:
        item = result[0]
        if hasattr(item, 'text'):
            return json.loads(item.text)
    return result

async def test_persistence():
    """Test that trades persist after MCP subprocess terminates."""
    from contextlib import AsyncExitStack
    from agents.mcp import MCPServerStdio

    print("=" * 60)
    print("Testing Trade Persistence")
    print("=" * 60)

    # Step 1: Check initial state
    print("\n1. Initial state file check:")
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            state = json.load(f)
        print(f"   Trades: {len(state.get('trades', []))}")
        print(f"   VNQ qty: {state.get('holdings', {}).get('VNQ', {}).get('quantity', 'N/A')}")
    else:
        print("   No state file exists (will be created)")

    # Step 2: Start MCP server and execute a trade
    print("\n2. Starting MCP server and executing trade...")
    async with AsyncExitStack() as stack:
        mcp = await stack.enter_async_context(
            MCPServerStdio(
                {"command": "uv", "args": ["run", "portfolio_mcp.py"]},
                client_session_timeout_seconds=60
            )
        )

        # List available tools
        tools = await mcp.list_tools()
        print(f"   Available tools: {[t.name for t in tools]}")

        # Check current state
        result = await mcp.call_tool("get_portfolio_state", {})
        state_data = parse_mcp_result(result)
        print(f"   Current VNQ holdings: {state_data['holdings'].get('VNQ', {}).get('quantity', 0)}")

        # Execute a trade
        print("\n3. Executing test trade: SELL 100 VNQ...")
        result = await mcp.call_tool("simulate_trade", {
            "action": "sell",
            "symbol": "VNQ",
            "quantity": 100,
            "rationale": "Test persistence"
        })
        trade = parse_mcp_result(result)
        print(f"   Trade result: {trade.get('action', 'error')} {trade.get('quantity', '')} @ ${trade.get('price', 0):.2f}")

        # Get trade history from MCP
        result = await mcp.call_tool("get_trade_history", {})
        trades = parse_mcp_result(result)
        print(f"   Trades in MCP memory: {len(trades)}")

    print("\n4. MCP server terminated. Checking state file...")

    # Step 3: Check state file after MCP terminates
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            state = json.load(f)
        trades = state.get("trades", [])
        vnq_qty = state.get("holdings", {}).get("VNQ", {}).get("quantity", "N/A")
        print(f"   Trades in state file: {len(trades)}")
        print(f"   VNQ quantity in state file: {vnq_qty}")

        if trades:
            print(f"\n   Last trade: {trades[-1].get('action')} {trades[-1].get('quantity')} {trades[-1].get('symbol')}")
            print("   ✓ Trade persistence WORKING!")
        else:
            print("   ✗ No trades in state file - persistence FAILED")
    else:
        print("   ✗ State file not found - persistence FAILED")

    # Step 4: Restart MCP and verify state is loaded
    print("\n5. Restarting MCP server to verify state is loaded...")
    async with AsyncExitStack() as stack:
        mcp = await stack.enter_async_context(
            MCPServerStdio(
                {"command": "uv", "args": ["run", "portfolio_mcp.py"]},
                client_session_timeout_seconds=60
            )
        )

        result = await mcp.call_tool("get_trade_history", {})
        trades = parse_mcp_result(result)
        print(f"   Trades loaded in new MCP instance: {len(trades)}")

        result = await mcp.call_tool("get_portfolio_state", {})
        state_data = parse_mcp_result(result)
        vnq_qty = state_data['holdings'].get('VNQ', {}).get('quantity', 0)
        print(f"   VNQ holdings in new MCP instance: {vnq_qty}")

        if trades and vnq_qty < 2600:
            print("\n   ✓ State correctly loaded after restart!")
        else:
            print("\n   ✗ State NOT loaded correctly after restart")

    print("\n" + "=" * 60)
    print("Test complete!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_persistence())
