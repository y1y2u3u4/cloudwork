"""Tests for models.py Database class."""
import os
import tempfile
import unittest

# Ensure we can import from parent directory
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Database


class TestDatabase(unittest.TestCase):

    def setUp(self):
        """Create a temp DB file for each test."""
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        self.db = Database(self.tmp.name)

    def tearDown(self):
        """Close DB and remove temp file."""
        self.db.close()
        os.unlink(self.tmp.name)

    # ------------------------------------------------------------------
    # save_market / get_market
    # ------------------------------------------------------------------

    def test_save_and_get_market(self):
        self.db.save_market(
            market_id="mkt-001",
            question="Will BTC reach 100k?",
            description="Bitcoin price prediction",
            category="crypto",
            end_date="2026-12-31",
            token_id_yes="tok-yes-001",
            token_id_no="tok-no-001",
            liquidity=50000.0,
        )
        market = self.db.get_market("mkt-001")
        self.assertIsNotNone(market)
        self.assertEqual(market["id"], "mkt-001")
        self.assertEqual(market["question"], "Will BTC reach 100k?")
        self.assertEqual(market["description"], "Bitcoin price prediction")
        self.assertEqual(market["category"], "crypto")
        self.assertEqual(market["end_date"], "2026-12-31")
        self.assertEqual(market["token_id_yes"], "tok-yes-001")
        self.assertEqual(market["token_id_no"], "tok-no-001")
        self.assertAlmostEqual(market["liquidity"], 50000.0)

    def test_get_market_not_found(self):
        result = self.db.get_market("nonexistent-id")
        self.assertIsNone(result)

    def test_save_market_replace(self):
        """INSERT OR REPLACE should update existing record."""
        self.db.save_market(
            market_id="mkt-002",
            question="Old question",
            description=None,
            category="politics",
            end_date=None,
            token_id_yes=None,
            token_id_no=None,
            liquidity=1000.0,
        )
        self.db.save_market(
            market_id="mkt-002",
            question="Updated question",
            description="Updated desc",
            category="politics",
            end_date=None,
            token_id_yes=None,
            token_id_no=None,
            liquidity=2000.0,
        )
        market = self.db.get_market("mkt-002")
        self.assertEqual(market["question"], "Updated question")
        self.assertAlmostEqual(market["liquidity"], 2000.0)

    # ------------------------------------------------------------------
    # save_prediction / get_prediction
    # ------------------------------------------------------------------

    def _create_market(self, market_id="mkt-001"):
        self.db.save_market(
            market_id=market_id,
            question="Test question",
            description=None,
            category="crypto",
            end_date="2026-12-31",
            token_id_yes=None,
            token_id_no=None,
            liquidity=10000.0,
        )

    def test_save_and_get_prediction(self):
        self._create_market()
        pred_id = self.db.save_prediction(
            market_id="mkt-001",
            ai_probability=0.75,
            ai_confidence=0.85,
            market_price=0.60,
            model_used="claude-sonnet-4",
            reasoning="Strong technical analysis",
            dimensions_json='{"technical": 0.8}',
        )
        self.assertIsInstance(pred_id, int)
        self.assertGreater(pred_id, 0)

        pred = self.db.get_prediction(pred_id)
        self.assertIsNotNone(pred)
        self.assertEqual(pred["market_id"], "mkt-001")
        self.assertAlmostEqual(pred["ai_probability"], 0.75)
        self.assertAlmostEqual(pred["ai_confidence"], 0.85)
        self.assertAlmostEqual(pred["market_price"], 0.60)
        self.assertEqual(pred["model_used"], "claude-sonnet-4")
        self.assertEqual(pred["reasoning"], "Strong technical analysis")
        self.assertEqual(pred["dimensions_json"], '{"technical": 0.8}')
        self.assertIsNone(pred["outcome"])
        self.assertIsNone(pred["brier_score"])

    def test_get_prediction_not_found(self):
        result = self.db.get_prediction(9999)
        self.assertIsNone(result)

    def test_save_prediction_returns_incrementing_ids(self):
        self._create_market()
        id1 = self.db.save_prediction(
            market_id="mkt-001",
            ai_probability=0.5,
            ai_confidence=0.7,
            market_price=0.5,
            model_used=None,
            reasoning=None,
            dimensions_json=None,
        )
        id2 = self.db.save_prediction(
            market_id="mkt-001",
            ai_probability=0.6,
            ai_confidence=0.8,
            market_price=0.55,
            model_used=None,
            reasoning=None,
            dimensions_json=None,
        )
        self.assertGreater(id2, id1)

    # ------------------------------------------------------------------
    # get_unresolved_predictions
    # ------------------------------------------------------------------

    def test_get_unresolved_predictions(self):
        self._create_market()
        id1 = self.db.save_prediction(
            market_id="mkt-001",
            ai_probability=0.7,
            ai_confidence=0.8,
            market_price=0.6,
            model_used=None,
            reasoning=None,
            dimensions_json=None,
        )
        id2 = self.db.save_prediction(
            market_id="mkt-001",
            ai_probability=0.4,
            ai_confidence=0.6,
            market_price=0.45,
            model_used=None,
            reasoning=None,
            dimensions_json=None,
        )
        # Resolve id1
        self.db.resolve_prediction(id1, outcome=1.0)

        unresolved = self.db.get_unresolved_predictions()
        ids = [p["id"] for p in unresolved]
        self.assertNotIn(id1, ids)
        self.assertIn(id2, ids)

    def test_get_unresolved_predictions_empty(self):
        result = self.db.get_unresolved_predictions()
        self.assertEqual(result, [])

    # ------------------------------------------------------------------
    # resolve_prediction / brier_score
    # ------------------------------------------------------------------

    def test_resolve_prediction_correct_brier_score(self):
        self._create_market()
        pred_id = self.db.save_prediction(
            market_id="mkt-001",
            ai_probability=0.8,
            ai_confidence=0.9,
            market_price=0.7,
            model_used=None,
            reasoning=None,
            dimensions_json=None,
        )
        self.db.resolve_prediction(pred_id, outcome=1.0)

        pred = self.db.get_prediction(pred_id)
        self.assertAlmostEqual(pred["outcome"], 1.0)
        # brier = (0.8 - 1.0)^2 = 0.04
        self.assertAlmostEqual(pred["brier_score"], 0.04, places=6)

    def test_resolve_prediction_outcome_zero(self):
        self._create_market()
        pred_id = self.db.save_prediction(
            market_id="mkt-001",
            ai_probability=0.3,
            ai_confidence=0.75,
            market_price=0.35,
            model_used=None,
            reasoning=None,
            dimensions_json=None,
        )
        self.db.resolve_prediction(pred_id, outcome=0.0)

        pred = self.db.get_prediction(pred_id)
        self.assertAlmostEqual(pred["outcome"], 0.0)
        # brier = (0.3 - 0.0)^2 = 0.09
        self.assertAlmostEqual(pred["brier_score"], 0.09, places=6)

    def test_resolve_prediction_perfect(self):
        self._create_market()
        pred_id = self.db.save_prediction(
            market_id="mkt-001",
            ai_probability=1.0,
            ai_confidence=0.95,
            market_price=0.9,
            model_used=None,
            reasoning=None,
            dimensions_json=None,
        )
        self.db.resolve_prediction(pred_id, outcome=1.0)

        pred = self.db.get_prediction(pred_id)
        # brier = (1.0 - 1.0)^2 = 0.0
        self.assertAlmostEqual(pred["brier_score"], 0.0, places=6)

    # ------------------------------------------------------------------
    # get_prediction_stats
    # ------------------------------------------------------------------

    def test_get_prediction_stats_empty(self):
        stats = self.db.get_prediction_stats()
        self.assertEqual(stats["total"], 0)
        self.assertEqual(stats["resolved"], 0)
        self.assertEqual(stats["unresolved"], 0)
        self.assertIsNone(stats["avg_brier_score"])

    def test_get_prediction_stats(self):
        self._create_market()
        id1 = self.db.save_prediction(
            market_id="mkt-001",
            ai_probability=0.8,
            ai_confidence=0.9,
            market_price=0.7,
            model_used=None,
            reasoning=None,
            dimensions_json=None,
        )
        id2 = self.db.save_prediction(
            market_id="mkt-001",
            ai_probability=0.6,
            ai_confidence=0.7,
            market_price=0.55,
            model_used=None,
            reasoning=None,
            dimensions_json=None,
        )
        id3 = self.db.save_prediction(
            market_id="mkt-001",
            ai_probability=0.4,
            ai_confidence=0.6,
            market_price=0.45,
            model_used=None,
            reasoning=None,
            dimensions_json=None,
        )

        # Resolve 2 of 3
        self.db.resolve_prediction(id1, outcome=1.0)  # brier = (0.8-1)^2 = 0.04
        self.db.resolve_prediction(id2, outcome=0.0)  # brier = (0.6-0)^2 = 0.36

        stats = self.db.get_prediction_stats()
        self.assertEqual(stats["total"], 3)
        self.assertEqual(stats["resolved"], 2)
        self.assertEqual(stats["unresolved"], 1)
        # avg_brier = (0.04 + 0.36) / 2 = 0.20
        self.assertAlmostEqual(stats["avg_brier_score"], 0.20, places=6)

    # ------------------------------------------------------------------
    # get_predictions_by_category
    # ------------------------------------------------------------------

    def test_get_predictions_by_category(self):
        self.db.save_market(
            market_id="mkt-crypto",
            question="BTC question",
            description=None,
            category="crypto",
            end_date=None,
            token_id_yes=None,
            token_id_no=None,
            liquidity=10000.0,
        )
        self.db.save_market(
            market_id="mkt-politics",
            question="Election question",
            description=None,
            category="politics",
            end_date=None,
            token_id_yes=None,
            token_id_no=None,
            liquidity=5000.0,
        )

        pred_id = self.db.save_prediction(
            market_id="mkt-crypto",
            ai_probability=0.7,
            ai_confidence=0.8,
            market_price=0.65,
            model_used=None,
            reasoning=None,
            dimensions_json=None,
        )
        self.db.save_prediction(
            market_id="mkt-politics",
            ai_probability=0.4,
            ai_confidence=0.6,
            market_price=0.45,
            model_used=None,
            reasoning=None,
            dimensions_json=None,
        )
        self.db.resolve_prediction(pred_id, outcome=1.0)  # brier = (0.7-1)^2 = 0.09

        rows = self.db.get_predictions_by_category()
        self.assertIsInstance(rows, list)
        categories = {r["category"]: r for r in rows}
        self.assertIn("crypto", categories)
        self.assertIn("politics", categories)
        self.assertEqual(categories["crypto"]["count"], 1)
        self.assertAlmostEqual(categories["crypto"]["avg_brier"], 0.09, places=6)
        self.assertEqual(categories["politics"]["count"], 1)
        # politics has no resolved predictions, avg_brier should be None
        self.assertIsNone(categories["politics"]["avg_brier"])

    # ------------------------------------------------------------------
    # get_open_positions_count
    # ------------------------------------------------------------------

    def test_get_open_positions_count_empty(self):
        count = self.db.get_open_positions_count()
        self.assertEqual(count, 0)

    def test_get_open_positions_count(self):
        self._create_market()
        conn = self.db._conn
        conn.execute(
            """INSERT INTO positions (market_id, direction, entry_price, size_usd, entry_timestamp, status)
               VALUES (?, ?, ?, ?, ?, ?)""",
            ("mkt-001", "YES", 0.65, 50.0, "2026-04-01T10:00:00", "open"),
        )
        conn.execute(
            """INSERT INTO positions (market_id, direction, entry_price, size_usd, entry_timestamp, status)
               VALUES (?, ?, ?, ?, ?, ?)""",
            ("mkt-001", "NO", 0.35, 30.0, "2026-04-01T11:00:00", "closed"),
        )
        conn.commit()

        count = self.db.get_open_positions_count()
        self.assertEqual(count, 1)

    # ------------------------------------------------------------------
    # close
    # ------------------------------------------------------------------

    def test_close(self):
        """After close(), operations should raise an error."""
        self.db.close()
        with self.assertRaises(Exception):
            self.db.get_market("any-id")
        # Re-open to avoid tearDown error
        self.db = Database(self.tmp.name)


if __name__ == "__main__":
    unittest.main()
