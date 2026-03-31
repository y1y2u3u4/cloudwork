"""Tests for scanner.py — no real API calls."""

import json
import pytest
from datetime import datetime, timezone, timedelta

from scanner import parse_market, filter_markets


def _make_raw_market(overrides=None):
    base = {
        "id": "100",
        "question": "Will X happen by June?",
        "description": "Test market description",
        "category": "Politics",
        "endDate": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "liquidityNum": 10000.0,
        "outcomePrices": json.dumps(["0.55", "0.45"]),
        "clobTokenIds": json.dumps(["token_yes_100", "token_no_100"]),
        "active": True,
        "closed": False,
        "acceptingOrders": True,
        "volume24hr": 5000,
    }
    if overrides:
        base.update(overrides)
    return base


class TestParseMarket:
    def test_parse_extracts_all_fields(self):
        raw = _make_raw_market()
        result = parse_market(raw)

        assert result["market_id"] == "100"
        assert result["question"] == "Will X happen by June?"
        assert result["description"] == "Test market description"
        assert result["category"] == "Politics"
        assert result["yes_price"] == pytest.approx(0.55)
        assert result["liquidity"] == 10000.0
        assert result["volume_24h"] == 5000
        assert result["token_id_yes"] == "token_yes_100"
        assert result["token_id_no"] == "token_no_100"

    def test_parse_market_id_is_string(self):
        raw = _make_raw_market({"id": 999})
        result = parse_market(raw)
        assert result["market_id"] == "999"
        assert isinstance(result["market_id"], str)

    def test_parse_yes_price_is_float(self):
        raw = _make_raw_market({"outcomePrices": json.dumps(["0.30", "0.70"])})
        result = parse_market(raw)
        assert result["yes_price"] == pytest.approx(0.30)
        assert isinstance(result["yes_price"], float)

    def test_parse_end_date(self):
        end = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
        raw = _make_raw_market({"endDate": end})
        result = parse_market(raw)
        assert result["end_date"] == end


class TestFilterMarkets:
    def test_keeps_valid_market(self):
        markets = [_make_raw_market()]
        result = filter_markets(markets)
        assert len(result) == 1
        assert result[0]["market_id"] == "100"

    def test_removes_low_liquidity(self):
        markets = [_make_raw_market({"liquidityNum": 4999.0})]
        result = filter_markets(markets)
        assert len(result) == 0

    def test_keeps_exactly_min_liquidity(self):
        markets = [_make_raw_market({"liquidityNum": 5000.0})]
        result = filter_markets(markets)
        assert len(result) == 1

    def test_removes_price_too_low(self):
        markets = [_make_raw_market({"outcomePrices": json.dumps(["0.14", "0.86"])})]
        result = filter_markets(markets)
        assert len(result) == 0

    def test_removes_price_too_high(self):
        markets = [_make_raw_market({"outcomePrices": json.dumps(["0.86", "0.14"])})]
        result = filter_markets(markets)
        assert len(result) == 0

    def test_keeps_price_at_boundary_low(self):
        markets = [_make_raw_market({"outcomePrices": json.dumps(["0.15", "0.85"])})]
        result = filter_markets(markets)
        assert len(result) == 1

    def test_keeps_price_at_boundary_high(self):
        markets = [_make_raw_market({"outcomePrices": json.dumps(["0.85", "0.15"])})]
        result = filter_markets(markets)
        assert len(result) == 1

    def test_removes_near_expiry(self):
        soon = (datetime.now(timezone.utc) + timedelta(hours=23)).isoformat()
        markets = [_make_raw_market({"endDate": soon})]
        result = filter_markets(markets)
        assert len(result) == 0

    def test_keeps_market_with_enough_time(self):
        future = (datetime.now(timezone.utc) + timedelta(hours=25)).isoformat()
        markets = [_make_raw_market({"endDate": future})]
        result = filter_markets(markets)
        assert len(result) == 1

    def test_removes_closed_market(self):
        markets = [_make_raw_market({"closed": True})]
        result = filter_markets(markets)
        assert len(result) == 0

    def test_removes_inactive_market(self):
        markets = [_make_raw_market({"active": False})]
        result = filter_markets(markets)
        assert len(result) == 0

    def test_filters_multiple_markets(self):
        markets = [
            _make_raw_market({"id": "1"}),  # valid
            _make_raw_market({"id": "2", "liquidityNum": 100.0}),  # low liquidity
            _make_raw_market({"id": "3", "outcomePrices": json.dumps(["0.05", "0.95"])}),  # bad price
            _make_raw_market({"id": "4", "closed": True}),  # closed
            _make_raw_market({"id": "5"}),  # valid
        ]
        result = filter_markets(markets)
        assert len(result) == 2
        ids = {m["market_id"] for m in result}
        assert ids == {"1", "5"}

    def test_empty_list(self):
        result = filter_markets([])
        assert result == []
