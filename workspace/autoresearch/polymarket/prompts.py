PREDICTION_SYSTEM = """You are a calibrated prediction engine. Your job is to estimate the probability of events resolving YES on Polymarket prediction markets.

You must be well-calibrated: when you say 70%, roughly 70% of those events should happen. Overconfidence is the most common failure mode — resist it.

Output ONLY valid JSON. No markdown, no explanation outside the JSON."""

PREDICTION_USER = """Analyze this Polymarket prediction market and estimate the probability of YES.

## Market
Question: {question}
Description: {description}
Category: {category}
Resolution date: {end_date}
Current market price (YES): {market_price:.1%}

## Recent Information
{search_results}

## Required Analysis

Evaluate on these 5 dimensions (score 0-5 each):

1. **base_rate**: Historical frequency of similar events
2. **catalysts**: Specific upcoming events that shift probability (name them with dates)
3. **counterfactual_fragility**: How many independent things must align for YES (high = fragile = lower prob)
4. **information_recency**: How fresh/stale the available evidence is (5 = very recent data)
5. **consensus_bias**: Does the market likely over/underweight certain factors? (5 = strong detectable bias)

## Output Format (strict JSON)
{{
  "probability": <float 0.0-1.0>,
  "confidence": <float 0.0-1.0, how sure you are of your probability estimate>,
  "dimensions": {{
    "base_rate": <int 0-5>,
    "catalysts": <int 0-5>,
    "counterfactual_fragility": <int 0-5>,
    "information_recency": <int 0-5>,
    "consensus_bias": <int 0-5>
  }},
  "reasoning": "<2-3 sentences explaining your key factors>",
  "key_catalysts": ["<specific event 1>", "<specific event 2>"]
}}"""


def build_prediction_prompt(market: dict, search_results: str) -> tuple:
    """Return (system_prompt, user_prompt) for the prediction LLM call."""
    user = PREDICTION_USER.format(
        question=market["question"],
        description=market.get("description", "N/A"),
        category=market.get("category", "Unknown"),
        end_date=market.get("end_date", "Unknown"),
        market_price=market.get("yes_price", 0.5),
        search_results=search_results or "No recent information found.",
    )
    return PREDICTION_SYSTEM, user
