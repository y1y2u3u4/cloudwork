# Polymarket AI Prediction Trading System

## Project Overview

Uses LLMs to predict outcomes on Polymarket prediction markets, detects mispricings vs market consensus, and generates trade signals. Currently in **Phase 1: predict-only validation** — no real money is being traded yet.

## Architecture

```
Scanner (Gamma API) → Predictor (LLM + Web Search) → Edge Detector (1/4 Kelly) → Monitor (Brier Score)
```

Data flow: `scanner.fetch_active_markets()` → 5-filter pipeline → `predictor.predict_market()` → DuckDuckGo search + `claude-sonnet-4-20250514` → `edge.generate_signal()` → `models.Database` persist → `monitor.format_*` report.

## File Structure

```
polymarket/
├── config.py          # API URLs, trading params (MIN_EDGE=0.10, MIN_CONFIDENCE=0.70), env vars
├── models.py          # SQLite Database class — markets / predictions / positions CRUD
├── scanner.py         # Gamma API fetch + 5-filter pipeline (liquidity, price range, TTR, active, open)
├── predictor.py       # DuckDuckGo HTML scrape → Anthropic API → JSON parse
├── prompts.py         # 5-dimension structured prediction prompt (base_rate/catalysts/fragility/recency/bias)
├── edge.py            # Edge = ai_prob - market_price; 1/4 Kelly sizing capped at $20-50
├── monitor.py         # Brier Score tracking; format_signal_report / format_stats_report
├── main.py            # CLI entry point — scan / predict / predict-one / stats / resolve
├── data/polymarket.db # SQLite database (git-ignored)
├── tests/             # 52 tests across models, scanner, edge, monitor
└── docs/              # Research notes and architecture docs
```

## Commands

```bash
# Run from polymarket/ directory
python main.py scan              # Scan markets (no API key needed)
python main.py predict           # Full pipeline: scan → predict → edge → log to DB
python main.py predict-one <id>  # Predict single market by Polymarket market ID
python main.py stats             # Show prediction statistics and Brier scores
python main.py resolve           # Settle resolved markets and compute Brier scores

# Tests
python -m pytest tests/ -v       # 52 tests, all should pass
```

## Environment Variables

| Variable | Required | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes (for predict) | Anthropic API — model `claude-sonnet-4-20250514` |
| `POLY_MODE` | No | `predict` (default) / `semi` / `auto` |

No other external dependencies — Polymarket Gamma API is public (no auth), DuckDuckGo search uses HTML scraping (no API key).

## Key Configuration (`config.py`)

```python
MIN_LIQUIDITY = 5000          # USDC — filter out thin markets
PRICE_RANGE_LOW = 0.15        # Skip extreme-priced markets (poor risk/reward)
PRICE_RANGE_HIGH = 0.85
MIN_HOURS_TO_RESOLUTION = 24  # Need time to act on signals
MIN_EDGE = 0.10               # 10% edge required to generate signal
MIN_CONFIDENCE = 0.70         # 70% confidence required
KELLY_FRACTION = 0.25         # Quarter-Kelly position sizing
BANKROLL = 1000.0             # USDC
MIN_TRADE_SIZE = 20.0         # USD per trade
MAX_TRADE_SIZE = 50.0         # USD per trade cap
MAX_POSITIONS = 20            # Concurrent open positions limit
PREDICTION_MODEL = "claude-sonnet-4-20250514"
```

## Prediction Pipeline

1. **Scanner**: fetches top-100 markets by 24h volume, applies 5 filters (open, active, liquidity ≥ $5k, price 15-85%, TTR ≥ 24h)
2. **Web Search**: DuckDuckGo HTML scrape — free, no API key, returns up to 5 result snippets
3. **LLM Prediction**: structured prompt returns JSON with `probability`, `confidence`, 5 dimension scores, `reasoning`, `key_catalysts`
4. **Edge Detection**: `edge = ai_prob - market_price`; YES if edge > 0, NO if edge < 0
5. **Kelly Sizing**: `kelly = |edge| / (1 - price)` for YES or `|edge| / price` for NO; then `× 0.25 × bankroll`, capped at $50
6. **Persistence**: markets, predictions, and (future) positions stored in SQLite

## Database Schema

Three tables: `markets` (primary), `predictions` (FK to markets, stores Brier score on resolution), `positions` (FK to both, for Phase 2 trading).

Resolution: `cmd_resolve` polls Gamma API for closed markets, sets `outcome=1.0` if YES price >95%, `outcome=0.0` if <5%, skips ambiguous.

## Upcoming: Map-Reduce Predictor

Current single-pass LLM call is being replaced with parallel sub-agents:
- **Map**: 4 parallel sub-agents — (1) resolution rules analysis, (2) factual evidence, (3) counter-arguments, (4) domain-specific catalysts
- **Reduce**: synthesis into calibrated probability
- **Domain rubrics**: different dimensions for politics / sports / crypto / geopolitics

## Critical Lessons Learned

1. **Resolution rules determine everything** — always read exact settlement criteria before predicting; "wick counts" vs "close price" for BTC markets changes estimates dramatically
2. **Single-pass LLM misses counter-arguments** — Map-Reduce architecture is the fix
3. **Markets at extremes (<15% or >85%) have poor risk/reward** — already filtered out by scanner
4. **Liquidity < $20k makes $50 trades impractical** — conservative threshold set at $5k for discovery, consider raising for live trading
5. **Brier Score is the ground truth** — lower is better (perfect = 0.0, random = 0.25); track by category to find where the model has edge

## Phase Roadmap

| Phase | Description | Status |
|---|---|---|
| Phase 1 | Predict-only: validate calibration via Brier score | Current |
| Phase 2 | Semi-auto: human confirms signals before CLOB order | Planned |
| Phase 3 | Full-auto: CLOB API integration with wallet | Future |

## API Endpoints

- **Gamma API** (market discovery): `https://gamma-api.polymarket.com` — public, no auth
- **CLOB API** (order execution): `https://clob.polymarket.com` — requires wallet (Phase 2+)
- **Data API** (analytics): `https://data-api.polymarket.com`
