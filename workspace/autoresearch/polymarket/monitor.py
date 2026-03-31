"""Monitor and stats formatting functions for Polymarket trading signals."""
from typing import Dict, List, Optional


def format_signal_report(signal: dict, reasoning: str = "") -> str:
    """Format a trade signal for display.

    Args:
        signal: dict with keys: market_id, question, direction, ai_prob,
                market_price, edge, size_usd
        reasoning: optional explanation for the signal

    Returns:
        Formatted string report
    """
    question = signal.get("question", "Unknown")
    direction = signal.get("direction", "N/A")
    ai_prob = signal.get("ai_prob", 0.0)
    market_price = signal.get("market_price", 0.0)
    edge = signal.get("edge", 0.0)
    size_usd = signal.get("size_usd", 0.0)

    lines = [
        f"📊 Signal: {question}",
        f"Direction: {direction}",
        f"AI Prediction: {ai_prob:.1%}",
        f"Market Price: {market_price:.1%}",
        f"Edge: {edge:.1%}",
        f"Size: ${size_usd:.0f}",
    ]

    if reasoning:
        lines.append(f"Reasoning: {reasoning}")

    return "\n".join(lines)


def format_stats_report(stats: dict, category_stats: Optional[List[dict]] = None) -> str:
    """Format prediction statistics.

    Args:
        stats: dict with keys: total, resolved, unresolved, avg_brier_score
        category_stats: optional list of dicts with keys: category, count, avg_brier

    Returns:
        Formatted string report
    """
    total = stats.get("total", 0)
    resolved = stats.get("resolved", 0)
    unresolved = stats.get("unresolved", 0)
    avg_brier_score = stats.get("avg_brier_score", 0.0)

    lines = [
        "📈 Prediction Stats",
        f"Total predictions: {total}",
        f"Resolved: {resolved}",
        f"Unresolved: {unresolved}",
        f"Avg Brier Score: {avg_brier_score:.4f}",
    ]

    if category_stats:
        lines.append("")
        lines.append("By Category:")
        for cat in category_stats:
            category = cat.get("category", "Unknown")
            count = cat.get("count", 0)
            avg_brier = cat.get("avg_brier", 0.0)
            lines.append(f"  {category}: {count} predictions, Brier={avg_brier:.4f}")

    return "\n".join(lines)


def format_daily_summary(stats: dict, signals: list, new_predictions: int) -> str:
    """Format daily summary with new predictions count, active signals, and brier score.

    Args:
        stats: dict with keys: total, resolved, unresolved, avg_brier_score
        signals: list of active signal dicts
        new_predictions: number of new predictions made today

    Returns:
        Formatted string report
    """
    active_signals = len(signals)
    avg_brier_score = stats.get("avg_brier_score", 0.0)
    total = stats.get("total", 0)

    lines = [
        "📅 Daily Summary",
        f"New Predictions: {new_predictions}",
        f"Active Signals: {active_signals}",
        f"Total Predictions: {total}",
        f"Cumulative Brier Score: {avg_brier_score:.4f}",
    ]

    return "\n".join(lines)
