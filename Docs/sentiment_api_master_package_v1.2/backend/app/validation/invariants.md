# invariants (v1.2)

## Tickers
- Every output ticker must exist in ticker_universe and be active.
- winners sorted desc by expected_return_bps; losers sorted asc.
- expected_return_bps within [-5000, 5000].
- rationale_en length >= 10.

## Clusters
- first_seen <= last_seen.
- impact_score 0..100.
- L3+ must have >=2 sources unless credibility includes official.
