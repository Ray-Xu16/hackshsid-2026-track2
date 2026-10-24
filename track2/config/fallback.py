"""The zero-code fallback path, kept as data because it is quoted verbatim.

This block is printed at the end of the bench run so that a reader without
Python can reproduce the same annual numbers in Excel. The column letters refer
to ``HOURLY_COLUMNS`` in :mod:`track2.config.schema`; if that order changes,
the letters here must change with it.
"""

EXCEL_HINT = """
-- Zero-code fallback (Excel energy-balance sheet) --
  1. Open var/bench/sim_base.csv in Excel (UTF-8 BOM, Chinese text intact).
     Column letters: F=price  G=grid_carbon  J=green  N=it_load
                     O=grid_energy  P=green_used  Q=green_curtailed
     Units already match Part 1: kW and kWh with dt = 1 h, so no x1000 step.
  2. Rebuild the energy balance from scratch in W:AA (fill down to row 8761):
       W2: =MIN(J2,N2)          green used on site (kW)
       X2: =N2-W2               grid purchase (kW)
       Y2: =J2-W2               green curtailed (kW)
       Z2: =X2*F2               electricity cost (yuan)      <- kWh x yuan/kWh
       AA2: =X2*G2/1000000      carbon (tCO2e)               <- g/kWh x kWh / 1e6
     SUM(W:Y) must equal the columns O:P:Q; SUM(Z) and SUM(AA) must equal
     var/bench/scenario_summary.csv, row base (annual_cost, annual_carbon).
  3. The same sheet checks the S1/S2 effect: replace column M (elastic_load)
     with a shifted profile, keep its daily total at 6,000 kWh (SUMIF per day),
     and recompute. The result should sit between the S0 row and the LB row.
"""
