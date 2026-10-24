"""Configuration layer: parameters, scenarios, naming contract, fallback text.

Import from here, not from the individual modules, so the internal split can
change without touching callers:

    from track2.config import CONFIG, SCENARIOS, VARIABLE_MAP
"""

from .params import CONFIG
from .scenarios import (LAMBDA_SWEEP, LAM_COST_FIRST, LAM_GREEN_FIRST,
                        LAM_LADDER, LAM_LADDER_SWEEP, SCENARIOS)
from .schema import DATA_DICT, HOURLY_COLUMNS, VARIABLE_MAP
from .fallback import EXCEL_HINT

__all__ = ["CONFIG", "SCENARIOS", "LAMBDA_SWEEP", "LAM_GREEN_FIRST", "LAM_COST_FIRST",
           "LAM_LADDER", "LAM_LADDER_SWEEP", "VARIABLE_MAP", "HOURLY_COLUMNS",
           "DATA_DICT", "EXCEL_HINT"]
