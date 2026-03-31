"""Tests for monitor.py formatting functions."""
import pytest
from polymarket.monitor import (
    format_signal_report,
    format_stats_report,
    format_daily_summary,
)


def test_format_signal_report():
    signal = {
        "market_id": "123",
        "question": "Will BTC hit 100k?",
        "direction": "YES",
        "edge": 0.15,
        "ai_prob": 0.70,
        "market_price": 0.55,
        "size_usd": 35.0,
    }
    report = format_signal_report(signal, reasoning="Strong momentum signals")
    assert "Will BTC hit 100k?" in report
    assert "YES" in report
    assert "15.0%" in report
    assert "$35" in report


def test_format_signal_report_no_reasoning():
    signal = {
        "market_id": "456",
        "question": "Will ETH hit 5k?",
        "direction": "NO",
        "edge": 0.10,
        "ai_prob": 0.30,
        "market_price": 0.40,
        "size_usd": 50.0,
    }
    report = format_signal_report(signal)
    assert "Will ETH hit 5k?" in report
    assert "NO" in report
    assert "10.0%" in report
    assert "$50" in report


def test_format_signal_report_probabilities():
    signal = {
        "market_id": "789",
        "question": "Test question?",
        "direction": "YES",
        "edge": 0.20,
        "ai_prob": 0.75,
        "market_price": 0.55,
        "size_usd": 100.0,
    }
    report = format_signal_report(signal, reasoning="Test reasoning")
    assert "75.0%" in report
    assert "55.0%" in report
    assert "Strong momentum" in report or "Test reasoning" in report


def test_format_stats_report():
    stats = {
        "total": 50,
        "resolved": 30,
        "unresolved": 20,
        "avg_brier_score": 0.18,
    }
    category_stats = [
        {"category": "Politics", "count": 15, "avg_brier": 0.15},
        {"category": "Crypto", "count": 10, "avg_brier": 0.22},
    ]
    report = format_stats_report(stats, category_stats)
    assert "50" in report
    assert "0.18" in report
    assert "Politics" in report
    assert "Crypto" in report


def test_format_stats_report_no_categories():
    stats = {
        "total": 10,
        "resolved": 5,
        "unresolved": 5,
        "avg_brier_score": 0.25,
    }
    report = format_stats_report(stats)
    assert "10" in report
    assert "0.25" in report


def test_format_stats_report_counts():
    stats = {
        "total": 50,
        "resolved": 30,
        "unresolved": 20,
        "avg_brier_score": 0.18,
    }
    category_stats = [
        {"category": "Politics", "count": 15, "avg_brier": 0.15},
    ]
    report = format_stats_report(stats, category_stats)
    assert "30" in report
    assert "20" in report
    assert "15" in report


def test_format_daily_summary():
    stats = {
        "total": 100,
        "resolved": 60,
        "unresolved": 40,
        "avg_brier_score": 0.20,
    }
    signals = [
        {"market_id": "1", "question": "Q1?", "direction": "YES", "edge": 0.12},
        {"market_id": "2", "question": "Q2?", "direction": "NO", "edge": 0.08},
    ]
    report = format_daily_summary(stats, signals, new_predictions=5)
    assert "5" in report
    assert "2" in report  # active signals count
    assert "0.20" in report or "0.2" in report


def test_format_daily_summary_empty_signals():
    stats = {
        "total": 0,
        "resolved": 0,
        "unresolved": 0,
        "avg_brier_score": 0.0,
    }
    report = format_daily_summary(stats, [], new_predictions=0)
    assert "0" in report
