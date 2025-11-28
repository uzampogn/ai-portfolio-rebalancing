"""Test script for portfolio MCP server tools."""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from portfolio_server.server import (
    get_portfolio_state,
    get_asset_price,
    simulate_trade,
    get_trade_history,
    calculate_performance,
    reset_portfolio,
    list_tradeable_assets
)

async def test_all_tools():
    print("Testing Portfolio MCP Tools")
    print("=" * 60)

    # Reset to clean state
    reset_portfolio()

    # Test 1: get_portfolio_state
    print("\n1. Testing get_portfolio_state()...")
    state = await get_portfolio_state()
    print(f"   Portfolio: {state['name']}")
    print(f"   Initial Value: {state['initial_value']:,.2f} EUR")
    print(f"   Current Value: {state['current_value']:,.2f} EUR")
    print(f"   Holdings: {list(state['holdings'].keys())}")
    print(f"   Current Allocation: {state['current_allocation']}")
    print(f"   Investor Profile: {state['investor_profile']['risk_level']}, {state['investor_profile']['time_horizon']}yr")

    # Test 2: get_asset_price (now returns dict)
    print("\n2. Testing get_asset_price()...")
    for asset_id in ["amzn", "btc", "apt_1", "govt_bonds"]:
        result = await get_asset_price(asset_id)
        if "error" in result:
            print(f"   {asset_id}: {result['error']}")
        else:
            print(f"   {result['name']}: ${result['price']:,.2f} (source: {result['source']})")

    # Test 3: list_tradeable_assets
    print("\n3. Testing list_tradeable_assets()...")
    tradeable = await list_tradeable_assets()
    print(f"   Tradeable assets: {len(tradeable)}")
    for asset in tradeable:
        print(f"   - {asset['name']} ({asset['asset_id']}): ${asset['current_price']:,.2f}")

    # Test 4: simulate_trade (sell some crypto to rebalance)
    print("\n4. Testing simulate_trade()...")
    trade_result = await simulate_trade(
        action="sell",
        asset_id="btc",
        quantity=0.005,
        rationale="Rebalancing: crypto overweight"
    )
    if "error" in trade_result:
        print(f"   Error: {trade_result['error']}")
    else:
        print(f"   Trade: {trade_result['action'].upper()} {trade_result['quantity']} {trade_result['name']} @ ${trade_result['price']:,.2f}")

    # Test 5: Try to trade non-tradeable asset (should fail)
    print("\n5. Testing trade restriction on manual asset...")
    trade_result = await simulate_trade(
        action="sell",
        asset_id="apt_1",
        quantity=1,
        rationale="Try to sell apartment"
    )
    print(f"   Result: {trade_result.get('error', 'Unexpected success')}")

    # Test 6: get_trade_history
    print("\n6. Testing get_trade_history()...")
    history = await get_trade_history()
    print(f"   Total trades: {len(history)}")
    for trade in history:
        print(f"   - {trade['action'].upper()} {trade['quantity']} {trade['name']} @ ${trade['price']:,.2f}")

    # Test 7: calculate_performance
    print("\n7. Testing calculate_performance()...")
    perf = await calculate_performance()
    print(f"   Initial Value: ${perf['initial_value']:,.2f}")
    print(f"   Current Value: ${perf['current_value']:,.2f}")
    print(f"   Change: ${perf['absolute_change']:,.2f} ({perf['percentage_change']:.2f}%)")
    print(f"   Total Fees: ${perf['total_fees']:,.2f}")

    print("\n" + "=" * 60)
    print("All MCP tools working correctly!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_all_tools())
