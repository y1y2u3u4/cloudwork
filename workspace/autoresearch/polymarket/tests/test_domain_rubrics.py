"""Tests for domain_rubrics.py"""
import pytest
from domain_rubrics import (
    detect_domain,
    get_rubric,
    format_rubric_for_prompt,
    calculate_weighted_score,
    RUBRICS,
    DEFAULT_RUBRIC,
    DOMAIN_KEYWORDS,
)


class TestDetectDomain:
    def test_geopolitics_keywords(self):
        assert detect_domain("Will Russia invade Ukraine again?") == "geopolitics"
        assert detect_domain("Will Iran launch military strikes?") == "geopolitics"
        assert detect_domain("NATO ceasefire agreement by Q3?") == "geopolitics"

    def test_politics_keywords(self):
        assert detect_domain("Who will win the US presidential election?") == "politics"
        assert detect_domain("Will the senate confirm the nomination?") == "politics"
        assert detect_domain("Will the governor sign the bill?") == "politics"

    def test_crypto_keywords(self):
        assert detect_domain("Will Bitcoin reach $100k?") == "crypto"
        assert detect_domain("Will ETH hit $5000?") == "crypto"
        assert detect_domain("Will the BTC ETH crypto defi blockchain NFT token reach?") == "crypto"

    def test_sports_keywords(self):
        assert detect_domain("Will the NBA finals go to game 7?") == "sports"
        assert detect_domain("Who wins the FIFA World Cup?") == "sports"
        assert detect_domain("Will Team A win the championship?") == "sports"

    def test_economics_keywords(self):
        assert detect_domain("Will the Fed raise interest rate?") == "economics"
        assert detect_domain("Will GDP growth exceed 2%?") == "economics"
        assert detect_domain("Will unemployment rise due to tariff and trade war?") == "economics"

    def test_tech_keywords(self):
        assert detect_domain("Will OpenAI launch GPT-5?") == "tech"
        assert detect_domain("Will the company IPO this year?") == "tech"
        assert detect_domain("Will the acquisition close by Q2?") == "tech"

    def test_fallback_to_general(self):
        assert detect_domain("Will the new bridge be finished by December?") == "general"
        assert detect_domain("Will the population exceed 10 billion by 2050?") == "general"
        assert detect_domain("") == "general"

    def test_category_included_in_detection(self):
        result = detect_domain("Will prices rise?", category="crypto markets")
        assert result == "crypto"

    def test_highest_score_wins(self):
        # Multiple crypto keywords should beat single politics keyword
        result = detect_domain("Will Bitcoin ETH BTC crypto token vote?")
        assert result == "crypto"

    def test_case_insensitive(self):
        assert detect_domain("Will BITCOIN reach new highs?") == "crypto"
        assert detect_domain("US ELECTION outcome 2024") == "politics"


class TestGetRubric:
    def test_returns_correct_rubric_for_each_known_domain(self):
        for domain in RUBRICS:
            rubric = get_rubric(domain)
            assert rubric is RUBRICS[domain]

    def test_fallback_to_default_for_general(self):
        rubric = get_rubric("general")
        assert rubric is DEFAULT_RUBRIC

    def test_fallback_to_default_for_unknown_domain(self):
        rubric = get_rubric("unknown_domain_xyz")
        assert rubric is DEFAULT_RUBRIC

    def test_rubric_has_required_keys(self):
        for domain in list(RUBRICS.keys()) + ["general"]:
            rubric = get_rubric(domain)
            assert "name" in rubric
            assert "dimensions" in rubric
            assert isinstance(rubric["dimensions"], list)
            assert len(rubric["dimensions"]) > 0

    def test_each_dimension_has_required_fields(self):
        for domain in list(RUBRICS.keys()) + ["general"]:
            rubric = get_rubric(domain)
            for dim in rubric["dimensions"]:
                assert "id" in dim
                assert "name" in dim
                assert "description" in dim
                assert "weight" in dim
                assert isinstance(dim["weight"], (int, float))
                assert dim["weight"] > 0

    def test_geopolitics_has_decision_maker_intent(self):
        rubric = get_rubric("geopolitics")
        dim_ids = [d["id"] for d in rubric["dimensions"]]
        assert "decision_maker_intent" in dim_ids

    def test_crypto_has_price_distance(self):
        rubric = get_rubric("crypto")
        dim_ids = [d["id"] for d in rubric["dimensions"]]
        assert "price_distance" in dim_ids

    def test_sports_has_injury_availability(self):
        rubric = get_rubric("sports")
        dim_ids = [d["id"] for d in rubric["dimensions"]]
        assert "injury_availability" in dim_ids

    def test_politics_has_polling_data(self):
        rubric = get_rubric("politics")
        dim_ids = [d["id"] for d in rubric["dimensions"]]
        assert "polling_data" in dim_ids


class TestFormatRubricForPrompt:
    def test_returns_non_empty_string(self):
        for domain in list(RUBRICS.keys()) + ["general"]:
            result = format_rubric_for_prompt(domain)
            assert isinstance(result, str)
            assert len(result) > 0

    def test_contains_domain_name(self):
        result = format_rubric_for_prompt("geopolitics")
        assert "Geopolitical Conflict & Diplomacy" in result

    def test_contains_all_dimension_names(self):
        for domain in list(RUBRICS.keys()) + ["general"]:
            rubric = get_rubric(domain)
            result = format_rubric_for_prompt(domain)
            for dim in rubric["dimensions"]:
                assert dim["name"] in result

    def test_contains_weight_info(self):
        result = format_rubric_for_prompt("crypto")
        assert "weight" in result
        assert "2.0x" in result  # price_distance and resolution_mechanics

    def test_contains_score_instruction(self):
        result = format_rubric_for_prompt("politics")
        assert "score 0-5" in result.lower() or "0-5" in result

    def test_dimensions_numbered(self):
        result = format_rubric_for_prompt("sports")
        assert "1." in result
        assert "2." in result

    def test_fallback_domain_works(self):
        result = format_rubric_for_prompt("general")
        assert "General Prediction" in result

    def test_unknown_domain_uses_default(self):
        result = format_rubric_for_prompt("nonexistent")
        assert "General Prediction" in result


class TestCalculateWeightedScore:
    def test_all_max_scores_returns_one(self):
        domain = "sports"
        rubric = get_rubric(domain)
        scores = {dim["id"]: 5 for dim in rubric["dimensions"]}
        result = calculate_weighted_score(scores, domain)
        assert abs(result - 1.0) < 1e-9

    def test_all_zero_scores_returns_zero(self):
        domain = "crypto"
        rubric = get_rubric(domain)
        scores = {dim["id"]: 0 for dim in rubric["dimensions"]}
        result = calculate_weighted_score(scores, domain)
        assert abs(result - 0.0) < 1e-9

    def test_empty_scores_returns_zero(self):
        # Missing keys default to 0, so all-zero
        result = calculate_weighted_score({}, "politics")
        assert result == 0.0

    def test_partial_scores_between_zero_and_one(self):
        domain = "geopolitics"
        rubric = get_rubric(domain)
        # Give half the dimensions a score of 5
        scores = {}
        for i, dim in enumerate(rubric["dimensions"]):
            scores[dim["id"]] = 5 if i % 2 == 0 else 0
        result = calculate_weighted_score(scores, domain)
        assert 0.0 < result < 1.0

    def test_weighted_average_correctness(self):
        # Use a domain with known weights for manual verification
        # crypto: price_distance w=2.0, resolution_mechanics w=2.0, macro_regime w=1.5,
        #         liquidity_structure w=1.0, time_window w=1.5, catalyst_events w=1.0
        domain = "crypto"
        scores = {
            "price_distance": 4,
            "resolution_mechanics": 2,
            "macro_regime": 0,
            "liquidity_structure": 0,
            "time_window": 0,
            "catalyst_events": 0,
        }
        # weighted_sum = 4*2.0 + 2*2.0 = 12.0
        # total_weight = 5*(2.0+2.0+1.5+1.0+1.5+1.0) = 5*9.0 = 45.0
        expected = 12.0 / 45.0
        result = calculate_weighted_score(scores, domain)
        assert abs(result - expected) < 1e-9

    def test_missing_dimension_ids_default_to_zero(self):
        domain = "sports"
        # Only provide one dimension score
        scores = {"team_form": 5}
        result = calculate_weighted_score(scores, domain)
        rubric = get_rubric(domain)
        # Manually compute expected
        total_weight = sum(5.0 * d["weight"] for d in rubric["dimensions"])
        weighted_sum = 5.0 * next(d["weight"] for d in rubric["dimensions"] if d["id"] == "team_form")
        expected = weighted_sum / total_weight
        assert abs(result - expected) < 1e-9

    def test_result_within_bounds(self):
        for domain in list(RUBRICS.keys()) + ["general"]:
            rubric = get_rubric(domain)
            # Random-ish scores
            scores = {dim["id"]: (i % 6) for i, dim in enumerate(rubric["dimensions"])}
            result = calculate_weighted_score(scores, domain)
            assert 0.0 <= result <= 1.0

    def test_fallback_domain(self):
        scores = {"base_rate": 3, "catalysts": 4}
        result = calculate_weighted_score(scores, "general")
        assert 0.0 <= result <= 1.0

    def test_unknown_domain_uses_default_rubric(self):
        # Should not raise, uses DEFAULT_RUBRIC
        result = calculate_weighted_score({}, "totally_unknown_domain")
        assert result == 0.0
