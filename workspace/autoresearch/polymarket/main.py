"""Polymarket AI Prediction Trading — CLI Orchestrator.

Usage:
    python main.py scan               # Scan and display candidate markets (no API key needed)
    python main.py predict            # Full pipeline: scan → predict → detect edges → log to DB
    python main.py predict-one <id>   # Predict a single market by its Polymarket market ID
    python main.py deep-analyze <id>  # Map-Reduce deep analysis on a single market
    python main.py stats              # Show prediction statistics from the local DB
    python main.py resolve            # Check unresolved predictions against settled markets
"""

import sys
import json
import os
import requests
from datetime import datetime, timezone

from config import DB_PATH, GAMMA_API_URL
from models import Database
from scanner import fetch_active_markets, parse_market
from predictor import predict_market
from map_reduce_predictor import predict_market_deep
from edge import generate_signal
from monitor import format_signal_report, format_stats_report


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def ensure_db() -> Database:
    """Create data directory if needed and return an open Database instance."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return Database(DB_PATH)


def _save_market_from_dict(db: Database, market: dict) -> None:
    """Persist a parsed market dict to the database."""
    db.save_market(
        market_id=market["market_id"],
        question=market["question"],
        description=market.get("description"),
        category=market.get("category"),
        end_date=market.get("end_date"),
        token_id_yes=market.get("token_id_yes"),
        token_id_no=market.get("token_id_no"),
        liquidity=market.get("liquidity"),
    )


def _save_prediction_from_result(
    db: Database, market: dict, result: dict
) -> int:
    """Persist a prediction result dict to the database and return its row id."""
    return db.save_prediction(
        market_id=market["market_id"],
        ai_probability=result["probability"],
        ai_confidence=result["confidence"],
        market_price=market["yes_price"],
        model_used=None,
        reasoning=result.get("reasoning"),
        dimensions_json=json.dumps(result.get("dimensions", {})),
    )


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_scan() -> None:
    """Fetch and display candidate markets without making any predictions."""
    print("Fetching active markets from Polymarket…")
    markets = fetch_active_markets()

    if not markets:
        print("No candidate markets found matching current filters.")
        return

    print(f"\nFound {len(markets)} candidate market(s):\n")
    print(
        f"{'#':<4} {'Category':<18} {'Question':<72} {'Price':>6} "
        f"{'Liquidity':>12} {'Vol24h':>10} {'ID':<36} {'End Date'}"
    )
    print("-" * 180)

    for i, market in enumerate(markets, start=1):
        question = market["question"][:70]
        category = (market.get("category") or "")[:16]
        price = market["yes_price"]
        liquidity = market.get("liquidity") or 0
        vol = market.get("volume_24h") or 0
        market_id = market["market_id"]
        end_date = market.get("end_date", "")[:10]

        print(
            f"{i:<4} {category:<18} {question:<72} {price:>6.2f} "
            f"{liquidity:>12,.0f} {vol:>10,.0f} {market_id:<36} {end_date}"
        )


def cmd_predict() -> None:
    """Full pipeline: scan → predict → edge detection → save to DB."""
    db = ensure_db()

    print("Scanning markets…")
    markets = fetch_active_markets()

    if not markets:
        print("No candidate markets found.")
        db.close()
        return

    print(f"Found {len(markets)} candidate market(s). Running predictions…\n")

    signals = []
    open_positions = db.get_open_positions_count()

    for i, market in enumerate(markets, start=1):
        question_short = market["question"][:60]
        print(f"[{i}/{len(markets)}] {question_short}…", flush=True)

        # Persist market
        _save_market_from_dict(db, market)

        # Predict
        result = predict_market(market)

        # Persist prediction
        _save_prediction_from_result(db, market, result)

        ai_prob = result["probability"]
        market_price = market["yes_price"]
        confidence = result["confidence"]
        edge = ai_prob - market_price

        print(
            f"         AI prob: {ai_prob:.1%}  |  Market: {market_price:.1%}  "
            f"|  Edge: {edge:+.1%}  |  Conf: {confidence:.1%}"
        )

        # Check for signal
        signal = generate_signal(
            market_id=market["market_id"],
            question=market["question"],
            ai_prob=ai_prob,
            ai_confidence=confidence,
            market_price=market_price,
            open_positions=open_positions,
        )
        if signal:
            print(f"         >>> SIGNAL: {signal['direction']}  size=${signal['size_usd']:.0f}")
            signals.append((signal, result.get("reasoning", "")))

    print(f"\n{'='*60}")
    print(f"Processed {len(markets)} market(s). {len(signals)} signal(s) found.\n")

    for signal, reasoning in signals:
        print("🎯 SIGNAL")
        print(format_signal_report(signal, reasoning=reasoning))
        print()

    db.close()


def cmd_predict_one(market_id: str) -> None:
    """Fetch a single market by ID, predict, and display details."""
    db = ensure_db()

    print(f"Fetching market {market_id}…")
    url = f"{GAMMA_API_URL}/markets/{market_id}"
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        raw = response.json()
    except requests.RequestException as exc:
        print(f"Error fetching market: {exc}")
        db.close()
        return

    try:
        market = parse_market(raw)
    except (KeyError, ValueError, json.JSONDecodeError) as exc:
        print(f"Error parsing market data: {exc}")
        db.close()
        return

    print(f"Question : {market['question']}")
    print(f"Category : {market.get('category', 'N/A')}")
    print(f"Price    : {market['yes_price']:.1%}")
    print(f"Liquidity: {market.get('liquidity', 0):,.0f} USDC")
    print(f"End Date : {market.get('end_date', 'N/A')}")
    print("\nRunning prediction…")

    _save_market_from_dict(db, market)
    result = predict_market(market)
    pred_id = _save_prediction_from_result(db, market, result)

    ai_prob = result["probability"]
    confidence = result["confidence"]
    market_price = market["yes_price"]
    edge = ai_prob - market_price

    print(f"\nPrediction (id={pred_id}):")
    print(f"  AI Probability : {ai_prob:.1%}")
    print(f"  AI Confidence  : {confidence:.1%}")
    print(f"  Market Price   : {market_price:.1%}")
    print(f"  Edge           : {edge:+.1%}")
    print(f"\nReasoning:\n{result.get('reasoning', 'N/A')}")

    if result.get("dimensions"):
        print("\nDimensions:")
        for k, v in result["dimensions"].items():
            print(f"  {k}: {v}")

    signal = generate_signal(
        market_id=market["market_id"],
        question=market["question"],
        ai_prob=ai_prob,
        ai_confidence=confidence,
        market_price=market_price,
    )
    if signal:
        print("\n🎯 SIGNAL DETECTED")
        print(format_signal_report(signal, reasoning=result.get("reasoning", "")))
    else:
        print("\nNo signal generated (edge or confidence below threshold).")

    db.close()


def cmd_deep_analyze(market_id: str) -> None:
    """Fetch a single market by ID and run Map-Reduce deep analysis."""
    db = ensure_db()

    print(f"Fetching market {market_id}…")
    url = f"{GAMMA_API_URL}/markets/{market_id}"
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        raw = response.json()
    except requests.RequestException as exc:
        print(f"Error fetching market: {exc}")
        db.close()
        return

    try:
        market = parse_market(raw)
    except (KeyError, ValueError, json.JSONDecodeError) as exc:
        print(f"Error parsing market data: {exc}")
        db.close()
        return

    print(f"Question : {market['question']}")
    print(f"Category : {market.get('category', 'N/A')}")
    print(f"Price    : {market['yes_price']:.1%}")
    print(f"Liquidity: {market.get('liquidity', 0):,.0f} USDC")
    print(f"End Date : {market.get('end_date', 'N/A')}")
    print("\nRunning Map-Reduce deep analysis (4 parallel sub-analyses)…\n")

    _save_market_from_dict(db, market)
    result = predict_market_deep(market)

    # Print each sub-analysis
    dimensions = result.get("dimensions", {})
    sub_analysis_labels = {
        "resolution_rules": "=== Analysis 1: Resolution Rules ===",
        "evidence": "=== Analysis 2: Evidence Gathering ===",
        "counter_arguments": "=== Analysis 3: Counter-Arguments (Devil's Advocate) ===",
        "catalysts": "=== Analysis 4: Domain Catalysts ===",
    }
    for key, label in sub_analysis_labels.items():
        if key in dimensions:
            print(label)
            value = dimensions[key]
            if isinstance(value, dict):
                for k, v in value.items():
                    print(f"  {k}: {v}")
            else:
                print(f"  {value}")
            print()

    ai_prob = result["probability"]
    confidence = result["confidence"]
    market_price = market["yes_price"]
    edge = ai_prob - market_price

    print("=== Final Synthesis ===")
    print(f"  AI Probability : {ai_prob:.1%}")
    print(f"  AI Confidence  : {confidence:.1%}")
    print(f"  Market Price   : {market_price:.1%}")
    print(f"  Edge           : {edge:+.1%}")
    print(f"\nReasoning:\n{result.get('reasoning', 'N/A')}")

    pred_id = _save_prediction_from_result(db, market, result)
    print(f"\nSaved prediction (id={pred_id}) to DB.")

    signal = generate_signal(
        market_id=market["market_id"],
        question=market["question"],
        ai_prob=ai_prob,
        ai_confidence=confidence,
        market_price=market_price,
    )
    if signal:
        print("\n>>> SIGNAL DETECTED")
        print(format_signal_report(signal, reasoning=result.get("reasoning", "")))
    else:
        print("\nNo signal generated (edge or confidence below threshold).")

    db.close()


def cmd_stats() -> None:
    """Display prediction statistics from the local database."""
    db = ensure_db()
    stats = db.get_prediction_stats()
    # avg_brier_score is NULL when no predictions are resolved; default to 0.0
    if stats.get("avg_brier_score") is None:
        stats["avg_brier_score"] = 0.0
    category_stats = db.get_predictions_by_category()
    print(format_stats_report(stats, category_stats=category_stats or None))
    db.close()


def cmd_resolve() -> None:
    """Resolve unresolved predictions against settled Polymarket markets."""
    db = ensure_db()
    unresolved = db.get_unresolved_predictions()

    if not unresolved:
        print("No unresolved predictions found.")
        db.close()
        return

    print(f"Found {len(unresolved)} unresolved prediction(s). Checking…\n")

    resolved_count = 0
    for pred in unresolved:
        market_id = pred["market_id"]
        pred_id = pred["id"]
        ai_prob = pred["ai_probability"]

        url = f"{GAMMA_API_URL}/markets/{market_id}"
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            raw = response.json()
        except requests.RequestException as exc:
            print(f"  [SKIP] Market {market_id}: fetch error — {exc}")
            continue

        # Only resolve closed markets
        if not raw.get("closed", False):
            print(f"  [OPEN] Market {market_id}: still open, skipping.")
            continue

        # Determine outcome from outcomePrices
        try:
            prices = json.loads(raw["outcomePrices"])
            yes_price_final = float(prices[0])
        except (KeyError, ValueError, json.JSONDecodeError):
            print(f"  [SKIP] Market {market_id}: could not parse outcomePrices.")
            continue

        if yes_price_final > 0.95:
            outcome = 1.0
            outcome_label = "YES"
        elif yes_price_final < 0.05:
            outcome = 0.0
            outcome_label = "NO"
        else:
            print(
                f"  [SKIP] Market {market_id}: ambiguous outcome price {yes_price_final:.2f}."
            )
            continue

        db.resolve_prediction(pred_id, outcome)
        brier = (ai_prob - outcome) ** 2
        question_short = raw.get("question", market_id)[:60]
        print(
            f"  [RESOLVED] Pred#{pred_id} | {question_short} | "
            f"Outcome={outcome_label} | AI={ai_prob:.1%} | Brier={brier:.4f}"
        )
        resolved_count += 1

    print(f"\nResolved {resolved_count}/{len(unresolved)} prediction(s).")
    db.close()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    args = sys.argv[1:]

    if not args:
        print(__doc__)
        sys.exit(0)

    cmd = args[0]

    if cmd == "scan":
        cmd_scan()
    elif cmd == "predict":
        cmd_predict()
    elif cmd == "predict-one":
        if len(args) < 2:
            print("Usage: python main.py predict-one <market_id>")
            sys.exit(1)
        cmd_predict_one(args[1])
    elif cmd == "deep-analyze":
        if len(args) < 2:
            print("Usage: python main.py deep-analyze <market_id>")
            sys.exit(1)
        cmd_deep_analyze(args[1])
    elif cmd == "stats":
        cmd_stats()
    elif cmd == "resolve":
        cmd_resolve()
    else:
        print(f"Unknown command: {cmd!r}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
