"""Market scanner — fetch and filter Polymarket markets from the Gamma API."""

import json
import requests
from datetime import datetime, timezone, timedelta
from typing import Dict, List

from config import (
    GAMMA_API_URL,
    MIN_LIQUIDITY,
    PRICE_RANGE_LOW,
    PRICE_RANGE_HIGH,
    MIN_HOURS_TO_RESOLUTION,
    SCAN_LIMIT,
)


def parse_market(raw: dict) -> dict:
    """Parse a raw Gamma API market response into a clean dict."""
    prices = json.loads(raw["outcomePrices"])
    token_ids = json.loads(raw["clobTokenIds"])
    return {
        "market_id": str(raw["id"]),
        "question": raw.get("question", ""),
        "description": raw.get("description", ""),
        "category": raw.get("category", ""),
        "end_date": raw["endDate"],
        "yes_price": float(prices[0]),
        "liquidity": raw["liquidityNum"],
        "volume_24h": raw.get("volume24hr", 0),
        "token_id_yes": token_ids[0],
        "token_id_no": token_ids[1],
    }


def _is_valid(raw: dict) -> bool:
    """Return True if the raw market passes all scanner filters."""
    # Must be open and active
    if raw.get("closed", True):
        return False
    if not raw.get("active", False):
        return False

    # Liquidity check
    if raw.get("liquidityNum", 0) < MIN_LIQUIDITY:
        return False

    # Price range check
    try:
        prices = json.loads(raw["outcomePrices"])
        yes_price = float(prices[0])
    except (KeyError, ValueError, json.JSONDecodeError):
        return False

    if yes_price < PRICE_RANGE_LOW or yes_price > PRICE_RANGE_HIGH:
        return False

    # Time-to-resolution check
    try:
        end_date_str = raw["endDate"]
        # Handle both offset-aware and offset-naive ISO strings
        if end_date_str.endswith("Z"):
            end_date_str = end_date_str[:-1] + "+00:00"
        end_date = datetime.fromisoformat(end_date_str)
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        hours_remaining = (end_date - now).total_seconds() / 3600
        if hours_remaining <= MIN_HOURS_TO_RESOLUTION:
            return False
    except (KeyError, ValueError):
        return False

    return True


def filter_markets(raw_markets: list) -> list:
    """Apply all filters and return list of parsed market dicts."""
    return [parse_market(raw) for raw in raw_markets if _is_valid(raw)]


def fetch_active_markets() -> list:
    """Fetch active markets from the Gamma API and return filtered list."""
    url = (
        f"{GAMMA_API_URL}/markets"
        f"?active=true&closed=false&limit={SCAN_LIMIT}"
        f"&order=volume24hr&ascending=false"
    )
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    raw_markets = response.json()
    return filter_markets(raw_markets)
