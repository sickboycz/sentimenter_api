# Channel sign semantics (must be consistent)

These semantics define what Call A sign means. Everything downstream assumes them.

- rates: +1 = yields/rates up (hawkish), -1 = yields/rates down (dovish)
- inflation: +1 = inflation up surprise, -1 = inflation cooling
- growth: +1 = growth improving, -1 = growth deteriorating
- liquidity: +1 = liquidity easing, -1 = liquidity tightening
- credit_stress: +1 = stress rising / spreads widening, -1 = stress easing
- geopolitics: +1 = escalation, -1 = de-escalation
- energy_supply: +1 = supply tightness / price pressure, -1 = easing
- trade_controls: +1 = tightening controls, -1 = easing
- regulation: +1 = tightening regulation, -1 = deregulation
- risk_appetite: +1 = risk-on flows, -1 = risk-off flows

If you change any of these semantics, you must re-calibrate.
