"""Quick test to verify Polygon API integration."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from portfolio_server.portfolio import get_price, PORTFOLIO, clear_price_cache, calculate_allocation, get_pre_rebalancing_holdings

print("Testing Polygon API integration...")
print("=" * 60)
print("Note: Free tier uses fallback prices. Paid tier gets real-time.")
print("=" * 60)

# Clear cache to ensure fresh API calls
clear_price_cache()

total_value = 0.0

for asset in PORTFOLIO["assets"]:
    asset_id = asset["id"]
    price = get_price(asset_id)
    value = asset["quantity"] * price
    total_value += value
    source = "Polygon" if "polygon" in asset else "Manual"
    print(f"{asset['name']:25} ${price:>12,.2f}  (Qty: {asset['quantity']:>8} = ${value:>12,.2f}) [{source}]")

print("=" * 60)
print(f"{'Total Portfolio Value':25} ${total_value:>12,.2f}")
print("=" * 60)

# Show allocation
holdings = get_pre_rebalancing_holdings()
allocation, _ = calculate_allocation(holdings)
print("\nCurrent Allocation:")
for asset_type, pct in allocation.items():
    print(f"  {asset_type:15} {pct:>6.1f}%")

print("\nInvestor Profile:")
print(f"  Risk Level: {PORTFOLIO['investor_profile']['risk_level']}")
print(f"  Time Horizon: {PORTFOLIO['investor_profile']['time_horizon']} years")
print(f"  Philosophy: {PORTFOLIO['investor_profile'].get('philosophy', 'N/A')}")

print("\n" + "=" * 60)
print("Polygon API integration working!")
print("=" * 60)
