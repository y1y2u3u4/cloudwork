"""Edge detection and Kelly position sizing for Polymarket."""
from config import (
    MIN_EDGE,
    MIN_CONFIDENCE,
    MAX_POSITIONS,
    MIN_TRADE_SIZE,
    MAX_TRADE_SIZE,
    KELLY_FRACTION,
    BANKROLL,
)


def calculate_edge(ai_prob: float, market_price: float) -> float:
    """Calculate edge as ai_prob - market_price.

    Positive edge = buy YES, Negative edge = buy NO.
    """
    return ai_prob - market_price


def calculate_position_size(
    edge: float,
    market_price: float,
    bankroll: float,
    kelly_fraction: float = KELLY_FRACTION,
    min_size: float = MIN_TRADE_SIZE,
    max_size: float = MAX_TRADE_SIZE,
) -> float:
    """Calculate position size using Kelly criterion.

    For YES (edge > 0): kelly = abs_edge / (1 - market_price)
    For NO (edge < 0): kelly = abs_edge / market_price
    size = kelly * kelly_fraction * bankroll
    If size < min_size: return 0.0
    Return min(size, max_size)
    """
    abs_edge = abs(edge)

    if edge > 0:
        # Buying YES
        kelly = abs_edge / (1 - market_price)
    else:
        # Buying NO
        kelly = abs_edge / market_price

    size = kelly * kelly_fraction * bankroll

    if size < min_size:
        return 0.0

    return min(size, max_size)


def generate_signal(
    market_id: str,
    question: str,
    ai_prob: float,
    ai_confidence: float,
    market_price: float,
    bankroll: float = BANKROLL,
    open_positions: int = 0,
    max_positions: int = MAX_POSITIONS,
):
    """Generate a trading signal or return None if conditions not met.

    Returns None if:
    - open_positions >= max_positions
    - ai_confidence < MIN_CONFIDENCE (0.70)
    - |edge| < MIN_EDGE (0.10)
    - size == 0.0

    Returns dict with: market_id, question, direction, edge, ai_prob,
    market_price, size_usd
    """
    # Check position limit
    if open_positions >= max_positions:
        return None

    # Check confidence threshold
    if ai_confidence < MIN_CONFIDENCE:
        return None

    edge = calculate_edge(ai_prob, market_price)

    # Check edge threshold
    if abs(edge) < MIN_EDGE:
        return None

    size = calculate_position_size(edge=edge, market_price=market_price, bankroll=bankroll)

    # Check minimum size
    if size == 0.0:
        return None

    direction = "YES" if edge > 0 else "NO"

    return {
        "market_id": market_id,
        "question": question,
        "direction": direction,
        "edge": round(edge, 4),
        "ai_prob": ai_prob,
        "market_price": market_price,
        "size_usd": size,
    }
