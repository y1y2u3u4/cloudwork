"""Map-Reduce Prediction Architecture for Polymarket.

Replaces the single-pass predictor with a 4-step parallel analysis (Map)
followed by a synthesis step (Reduce).

Map phase (4 independent sub-analyses):
  1. Resolution Rules Analyst  — parse exact resolution criteria
  2. Evidence Gatherer         — web search for supporting/opposing facts
  3. Counter-Argument Analyst  — devil's advocate against market consensus
  4. Domain Catalyst Analyst   — upcoming events / catalysts

Reduce phase:
  Synthesize all 4 analyses into a final calibrated probability.
"""

import json
import re
import concurrent.futures
from typing import Optional

import anthropic

from config import ANTHROPIC_API_KEY, PREDICTION_MODEL
from predictor import web_search  # reuse existing DuckDuckGo searcher

# Models used for each phase
ANALYSIS_MODEL = PREDICTION_MODEL   # fast model for Map phase
SYNTHESIS_MODEL = PREDICTION_MODEL  # same for now; swap to opus for higher quality


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_parse(text: str) -> dict:
    """Parse JSON from an LLM response, stripping markdown fences gracefully."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Return partial result so callers can still continue
        return {"parse_error": text[:300]}


def _call_model(system: str, user: str, max_tokens: int = 512,
                model: str = ANALYSIS_MODEL) -> dict:
    """Single Anthropic API call returning a parsed dict."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    resp = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return _safe_parse(resp.content[0].text)


# ---------------------------------------------------------------------------
# Map phase — 4 sub-analyses
# ---------------------------------------------------------------------------

def analyze_resolution_rules(question: str, description: str) -> dict:
    """Map step 1: Parse resolution criteria and identify edge cases.

    Returns
    -------
    dict with keys:
        resolution_summary, key_conditions, edge_cases,
        ambiguity_flags, resolution_type
    """
    prompt = f"""Analyze this Polymarket resolution criteria. Be extremely precise.

Question: {question}
Resolution Rules: {description}

Output strict JSON:
{{
  "resolution_summary": "<1-2 sentence plain language summary of what triggers YES>",
  "key_conditions": ["<specific condition 1>", "<condition 2>"],
  "edge_cases": ["<scenario that could be ambiguous>"],
  "ambiguity_flags": ["<any vague terms that could be interpreted differently>"],
  "resolution_type": "<binary|threshold|date-bound|conditional>"
}}"""
    return _call_model(
        system=(
            "You are a legal analyst specializing in prediction market resolution "
            "criteria. Output ONLY valid JSON."
        ),
        user=prompt,
        max_tokens=512,
    )


def gather_evidence(question: str) -> dict:
    """Map step 2: Search web for factual evidence both for and against.

    Returns
    -------
    dict with keys:
        supporting_evidence, opposing_evidence, key_facts, information_date
    """
    supporting_search = web_search(f"{question} latest news evidence 2026", max_results=5)
    opposing_search = web_search(
        f"{question} unlikely obstacles problems 2026", max_results=3
    )

    prompt = f"""Based on these search results, extract structured factual evidence.

Question: {question}

Search Results (supporting):
{supporting_search}

Search Results (opposing / obstacles):
{opposing_search}

Output strict JSON:
{{
  "supporting_evidence": ["<specific fact supporting YES>"],
  "opposing_evidence": ["<specific fact supporting NO>"],
  "key_facts": ["<most important factual data points>"],
  "information_date": "<approximate date of most recent info found>"
}}"""
    return _call_model(
        system=(
            "You are a fact-checker. Extract only verifiable factual claims. "
            "Output ONLY valid JSON."
        ),
        user=prompt,
        max_tokens=512,
    )


def analyze_counter_arguments(question: str, market_price: float) -> dict:
    """Map step 3: Devil's advocate — argue against the market consensus.

    Returns
    -------
    dict with keys:
        market_consensus_direction, counter_arguments,
        strongest_counter, counter_probability
    """
    consensus = "YES" if market_price > 0.5 else "NO"
    prompt = f"""The prediction market prices this at {market_price:.0%} YES.
Market consensus leans {consensus}.

Your job: argue the OPPOSITE. Why is the market WRONG?

Question: {question}

Think about: What is the market missing? What cognitive biases might explain the current price?
What low-probability scenarios could change everything?

Output strict JSON:
{{
  "market_consensus_direction": "{consensus}",
  "counter_arguments": ["<argument 1 against consensus>"],
  "strongest_counter": "<the single most compelling reason the market is wrong>",
  "counter_probability": <float: your contrarian estimate for P(YES)>
}}"""
    return _call_model(
        system=(
            "You are a contrarian analyst. Your job is to find flaws in consensus "
            "thinking. Be specific and evidence-based. Output ONLY valid JSON."
        ),
        user=prompt,
        max_tokens=512,
    )


def analyze_catalysts(question: str, category: str, end_date: str) -> dict:
    """Map step 4: Identify upcoming events / catalysts that could shift outcome.

    Returns
    -------
    dict with keys:
        upcoming_catalysts, catalyst_timeline, binary_events,
        catalyst_impact_direction
    """
    search_results = web_search(
        f"{question} upcoming events deadlines schedule 2026", max_results=3
    )

    prompt = f"""Identify specific upcoming catalysts for this prediction market.

Question: {question}
Category: {category}
Resolution date: {end_date}

Recent info:
{search_results}

Output strict JSON:
{{
  "upcoming_catalysts": ["<specific event with date>"],
  "catalyst_timeline": [
    {{"event": "<event>", "date": "<YYYY-MM-DD or approximate>",
      "impact": "increases_yes|increases_no|uncertain"}}
  ],
  "binary_events": ["<event that could cause sudden large move>"],
  "catalyst_impact_direction": "bullish_yes|bullish_no|mixed|neutral"
}}"""
    return _call_model(
        system=(
            "You are an events analyst. Identify SPECIFIC upcoming events with dates. "
            "Output ONLY valid JSON."
        ),
        user=prompt,
        max_tokens=512,
    )


# ---------------------------------------------------------------------------
# Reduce phase
# ---------------------------------------------------------------------------

def synthesize_prediction(
    question: str,
    description: str,
    market_price: float,
    category: str,
    end_date: str,
    rules_analysis: dict,
    evidence: dict,
    counter_args: dict,
    catalysts: dict,
) -> dict:
    """Reduce step: Synthesize all 4 sub-analyses into a final probability.

    Returns
    -------
    dict with keys:
        probability, confidence, reasoning, key_factors,
        risk_flags, resolution_check
    """
    prompt = f"""You are making a final probability prediction by synthesizing 4 independent analyses.

## Market
Question: {question}
Description: {description[:500]}
Category: {category}
Resolution date: {end_date}
Current market price: {market_price:.1%}

## Analysis 1: Resolution Rules
{json.dumps(rules_analysis, indent=2)}

## Analysis 2: Factual Evidence
{json.dumps(evidence, indent=2)}

## Analysis 3: Counter-Arguments (Devil's Advocate)
{json.dumps(counter_args, indent=2)}

## Analysis 4: Upcoming Catalysts
{json.dumps(catalysts, indent=2)}

## Your Task
1. Check: Does the factual evidence actually satisfy the resolution conditions?
2. Weigh supporting vs opposing evidence objectively.
3. Consider the strongest counter-argument — how much should it shift your estimate?
4. Factor in the catalyst timeline — are there binary events before resolution?
5. Flag any resolution edge cases or ambiguities.

Be well-calibrated. Overconfidence is the #1 failure mode. When uncertain, stay close to the
market price unless you have strong directional evidence.

Output strict JSON:
{{
  "probability": <float 0.0-1.0>,
  "confidence": <float 0.0-1.0>,
  "reasoning": "<3-5 sentences synthesizing all analyses>",
  "key_factors": ["<most important factor 1>", "<factor 2>", "<factor 3>"],
  "risk_flags": ["<any concerns about this prediction>"],
  "resolution_check": "yes|no|partial"
}}"""
    return _call_model(
        system=(
            "You are a calibrated prediction synthesizer. Integrate multiple independent "
            "analyses into a single probability estimate. Output ONLY valid JSON."
        ),
        user=prompt,
        max_tokens=1024,
        model=SYNTHESIS_MODEL,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def predict_market_deep(market: dict, parallel: bool = True) -> dict:
    """Full Map-Reduce prediction pipeline for a single Polymarket market.

    Parameters
    ----------
    market : dict
        Must contain at least ``question``. Optional keys:
        ``description``, ``category``, ``end_date``, ``yes_price``.
    parallel : bool
        If True (default), run the 4 Map analyses in parallel threads.
        Set to False for sequential execution (easier debugging).

    Returns
    -------
    dict with keys:
        probability, confidence, reasoning, key_factors, risk_flags,
        resolution_check, analyses, errors, error
    """
    question = market.get("question", "")
    description = market.get("description", "")
    market_price = float(market.get("yes_price", 0.5))
    category = market.get("category", "Unknown")
    end_date = market.get("end_date", "Unknown")

    analyses: dict = {}
    errors: list = []

    # ------------------------------------------------------------------
    # Map phase
    # ------------------------------------------------------------------
    def _run(name: str, fn, *args):
        """Execute a sub-analysis, capturing errors gracefully."""
        try:
            return name, fn(*args), None
        except Exception as exc:
            return name, {}, str(exc)

    tasks = [
        ("rules",     analyze_resolution_rules,    question, description),
        ("evidence",  gather_evidence,             question),
        ("counter",   analyze_counter_arguments,   question, market_price),
        ("catalysts", analyze_catalysts,           question, category, end_date),
    ]

    if parallel:
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(_run, name, fn, *args): name
                for name, fn, *args in tasks
            }
            for future in concurrent.futures.as_completed(futures):
                name, result, err = future.result()
                analyses[name] = result
                if err:
                    errors.append(f"{name} analysis failed: {err}")
    else:
        for name, fn, *args in tasks:
            name, result, err = _run(name, fn, *args)
            analyses[name] = result
            if err:
                errors.append(f"{name} analysis failed: {err}")

    # ------------------------------------------------------------------
    # Reduce phase
    # ------------------------------------------------------------------
    try:
        synthesis = synthesize_prediction(
            question=question,
            description=description,
            market_price=market_price,
            category=category,
            end_date=end_date,
            rules_analysis=analyses.get("rules", {}),
            evidence=analyses.get("evidence", {}),
            counter_args=analyses.get("counter", {}),
            catalysts=analyses.get("catalysts", {}),
        )
    except Exception as exc:
        return {
            "probability": 0.5,
            "confidence": 0.0,
            "reasoning": f"Synthesis failed: {exc}",
            "key_factors": [],
            "risk_flags": [],
            "resolution_check": "unknown",
            "analyses": analyses,
            "errors": errors,
            "error": True,
        }

    # Validate probability is in range
    probability = float(synthesis.get("probability", 0.5))
    probability = max(0.0, min(1.0, probability))
    confidence = float(synthesis.get("confidence", 0.0))
    confidence = max(0.0, min(1.0, confidence))

    return {
        "probability": probability,
        "confidence": confidence,
        "reasoning": synthesis.get("reasoning", ""),
        "key_factors": synthesis.get("key_factors", []),
        "risk_flags": synthesis.get("risk_flags", []),
        "resolution_check": synthesis.get("resolution_check", ""),
        "analyses": analyses,
        "errors": errors,
        "error": bool(synthesis.get("parse_error")),
    }
