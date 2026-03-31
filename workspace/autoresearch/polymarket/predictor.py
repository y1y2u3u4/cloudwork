import json
import re
import urllib.request
import urllib.parse
from html.parser import HTMLParser

import anthropic

from config import ANTHROPIC_API_KEY, PREDICTION_MODEL
from prompts import build_prediction_prompt


# ---------------------------------------------------------------------------
# HTML parser to extract DuckDuckGo result snippets
# ---------------------------------------------------------------------------

class _DDGParser(HTMLParser):
    """Minimal parser to pull text snippets from DuckDuckGo HTML results."""

    def __init__(self):
        super().__init__()
        self.snippets = []
        self._in_snippet = False
        self._current = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        # DDG wraps snippets in <a class="result__snippet"> or
        # <span class="result__snippet">
        cls = attrs_dict.get("class", "")
        if "result__snippet" in cls:
            self._in_snippet = True
            self._current = []

    def handle_endtag(self, tag):
        if self._in_snippet and tag in ("a", "span"):
            text = "".join(self._current).strip()
            if text:
                self.snippets.append(text)
            self._in_snippet = False
            self._current = []

    def handle_data(self, data):
        if self._in_snippet:
            self._current.append(data)


def web_search(query: str, max_results: int = 5) -> str:
    """Search using DuckDuckGo HTML endpoint (free, no API key required).

    Returns a formatted string of result snippets, or
    "No recent information found." if nothing useful is retrieved.
    """
    encoded = urllib.parse.quote_plus(query)
    url = f"https://html.duckduckgo.com/html/?q={encoded}"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except Exception as exc:
        return f"Search failed: {exc}"

    parser = _DDGParser()
    parser.feed(html)

    snippets = parser.snippets[:max_results]
    if not snippets:
        return "No recent information found."

    lines = []
    for i, snippet in enumerate(snippets, 1):
        lines.append(f"{i}. {snippet}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Core prediction pipeline
# ---------------------------------------------------------------------------

def _parse_json_response(text: str) -> dict:
    """Extract JSON from the model response, stripping any markdown fences."""
    # Strip ```json ... ``` or ``` ... ``` wrappers
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def predict_market(market: dict) -> dict:
    """Full prediction pipeline for a single Polymarket market.

    Parameters
    ----------
    market : dict
        Must contain at least ``question``. Optional keys: ``description``,
        ``category``, ``end_date``, ``yes_price``.

    Returns
    -------
    dict with keys:
        probability, confidence, reasoning, dimensions, key_catalysts,
        sources, error
    """
    question = market.get("question", "")

    # Step 1: gather recent context via web search
    search_query = f'"{question}" latest news 2026'
    search_results = web_search(search_query)

    # Step 2: build prompts
    system_prompt, user_prompt = build_prediction_prompt(market, search_results)

    # Step 3: call Anthropic API
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        message = client.messages.create(
            model=PREDICTION_MODEL,
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        raw_text = message.content[0].text
    except Exception as exc:
        return {
            "probability": 0.5,
            "confidence": 0.0,
            "reasoning": f"API call failed: {exc}",
            "dimensions": {},
            "key_catalysts": [],
            "sources": search_results,
            "error": True,
        }

    # Step 4: parse JSON response
    try:
        parsed = _parse_json_response(raw_text)
    except (json.JSONDecodeError, ValueError):
        return {
            "probability": 0.5,
            "confidence": 0.0,
            "reasoning": f"Failed to parse response: {raw_text[:200]}",
            "dimensions": {},
            "key_catalysts": [],
            "sources": search_results,
            "error": True,
        }

    return {
        "probability": float(parsed.get("probability", 0.5)),
        "confidence": float(parsed.get("confidence", 0.0)),
        "reasoning": parsed.get("reasoning", ""),
        "dimensions": parsed.get("dimensions", {}),
        "key_catalysts": parsed.get("key_catalysts", []),
        "sources": search_results,
        "error": False,
    }
