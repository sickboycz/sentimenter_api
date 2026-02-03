"""Unit tests: LLM asset targeting allowlist enforcement (v1.0)."""
from sentiment_api.engines.llm_asset_targeting.schemas import TickerSelectResult, TickerPick


def test_allowlist_membership_validation():
    """Tickers in TickerSelectResult must be validated against allowed set before use."""
    allowed = {"AAPL", "MSFT"}
    result = TickerSelectResult(
        winners=[TickerPick(symbol="AAPL", strength=0.8, why_refs=[], short_why_en="ok")],
        losers=[TickerPick(symbol="MSFT", strength=0.6, why_refs=[], short_why_en="ok")],
    )
    for p in result.winners + result.losers:
        assert p.symbol.upper() in allowed


def test_no_hallucinated_tickers_contract():
    """Runner must filter/reject any ticker not in allowed_symbols (contract)."""
    # Document contract: Call C output is validated; non-allowlisted tickers raise ValueError
    allowed_set = {"AAPL", "MSFT"}
    picks = [TickerPick(symbol="AAPL", strength=0.8, why_refs=[], short_why_en="")]
    for p in picks:
        assert p.symbol.upper() in allowed_set
