"""Domain-specific prediction rubrics.

Each domain has a set of evaluation dimensions tailored to what matters
for prediction accuracy in that area. Rubrics are used both in the
prediction prompt and for post-hoc calibration analysis.
"""

# Domain detection keywords
DOMAIN_KEYWORDS = {
    "geopolitics": ["war", "military", "troops", "ceasefire", "sanctions", "regime", "invasion", "forces enter", "iran", "russia", "china", "nato"],
    "politics": ["election", "president", "prime minister", "nomination", "vote", "parliament", "governor", "senate", "democrat", "republican"],
    "crypto": ["bitcoin", "btc", "ethereum", "eth", "token", "fdv", "crypto", "blockchain", "defi", "nft"],
    "sports": ["nba", "nfl", "fifa", "world cup", "championship", "finals", "match", "game", "tournament", "grand prix", "atp"],
    "economics": ["gdp", "inflation", "fed", "interest rate", "recession", "unemployment", "tariff", "trade"],
    "tech": ["ai", "launch", "release", "ipo", "acquisition", "product", "regulation"],
}

RUBRICS = {
    "geopolitics": {
        "name": "Geopolitical Conflict & Diplomacy",
        "dimensions": [
            {
                "id": "military_posture",
                "name": "Military Posture & Deployment",
                "description": "Current force positioning, troop movements, weapons systems deployed. Score 5 if active deployment matching the predicted action is underway.",
                "weight": 1.5,
            },
            {
                "id": "decision_maker_intent",
                "name": "Decision-Maker Intent Signals",
                "description": "Statements, actions, and historical patterns of key decision-makers (presidents, generals). Score 5 if decision-maker has explicitly signaled intent to act.",
                "weight": 2.0,
            },
            {
                "id": "diplomatic_status",
                "name": "Diplomatic Channel Status",
                "description": "Active negotiations, rejected proposals, broken-off talks. Score 5 if all diplomatic channels exhausted and parties refuse to negotiate.",
                "weight": 1.5,
            },
            {
                "id": "escalation_trajectory",
                "name": "Escalation Trajectory",
                "description": "Direction and speed of escalation over past 2 weeks. Score 5 if rapid escalation with no de-escalation signals.",
                "weight": 1.0,
            },
            {
                "id": "domestic_political_constraint",
                "name": "Domestic Political Constraints",
                "description": "Internal political pressure for/against action. Score 5 if strong domestic support for the predicted action.",
                "weight": 1.0,
            },
            {
                "id": "resolution_precision",
                "name": "Resolution Criteria Precision",
                "description": "How precisely the resolution criteria match observable events. Score 5 if criteria are unambiguous and easily verified.",
                "weight": 1.0,
            },
        ],
    },
    "politics": {
        "name": "Electoral & Political Outcomes",
        "dimensions": [
            {
                "id": "polling_data",
                "name": "Polling Data Quality & Consensus",
                "description": "Quantity and quality of polls, pollster agreement. Score 5 if multiple high-quality polls strongly agree.",
                "weight": 2.0,
            },
            {
                "id": "institutional_advantage",
                "name": "Institutional & Structural Advantage",
                "description": "Incumbency, gerrymandering, media control, party machinery. Score 5 if strong institutional advantage for predicted outcome.",
                "weight": 1.5,
            },
            {
                "id": "historical_precedent",
                "name": "Historical Precedent",
                "description": "How often similar political events have occurred. Score 5 if strong historical precedent exists.",
                "weight": 1.0,
            },
            {
                "id": "late_breaking_catalyst",
                "name": "Late-Breaking Catalyst Potential",
                "description": "Likelihood of scandal, endorsement, or event that could shift outcome. Score 5 if no plausible catalyst exists before resolution.",
                "weight": 1.0,
            },
            {
                "id": "pollster_divergence",
                "name": "Pollster Methodology Divergence",
                "description": "Disagreement between polling methodologies (e.g., govt vs independent pollsters). Score 5 if high divergence suggesting systematic bias.",
                "weight": 1.5,
            },
        ],
    },
    "crypto": {
        "name": "Cryptocurrency Price & Token Events",
        "dimensions": [
            {
                "id": "price_distance",
                "name": "Price Distance to Target",
                "description": "Current price vs target price as percentage. Score 5 if target is within normal daily volatility range.",
                "weight": 2.0,
            },
            {
                "id": "resolution_mechanics",
                "name": "Resolution Mechanics (wick vs close)",
                "description": "Whether resolution uses high/low wick or closing price. Score 5 if wick-based (easier to hit). Score 1 if closing price (harder).",
                "weight": 2.0,
            },
            {
                "id": "macro_regime",
                "name": "Macro Market Regime",
                "description": "Bull/bear/sideways trend, risk-on/off environment. Score 5 if current regime strongly favors the predicted direction.",
                "weight": 1.5,
            },
            {
                "id": "liquidity_structure",
                "name": "Liquidity & Holder Structure",
                "description": "ETF flows, long-term holder percentage, exchange reserves. Score 5 if liquidity structure supports predicted direction.",
                "weight": 1.0,
            },
            {
                "id": "time_window",
                "name": "Time Window vs Volatility",
                "description": "Time remaining vs historical volatility. Score 5 if ample time for the move to occur given normal vol.",
                "weight": 1.5,
            },
            {
                "id": "catalyst_events",
                "name": "Scheduled Catalysts",
                "description": "FOMC meetings, token unlocks, ETF decisions, halvings. Score 5 if major scheduled catalyst before resolution.",
                "weight": 1.0,
            },
        ],
    },
    "sports": {
        "name": "Sports Outcomes",
        "dimensions": [
            {
                "id": "team_form",
                "name": "Recent Form & Momentum",
                "description": "Win/loss record in last 5-10 games, scoring trends. Score 5 if dominant recent form.",
                "weight": 1.5,
            },
            {
                "id": "head_to_head",
                "name": "Head-to-Head Record",
                "description": "Historical matchup data between specific teams/players. Score 5 if clear historical dominance.",
                "weight": 1.0,
            },
            {
                "id": "injury_availability",
                "name": "Injury & Availability",
                "description": "Key player injuries, suspensions, rest decisions. Score 5 if all key players available.",
                "weight": 2.0,
            },
            {
                "id": "venue_advantage",
                "name": "Venue & Surface Advantage",
                "description": "Home/away, surface type (clay/grass/hard), altitude. Score 5 if strong venue advantage.",
                "weight": 1.0,
            },
            {
                "id": "betting_line_movement",
                "name": "Betting Line Movement",
                "description": "Direction and magnitude of odds movement from opening to current. Score 5 if sharp money strongly supports predicted outcome.",
                "weight": 1.5,
            },
            {
                "id": "tournament_context",
                "name": "Tournament Stage & Motivation",
                "description": "Elimination game vs group stage, playoff positioning incentives. Score 5 if high-stakes context increases predicted outcome likelihood.",
                "weight": 1.0,
            },
        ],
    },
}

# Fallback for unrecognized domains
DEFAULT_RUBRIC = {
    "name": "General Prediction",
    "dimensions": [
        {"id": "base_rate", "name": "Base Rate", "description": "Historical frequency of similar events. Score 5 if strong historical base rate exists.", "weight": 1.0},
        {"id": "catalysts", "name": "Catalysts", "description": "Specific upcoming events that shift probability. Score 5 if imminent catalyst strongly favors predicted outcome.", "weight": 1.5},
        {"id": "counterfactual_fragility", "name": "Counterfactual Fragility", "description": "How many independent things must align. Score 5 if outcome depends on single verifiable condition.", "weight": 1.0},
        {"id": "information_recency", "name": "Information Recency", "description": "Freshness of available evidence. Score 5 if very recent reliable data.", "weight": 1.0},
        {"id": "consensus_bias", "name": "Consensus Bias", "description": "Whether market over/underweights certain factors. Score 5 if strong detectable bias.", "weight": 1.5},
    ],
}


def detect_domain(question: str, category: str = "") -> str:
    """Detect the domain of a market from its question and category."""
    text = f"{question} {category}".lower()
    scores = {}
    for domain, keywords in DOMAIN_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            scores[domain] = score
    if not scores:
        return "general"
    return max(scores, key=scores.get)


def get_rubric(domain: str) -> dict:
    """Get the rubric for a domain. Falls back to DEFAULT_RUBRIC."""
    return RUBRICS.get(domain, DEFAULT_RUBRIC)


def format_rubric_for_prompt(domain: str) -> str:
    """Format a rubric's dimensions into text for inclusion in an LLM prompt."""
    rubric = get_rubric(domain)
    lines = [f"Domain: {rubric['name']}", "", "Evaluate on these dimensions (score 0-5 each):", ""]
    for i, dim in enumerate(rubric["dimensions"], 1):
        lines.append(f"{i}. **{dim['name']}** (weight: {dim['weight']}x): {dim['description']}")
    return "\n".join(lines)


def calculate_weighted_score(dimension_scores: dict, domain: str) -> float:
    """Calculate a weighted average score from dimension scores.

    Returns a value between 0.0 and 1.0 (normalized).
    """
    rubric = get_rubric(domain)
    total_weight = 0.0
    weighted_sum = 0.0
    for dim in rubric["dimensions"]:
        score = dimension_scores.get(dim["id"], 0)
        weight = dim["weight"]
        weighted_sum += score * weight
        total_weight += 5.0 * weight  # max score is 5
    if total_weight == 0:
        return 0.5
    return weighted_sum / total_weight
