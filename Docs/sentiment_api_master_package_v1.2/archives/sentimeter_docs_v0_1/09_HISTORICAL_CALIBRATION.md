# 09_HISTORICAL_CALIBRATION.md
## Goal
Initial priors from historical replay before live forward calibration.

Method:
- ingest news up to time T (no lookahead)
- build clusters/events at T
- record expectations
- measure outcomes at T+1/3/7/14
- derive priors: lag distributions, magnitude bins, topic multipliers

Anti-overfit:
coarse bins, min samples, regime tagging
