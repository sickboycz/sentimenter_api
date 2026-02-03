# What the numbers mean

This pack defines three *separate* concepts:

1) beta_market.yaml
   - Signed coefficients in [-1..+1]
   - Interpret as: "when channel sign is +1, this market tends to move in the sign of beta"
   - Example: SP500.rates = -0.35 means rates-up is a headwind for SP500.

2) beta_sector.yaml / beta_industry.yaml
   - Signed coefficients in [-1..+1]
   - Same interpretation as market betas, but at sector / industry level.

3) ticker_exposures.csv
   - Magnitudes in [0..1] (no sign!)
   - Interpret as: "how sensitive is this ticker to this channel?"
   - The sign comes from the **channel sign** (Call A) and the sector/industry beta signs.

In other words:
- betas answer: direction given channel sign
- exposures answer: magnitude of sensitivity
