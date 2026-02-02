import pytest

@pytest.mark.skip(reason="Invariant enforcement occurs in allocation engine; enable once implemented.")
def test_unknown_ticker_rejected():
    # Allocation engine must reject unknown tickers (not in ticker_universe).
    assert False
