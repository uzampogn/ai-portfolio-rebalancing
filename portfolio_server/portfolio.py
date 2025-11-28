"""Portfolio data loader with flexible pricing (Polygon API or manual)."""

import json
import os
import re
import requests
from datetime import datetime, timedelta
from functools import lru_cache
from polygon import RESTClient
from dotenv import load_dotenv

load_dotenv(override=True)

# Initialize Polygon client
polygon_client = RESTClient(api_key=os.getenv("POLYGON_API_KEY"))

# Brave Search API
BRAVE_API_KEY = os.getenv("BRAVE_SEARCH_API_KEY")

# Portfolio file path (in project root)
PORTFOLIO_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "portfolio.json")

# =============================================================================
# PRICE CACHE CONFIGURATION
# =============================================================================
# Cache TTL (Time-To-Live) - prices valid for this duration
CACHE_TTL_MINUTES = 15

# Disk cache file path (in project root)
PRICE_CACHE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".price_cache.json")


def load_portfolio(path: str = PORTFOLIO_FILE) -> dict:
    """Load portfolio from JSON file.

    Args:
        path: Path to portfolio JSON file

    Returns:
        Portfolio dictionary with assets and investor profile
    """
    with open(path) as f:
        return json.load(f)


# Load portfolio at module import
PORTFOLIO = load_portfolio()
TRADING_FEE = PORTFOLIO.get("trading_fee", 0.002)

# =============================================================================
# TTL-BASED PRICE CACHE WITH DISK PERSISTENCE
# =============================================================================
# Cache structure: {asset_id: {"price": float, "source": str, "timestamp": str}}
_PRICE_CACHE = {}
_EXCHANGE_RATE_CACHE = {}  # {pair: {"rate": float, "timestamp": str}}


def _load_disk_cache() -> dict:
    """Load price cache from disk file."""
    if os.path.exists(PRICE_CACHE_FILE):
        try:
            with open(PRICE_CACHE_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not load price cache: {e}")
    return {}


def _save_disk_cache():
    """Save price cache to disk file."""
    try:
        cache_data = {
            "prices": _PRICE_CACHE,
            "exchange_rates": _EXCHANGE_RATE_CACHE,
            "saved_at": datetime.now().isoformat()
        }
        with open(PRICE_CACHE_FILE, "w") as f:
            json.dump(cache_data, f, indent=2)
    except IOError as e:
        print(f"Warning: Could not save price cache: {e}")


def _is_cache_valid(timestamp_str: str, ttl_minutes: int = CACHE_TTL_MINUTES) -> bool:
    """Check if a cached value is still valid based on TTL."""
    if not timestamp_str:
        return False
    try:
        cached_time = datetime.fromisoformat(timestamp_str)
        return datetime.now() - cached_time < timedelta(minutes=ttl_minutes)
    except (ValueError, TypeError):
        return False


def _get_cached_price(asset_id: str) -> tuple[float | None, str | None]:
    """Get price from cache if valid (not expired).

    Returns:
        Tuple of (price, source) or (None, None) if not cached or expired
    """
    if asset_id in _PRICE_CACHE:
        cached = _PRICE_CACHE[asset_id]
        if _is_cache_valid(cached.get("timestamp")):
            return cached["price"], cached["source"]
    return None, None


def _get_cached_price_any_age(asset_id: str) -> tuple[float | None, str | None]:
    """Get price from cache regardless of age (for fallback).

    Returns:
        Tuple of (price, source) or (None, None) if not cached
    """
    if asset_id in _PRICE_CACHE:
        cached = _PRICE_CACHE[asset_id]
        return cached.get("price"), cached.get("source")
    return None, None


def _set_cached_price(asset_id: str, price: float, source: str):
    """Cache a price with timestamp."""
    _PRICE_CACHE[asset_id] = {
        "price": price,
        "source": source,
        "timestamp": datetime.now().isoformat()
    }
    # Save to disk periodically (on every cache update for simplicity)
    _save_disk_cache()


# Load disk cache on module import
_disk_cache = _load_disk_cache()
if _disk_cache:
    _PRICE_CACHE = _disk_cache.get("prices", {})
    _EXCHANGE_RATE_CACHE = _disk_cache.get("exchange_rates", {})
    print(f"Loaded {len(_PRICE_CACHE)} cached prices from disk")


def get_usd_eur_rate() -> float:
    """Get current USD to EUR exchange rate with TTL caching.

    Returns:
        Exchange rate (e.g., 0.92 means 1 USD = 0.92 EUR)
    """
    # Check TTL-based cache first
    if "USD_EUR" in _EXCHANGE_RATE_CACHE:
        cached = _EXCHANGE_RATE_CACHE["USD_EUR"]
        if isinstance(cached, dict) and _is_cache_valid(cached.get("timestamp"), ttl_minutes=60):
            return cached["rate"]
        elif isinstance(cached, (int, float)):
            # Old format - treat as valid for backwards compatibility
            return cached

    try:
        # Try Polygon forex rate
        rate_data = polygon_client.get_previous_close_agg("C:USDEUR")
        if rate_data and len(rate_data) > 0 and rate_data[0].close:
            rate = rate_data[0].close
            _EXCHANGE_RATE_CACHE["USD_EUR"] = {
                "rate": rate,
                "timestamp": datetime.now().isoformat()
            }
            _save_disk_cache()
            print(f"USD/EUR rate from Polygon: {rate:.4f}")
            return rate
    except Exception as e:
        print(f"Polygon forex error: {e}")

    # Try to use expired cached rate before falling back to hardcoded
    if "USD_EUR" in _EXCHANGE_RATE_CACHE:
        cached = _EXCHANGE_RATE_CACHE["USD_EUR"]
        if isinstance(cached, dict) and cached.get("rate"):
            print(f"Using expired cached USD/EUR rate: {cached['rate']:.4f}")
            return cached["rate"]

    # Fallback to approximate rate
    fallback_rate = 0.92  # Approximate USD to EUR rate
    _EXCHANGE_RATE_CACHE["USD_EUR"] = {
        "rate": fallback_rate,
        "timestamp": datetime.now().isoformat()
    }
    print(f"Using fallback USD/EUR rate: {fallback_rate}")
    return fallback_rate


def convert_to_eur(price_usd: float) -> float:
    """Convert USD price to EUR.

    Args:
        price_usd: Price in USD

    Returns:
        Price in EUR
    """
    rate = get_usd_eur_rate()
    return price_usd * rate


def reload_portfolio():
    """Reload portfolio from JSON file to get latest changes.

    Call this before each rebalancing run to ensure latest data is used.
    """
    global PORTFOLIO, TRADING_FEE
    PORTFOLIO = load_portfolio()
    TRADING_FEE = PORTFOLIO.get("trading_fee", 0.002)
    print(f"Portfolio reloaded: {PORTFOLIO['name']} with {len(PORTFOLIO['assets'])} assets")


def get_asset_by_id(asset_id: str) -> dict | None:
    """Get asset definition by ID.

    Args:
        asset_id: Asset identifier (e.g., 'amzn', 'paris_apt')

    Returns:
        Asset dictionary or None if not found
    """
    for asset in PORTFOLIO["assets"]:
        if asset["id"] == asset_id:
            return asset
    return None


@lru_cache(maxsize=100)
def fetch_polygon_price(ticker: str) -> float | None:
    """Fetch price from Polygon API.

    Args:
        ticker: Polygon ticker (e.g., 'AMZN', 'X:BTCUSD')

    Returns:
        Price from Polygon or None if unavailable
    """
    try:
        # Try get_previous_close_agg first (works on free tier for stocks)
        try:
            aggs = polygon_client.get_previous_close_agg(ticker)
            if aggs and len(aggs) > 0 and aggs[0].close:
                return aggs[0].close
        except Exception:
            pass

        # Try daily aggregates (may work on free tier with delay)
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            aggs = list(polygon_client.list_aggs(
                ticker=ticker,
                multiplier=1,
                timespan="day",
                from_=start_date.strftime("%Y-%m-%d"),
                to=end_date.strftime("%Y-%m-%d"),
                limit=1,
                sort="desc"
            ))
            if aggs and len(aggs) > 0:
                return aggs[0].close
        except Exception:
            pass

        # Try get_last_trade (requires paid tier)
        try:
            last_trade = polygon_client.get_last_trade(ticker)
            if last_trade:
                return last_trade.price
        except Exception:
            pass

    except Exception as e:
        print(f"Polygon API error for {ticker}: {e}")

    return None


def fetch_price_from_brave_search(asset_name: str, ticker: str = None) -> tuple[float | None, str | None]:
    """Fetch price using Brave Search API from trusted financial platforms.

    Args:
        asset_name: Name of the asset (e.g., 'Amazon', 'Bitcoin')
        ticker: Optional ticker symbol for better search results

    Returns:
        Tuple of (price, source) where source is the platform name, or (None, None) if unavailable
    """
    if not BRAVE_API_KEY:
        return None, None

    # Trusted financial platforms to search
    trusted_platforms = [
        ("site:finance.google.com", "Google Finance"),
        ("site:finance.yahoo.com", "Yahoo Finance"),
        ("site:marketwatch.com", "MarketWatch"),
    ]

    for site_filter, platform_name in trusted_platforms:
        try:
            # Build search query targeting specific platform
            if ticker:
                search_query = f"{ticker} {asset_name} stock price {site_filter}"
            else:
                search_query = f"{asset_name} stock price {site_filter}"

            # Call Brave Search API
            headers = {
                "Accept": "application/json",
                "X-Subscription-Token": BRAVE_API_KEY
            }
            params = {
                "q": search_query,
                "count": 5
            }

            response = requests.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers=headers,
                params=params,
                timeout=10
            )

            if response.status_code != 200:
                continue

            data = response.json()

            # Try to extract price from search results
            web_results = data.get("web", {}).get("results", [])

            for result in web_results:
                # Check description and title for price patterns
                text = f"{result.get('title', '')} {result.get('description', '')}"

                # Pattern to match prices like $123.45, $1,234.56, etc.
                price_patterns = [
                    r'\$([0-9,]+\.?\d*)',  # $123.45 or $1,234.56
                    r'USD\s*([0-9,]+\.?\d*)',  # USD 123.45
                    r'price[:\s]+\$?([0-9,]+\.?\d*)',  # price: 123.45
                    r'([0-9,]+\.\d{2})\s*USD',  # 123.45 USD
                ]

                for pattern in price_patterns:
                    matches = re.findall(pattern, text, re.IGNORECASE)
                    for match in matches:
                        try:
                            price = float(match.replace(',', ''))
                            # Sanity check - price should be reasonable
                            if 0.01 < price < 1000000:
                                print(f"  {platform_name} found price for {asset_name}: ${price:.2f}")
                                return price, platform_name
                        except ValueError:
                            continue

        except Exception as e:
            print(f"Brave Search error for {asset_name} on {platform_name}: {e}")
            continue

    # Fallback: try general search without site filter
    try:
        if ticker:
            search_query = f"{ticker} {asset_name} stock price today USD"
        else:
            search_query = f"{asset_name} stock price today USD"

        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": BRAVE_API_KEY
        }
        params = {
            "q": search_query,
            "count": 5
        }

        response = requests.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers=headers,
            params=params,
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            web_results = data.get("web", {}).get("results", [])

            for result in web_results:
                text = f"{result.get('title', '')} {result.get('description', '')}"
                price_patterns = [
                    r'\$([0-9,]+\.?\d*)',
                    r'USD\s*([0-9,]+\.?\d*)',
                    r'price[:\s]+\$?([0-9,]+\.?\d*)',
                ]

                for pattern in price_patterns:
                    matches = re.findall(pattern, text, re.IGNORECASE)
                    for match in matches:
                        try:
                            price = float(match.replace(',', ''))
                            if 0.01 < price < 1000000:
                                print(f"  Brave Search found price for {asset_name}: ${price:.2f}")
                                return price, "Brave Search"
                        except ValueError:
                            continue

            # Also check infobox if available
            infobox = data.get("infobox", {})
            if infobox:
                for key, value in infobox.items():
                    if isinstance(value, str) and '$' in value:
                        matches = re.findall(r'\$([0-9,]+\.?\d*)', value)
                        for match in matches:
                            try:
                                price = float(match.replace(',', ''))
                                if 0.01 < price < 1000000:
                                    print(f"  Brave Search found price for {asset_name}: ${price:.2f}")
                                    return price, "Brave Search"
                            except ValueError:
                                continue

    except Exception as e:
        print(f"Brave Search general error for {asset_name}: {e}")

    return None, None


def _is_eur_ticker(ticker: str) -> bool:
    """Check if ticker returns EUR prices directly (e.g., X:BTCEUR)."""
    return "EUR" in ticker.upper()


def get_price(asset_id: str) -> float:
    """Get current price for an asset in the asset's currency (usually EUR).

    Price resolution order (with TTL-based caching):
    1. Check TTL cache - return if valid (not expired)
    2. If expired/missing and has 'polygon.ticker' -> fetch from Polygon API
    3. If Polygon fails -> use expired cache (last known good price)
    4. If no cached price -> try Brave Search
    5. If Brave fails -> use 'unit_current_price' (manual fallback)
    6. Final fallback -> 'unit_purchase_price'

    Currency conversion: USD prices from Polygon/Brave are converted to EUR
    if the asset's currency is EUR.

    Args:
        asset_id: Asset identifier

    Returns:
        Current price in asset's currency (EUR)
    """
    # 1. Check TTL-based cache first
    cached_price, cached_source = _get_cached_price(asset_id)
    if cached_price is not None:
        return cached_price

    asset = get_asset_by_id(asset_id)
    if not asset:
        print(f"Warning: Asset '{asset_id}' not found")
        return 0.0

    asset_currency = asset.get("currency", "EUR")
    price = None
    source = None

    # 2. Try Polygon API if ticker is defined
    if "polygon" in asset:
        ticker = asset["polygon"]["ticker"]
        price = fetch_polygon_price(ticker)

        if price is not None:
            # Check if conversion needed (USD ticker but EUR asset)
            if asset_currency == "EUR" and not _is_eur_ticker(ticker):
                price = convert_to_eur(price)
            _set_cached_price(asset_id, price, "Polygon API")
            return price

        # 3. Polygon failed - try expired cache (last known good price)
        expired_price, expired_source = _get_cached_price_any_age(asset_id)
        if expired_price is not None:
            print(f"Using cached price for {asset['name']} (source: {expired_source})")
            return expired_price

        # 4. No cached price - try Brave Search as fallback
        print(f"Warning: No Polygon data for {asset['name']}, trying Brave Search...")
        price, source = fetch_price_from_brave_search(asset["name"], ticker)
        if price is not None:
            # Brave Search returns USD prices - convert if needed
            if asset_currency == "EUR":
                price = convert_to_eur(price)
            _set_cached_price(asset_id, price, source)
            return price

        print(f"Warning: Brave Search also failed for {asset['name']}, using manual fallback")

    # For assets without Polygon ticker - only try Brave Search for tradeable types
    # Cash, bonds, real_estate should use manual values (Brave Search gives garbage)
    elif asset["type"] in ["stock", "crypto"]:
        # Check expired cache first
        expired_price, expired_source = _get_cached_price_any_age(asset_id)
        if expired_price is not None:
            print(f"Using cached price for {asset['name']} (source: {expired_source})")
            return expired_price

        print(f"No Polygon ticker for {asset['name']}, trying Brave Search...")
        price, source = fetch_price_from_brave_search(asset["name"])
        if price is not None:
            # Brave Search returns USD prices - convert if needed
            if asset_currency == "EUR":
                price = convert_to_eur(price)
            _set_cached_price(asset_id, price, source)
            return price

    # 5. Use manual unit_current_price if defined (already in asset's currency)
    if "unit_current_price" in asset:
        price = asset["unit_current_price"]
        _set_cached_price(asset_id, price, "manual (unit_current_price)")
        return price

    # 6. Final fallback to purchase price (already in asset's currency)
    price = asset["unit_purchase_price"]
    _set_cached_price(asset_id, price, "fallback (unit_purchase_price)")
    return price


def get_price_with_source(asset_id: str) -> tuple[float, str]:
    """Get current price for an asset with source information.

    Uses TTL-based caching with improved fallback chain.

    Args:
        asset_id: Asset identifier

    Returns:
        Tuple of (price_in_eur, source) where source indicates where the price came from
    """
    # 1. Check TTL-based cache first
    cached_price, cached_source = _get_cached_price(asset_id)
    if cached_price is not None:
        return cached_price, cached_source

    asset = get_asset_by_id(asset_id)
    if not asset:
        print(f"Warning: Asset '{asset_id}' not found")
        return 0.0, "unknown"

    asset_currency = asset.get("currency", "EUR")
    result = None

    # 2. Try Polygon API if ticker is defined
    if "polygon" in asset:
        ticker = asset["polygon"]["ticker"]
        price = fetch_polygon_price(ticker)
        if price is not None:
            # Convert USD to EUR if needed
            if asset_currency == "EUR" and not _is_eur_ticker(ticker):
                price = convert_to_eur(price)
            _set_cached_price(asset_id, price, "Polygon API")
            result = (price, "Polygon API")
        else:
            # 3. Polygon failed - try expired cache
            expired_price, expired_source = _get_cached_price_any_age(asset_id)
            if expired_price is not None:
                print(f"Using cached price for {asset['name']} (source: {expired_source})")
                result = (expired_price, expired_source)
            else:
                # 4. No cached price - try Brave Search
                print(f"Warning: No Polygon data for {asset['name']}, trying Brave Search...")
                price, source = fetch_price_from_brave_search(asset["name"], ticker)
                if price is not None:
                    if asset_currency == "EUR":
                        price = convert_to_eur(price)
                    _set_cached_price(asset_id, price, source)
                    result = (price, source)
                else:
                    print(f"Warning: Brave Search also failed for {asset['name']}, using manual fallback")

    # For assets without Polygon ticker - only try Brave Search for tradeable types
    elif asset["type"] in ["stock", "crypto"]:
        # Check expired cache first
        expired_price, expired_source = _get_cached_price_any_age(asset_id)
        if expired_price is not None:
            print(f"Using cached price for {asset['name']} (source: {expired_source})")
            result = (expired_price, expired_source)
        else:
            print(f"No Polygon ticker for {asset['name']}, trying Brave Search...")
            price, source = fetch_price_from_brave_search(asset["name"])
            if price is not None:
                if asset_currency == "EUR":
                    price = convert_to_eur(price)
                _set_cached_price(asset_id, price, source)
                result = (price, source)

    # 5. If no API price found, use manual values
    if result is None:
        if "unit_current_price" in asset:
            price = asset["unit_current_price"]
            _set_cached_price(asset_id, price, "manual (unit_current_price)")
            result = (price, "manual")
        else:
            result = (asset["unit_purchase_price"], "purchase_price")

    # Final fallback - cache and return
    if result[1] == "purchase_price":
        _set_cached_price(asset_id, result[0], "fallback (unit_purchase_price)")

    return result


def calculate_allocation(holdings: dict) -> tuple[dict, float]:
    """Calculate current allocation percentages.

    Args:
        holdings: Dict of {asset_id: {"type": str, "quantity": float, ...}}

    Returns:
        Tuple of (allocation_dict, total_value)
    """
    total_value = 0.0
    type_values = {}

    # Calculate total value and value per type
    for asset_id, data in holdings.items():
        current_price = get_price(asset_id)
        asset_value = data["quantity"] * current_price
        total_value += asset_value

        asset_type = data["type"]
        type_values[asset_type] = type_values.get(asset_type, 0) + asset_value

    # Calculate percentages
    allocation = {}
    if total_value > 0:
        for asset_type, value in type_values.items():
            allocation[asset_type] = (value / total_value) * 100

    return allocation, total_value


def clear_price_cache(force: bool = False):
    """Clear price caches.

    With TTL-based caching, this is usually not needed. The cache will
    automatically refresh when entries expire.

    Args:
        force: If True, clear all caches including disk cache.
               If False (default), only clear the lru_cache for Polygon API.
    """
    global _PRICE_CACHE, _EXCHANGE_RATE_CACHE

    if force:
        # Full cache clear - use sparingly
        _PRICE_CACHE = {}
        _EXCHANGE_RATE_CACHE = {}
        fetch_polygon_price.cache_clear()
        # Also delete disk cache file
        if os.path.exists(PRICE_CACHE_FILE):
            try:
                os.remove(PRICE_CACHE_FILE)
                print("Cleared disk price cache")
            except IOError:
                pass
        print("Price cache fully cleared")
    else:
        # Soft clear - only clear the lru_cache to allow fresh Polygon calls
        # TTL cache is preserved to avoid rate limiting
        fetch_polygon_price.cache_clear()


def get_pre_rebalancing_holdings() -> dict:
    """Get pre-rebalancing holdings from portfolio definition.

    These are the holdings BEFORE any trades are executed.

    Returns:
        Dict of {asset_id: {"type": str, "quantity": float, "avg_price": float, ...}}
    """
    return {
        asset["id"]: {
            "type": asset["type"],
            "quantity": asset["quantity"],
            "avg_price": asset["unit_purchase_price"],
            "name": asset["name"],
            "currency": asset.get("currency", "USD")
        }
        for asset in PORTFOLIO["assets"]
    }


def calculate_original_investment() -> float:
    """Calculate original investment value from purchase prices.

    This is the total amount originally invested (cost basis).

    Returns:
        Total original investment based on unit_purchase_price * quantity
    """
    total = 0.0
    for asset in PORTFOLIO["assets"]:
        total += asset["quantity"] * asset["unit_purchase_price"]
    return total
