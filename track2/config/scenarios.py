"""Experiment switches: the three scenarios and the lambda values we report.

Same code, different inputs (Part 1 Section 1.1 row 10). Scaling is applied to
the *nominal* series with no random draw, so the three scenarios are paired:
identical weather and load realisations, only the knobs move.
"""

# Label -> price multipliers per TOU segment, and green capacity multipliers.
SCENARIOS = {
    "base": dict(
        label="base",
        price_mult=dict(valley=1.00, flat=1.00, peak=1.00, sharp=1.00),
        solar_mult=1.00, wind_mult=1.00),
    "high_price": dict(
        label="high price (peak-valley spread widened)",
        price_mult=dict(valley=1.00, flat=1.10, peak=1.45, sharp=1.60),
        solar_mult=1.00, wind_mult=1.00),
    "green_scarce": dict(
        label="scarce green (installed capacity reduced)",
        price_mult=dict(valley=1.00, flat=1.00, peak=1.00, sharp=1.00),
        solar_mult=0.40, wind_mult=0.60),
}

# Case A lambda sweep reported in the paper table, and the two points we quote.
LAMBDA_SWEEP = (0.0, 0.2, 0.4, 0.6, 1.0)
LAM_GREEN_FIRST, LAM_COST_FIRST = 0.2, 1.0

# Q2 strategy ladder: default weight and the S3 scan grid.
LAM_LADDER = 0.20
LAM_LADDER_SWEEP = tuple(round(x, 2) for x in [0.0, 0.1, 0.2, 0.3, 0.4, 0.5,
                                               0.6, 0.7, 0.8, 0.9, 1.0])
