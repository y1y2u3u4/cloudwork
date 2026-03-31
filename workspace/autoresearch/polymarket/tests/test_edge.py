"""Tests for edge.py - Edge Detector and Kelly Sizing"""
import pytest
from edge import calculate_edge, calculate_position_size, generate_signal


def test_calculate_edge_buy_yes():
    """ai=0.70, market=0.55 -> edge=0.15"""
    edge = calculate_edge(0.70, 0.55)
    assert abs(edge - 0.15) < 1e-9


def test_calculate_edge_buy_no():
    """ai=0.30, market=0.55 -> edge=-0.25"""
    edge = calculate_edge(0.30, 0.55)
    assert abs(edge - (-0.25)) < 1e-9


def test_position_size_quarter_kelly_clamped():
    """edge=0.15, market=0.55, bankroll=1000 -> kelly=0.333, quarter=83.3, clamped to 50"""
    size = calculate_position_size(edge=0.15, market_price=0.55, bankroll=1000)
    assert size == 50.0


def test_position_size_small_edge():
    """edge=0.10, market=0.50 -> exactly 50"""
    # kelly = 0.10 / (1 - 0.50) = 0.20, quarter = 0.05, size = 50
    # 0.05 * 1000 = 50.0
    size = calculate_position_size(edge=0.10, market_price=0.50, bankroll=1000)
    assert size == 50.0


def test_position_size_tiny_bankroll():
    """bankroll=100 -> below min -> 0.0"""
    # kelly = 0.10 / (1 - 0.50) = 0.20, quarter = 0.05, size = 0.05 * 100 = 5.0 < min_size=20
    size = calculate_position_size(edge=0.10, market_price=0.50, bankroll=100)
    assert size == 0.0


def test_generate_signal_yes():
    """generate_signal triggers YES: ai=0.75, confidence=0.85, market=0.55"""
    signal = generate_signal(
        market_id="test-market-1",
        question="Will X happen?",
        ai_prob=0.75,
        ai_confidence=0.85,
        market_price=0.55,
        bankroll=1000.0,
    )
    assert signal is not None
    assert signal["direction"] == "YES"
    assert signal["market_id"] == "test-market-1"
    assert "edge" in signal
    assert "size_usd" in signal


def test_generate_signal_no():
    """generate_signal triggers NO: ai=0.25, confidence=0.80, market=0.55"""
    signal = generate_signal(
        market_id="test-market-2",
        question="Will Y happen?",
        ai_prob=0.25,
        ai_confidence=0.80,
        market_price=0.55,
        bankroll=1000.0,
    )
    assert signal is not None
    assert signal["direction"] == "NO"


def test_generate_signal_below_edge_threshold():
    """ai=0.60, market=0.55 (edge=0.05) -> None"""
    signal = generate_signal(
        market_id="test-market-3",
        question="Will Z happen?",
        ai_prob=0.60,
        ai_confidence=0.85,
        market_price=0.55,
        bankroll=1000.0,
    )
    assert signal is None


def test_generate_signal_low_confidence():
    """confidence=0.50 -> None"""
    signal = generate_signal(
        market_id="test-market-4",
        question="Will W happen?",
        ai_prob=0.75,
        ai_confidence=0.50,
        market_price=0.55,
        bankroll=1000.0,
    )
    assert signal is None


def test_generate_signal_max_positions():
    """open_positions=20 -> None"""
    signal = generate_signal(
        market_id="test-market-5",
        question="Will V happen?",
        ai_prob=0.75,
        ai_confidence=0.85,
        market_price=0.55,
        bankroll=1000.0,
        open_positions=20,
    )
    assert signal is None
