"""Database models for Polymarket AI prediction trading system."""
import sqlite3
from datetime import datetime, timezone
from typing import Dict, List, Optional

from config import DB_PATH

_SCHEMA = """
CREATE TABLE IF NOT EXISTS markets (
    id TEXT PRIMARY KEY,
    question TEXT NOT NULL,
    description TEXT,
    category TEXT,
    end_date TEXT,
    token_id_yes TEXT,
    token_id_no TEXT,
    liquidity REAL,
    last_scanned TEXT
);

CREATE TABLE IF NOT EXISTS predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    market_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    ai_probability REAL NOT NULL,
    ai_confidence REAL NOT NULL,
    market_price REAL NOT NULL,
    model_used TEXT,
    reasoning TEXT,
    dimensions_json TEXT,
    outcome REAL,
    brier_score REAL,
    FOREIGN KEY (market_id) REFERENCES markets(id)
);

CREATE TABLE IF NOT EXISTS positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    market_id TEXT NOT NULL,
    prediction_id INTEGER,
    direction TEXT NOT NULL,
    entry_price REAL NOT NULL,
    size_usd REAL NOT NULL,
    shares REAL,
    entry_timestamp TEXT NOT NULL,
    status TEXT DEFAULT 'open',
    exit_price REAL,
    exit_timestamp TEXT,
    pnl REAL,
    FOREIGN KEY (market_id) REFERENCES markets(id),
    FOREIGN KEY (prediction_id) REFERENCES predictions(id)
);
"""


class Database:
    """SQLite database wrapper for Polymarket prediction trading."""

    def __init__(self, db_path: str = DB_PATH):
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    # ------------------------------------------------------------------
    # Markets
    # ------------------------------------------------------------------

    def save_market(
        self,
        market_id: str,
        question: str,
        description: Optional[str],
        category: Optional[str],
        end_date: Optional[str],
        token_id_yes: Optional[str],
        token_id_no: Optional[str],
        liquidity: Optional[float],
    ) -> None:
        """INSERT OR REPLACE a market record."""
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            """INSERT OR REPLACE INTO markets
               (id, question, description, category, end_date,
                token_id_yes, token_id_no, liquidity, last_scanned)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                market_id,
                question,
                description,
                category,
                end_date,
                token_id_yes,
                token_id_no,
                liquidity,
                now,
            ),
        )
        self._conn.commit()

    def get_market(self, market_id: str) -> Optional[Dict]:
        """Return market dict or None if not found."""
        row = self._conn.execute(
            "SELECT * FROM markets WHERE id = ?", (market_id,)
        ).fetchone()
        return dict(row) if row else None

    # ------------------------------------------------------------------
    # Predictions
    # ------------------------------------------------------------------

    def save_prediction(
        self,
        market_id: str,
        ai_probability: float,
        ai_confidence: float,
        market_price: float,
        model_used: Optional[str],
        reasoning: Optional[str],
        dimensions_json: Optional[str],
    ) -> int:
        """Insert a new prediction and return its integer id."""
        now = datetime.now(timezone.utc).isoformat()
        cursor = self._conn.execute(
            """INSERT INTO predictions
               (market_id, timestamp, ai_probability, ai_confidence, market_price,
                model_used, reasoning, dimensions_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                market_id,
                now,
                ai_probability,
                ai_confidence,
                market_price,
                model_used,
                reasoning,
                dimensions_json,
            ),
        )
        self._conn.commit()
        return cursor.lastrowid

    def get_prediction(self, pred_id: int) -> Optional[Dict]:
        """Return prediction dict or None if not found."""
        row = self._conn.execute(
            "SELECT * FROM predictions WHERE id = ?", (pred_id,)
        ).fetchone()
        return dict(row) if row else None

    def get_unresolved_predictions(self) -> List[Dict]:
        """Return all predictions where outcome IS NULL."""
        rows = self._conn.execute(
            "SELECT * FROM predictions WHERE outcome IS NULL"
        ).fetchall()
        return [dict(r) for r in rows]

    def resolve_prediction(self, pred_id: int, outcome: float) -> None:
        """Set outcome and compute brier_score = (ai_probability - outcome)^2."""
        row = self._conn.execute(
            "SELECT ai_probability FROM predictions WHERE id = ?", (pred_id,)
        ).fetchone()
        if row is None:
            raise ValueError(f"Prediction {pred_id} not found")
        brier_score = (row["ai_probability"] - outcome) ** 2
        self._conn.execute(
            "UPDATE predictions SET outcome = ?, brier_score = ? WHERE id = ?",
            (outcome, brier_score, pred_id),
        )
        self._conn.commit()

    def get_prediction_stats(self) -> Dict:
        """Return dict with total, resolved, unresolved, avg_brier_score."""
        row = self._conn.execute(
            """SELECT
                   COUNT(*) AS total,
                   SUM(CASE WHEN outcome IS NOT NULL THEN 1 ELSE 0 END) AS resolved,
                   SUM(CASE WHEN outcome IS NULL THEN 1 ELSE 0 END) AS unresolved,
                   AVG(brier_score) AS avg_brier_score
               FROM predictions"""
        ).fetchone()
        return {
            "total": row["total"] or 0,
            "resolved": row["resolved"] or 0,
            "unresolved": row["unresolved"] or 0,
            "avg_brier_score": row["avg_brier_score"],
        }

    def get_predictions_by_category(self) -> List[Dict]:
        """Return list of dicts with category, count, avg_brier joined with markets."""
        rows = self._conn.execute(
            """SELECT
                   m.category,
                   COUNT(p.id) AS count,
                   AVG(p.brier_score) AS avg_brier
               FROM predictions p
               JOIN markets m ON p.market_id = m.id
               GROUP BY m.category"""
        ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Positions
    # ------------------------------------------------------------------

    def get_open_positions_count(self) -> int:
        """Return count of positions with status='open'."""
        row = self._conn.execute(
            "SELECT COUNT(*) AS cnt FROM positions WHERE status = 'open'"
        ).fetchone()
        return row["cnt"]

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()
