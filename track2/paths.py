"""Every path the programs use, resolved from this file's location.

Nothing else in the project hard-codes a directory name: if a file needs to read
or write something, it imports it from here. That keeps "where does the output
go" a one-line answer and makes the tree relocatable.

  var/     dynamic content - everything a program produces at run time
  assets/  presentation assets - figures, written report documents,
           and the read-only upstream sources they cite
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]      # hackathon/

VAR = ROOT / "var"                             # dynamic content (generated)
BENCH = VAR / "bench"                          # 8,760 h tables, scenario summary
LADDER = VAR / "ladder"                        # strategy matrix, Pareto points
ARCHIVE = VAR / "archive"                      # superseded contracts, for traceability

ASSETS = ROOT / "assets"                       # presentation assets (curated)
FIGURES = ASSETS / "figures"                   # PNG output of run_figures.py
DOCS = ASSETS / "docs"                         # written report sections
REFERENCE = ASSETS / "reference"               # upstream sources, read-only: nothing writes here

DEFAULT_DIRS = (BENCH, LADDER, FIGURES)


def ensure(*dirs):
    """Create the given directories (default: all writable output dirs)."""
    for d in dirs or DEFAULT_DIRS:
        Path(d).mkdir(parents=True, exist_ok=True)
    return dirs or DEFAULT_DIRS


def as_path(d):
    """Accept either a Path or a CLI string and return a Path."""
    return Path(d) if d else None
