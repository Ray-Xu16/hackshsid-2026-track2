"""Run the whole chain: bench -> program -> ladder -> figures.

    python -m experiments.run_all     or     python main.py all

Stops at the first failing stage so a broken table never reaches a figure, and
prints the exit code of every stage at the end (one glance = project health).
"""

import sys
from pathlib import Path

if __package__ in (None, ""):                       # run this file directly
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments import run_bench, run_figures, run_ladder, run_program
from track2 import paths

STAGES = (
    ("bench", "8,760 h table x 3 scenarios", run_bench.main, ["--quiet"]),
    ("program", "Case A / Case B table", run_program.main, ["--quiet"]),
    ("ladder", "S0 / S1 / S2 / S3", run_ladder.main, ["--quiet"]),
    ("figures", "four figures", run_figures.main, []),
)


def main(argv=None):
    paths.ensure()
    results = []
    for name, what, entry, flags in STAGES:
        print("\n>>> %-9s %s" % (name, what))
        code = entry(list(flags) + list(argv or []))
        results.append((name, code))
        if code:
            print(">>> stopped at %s (exit %d)" % (name, code))
            break
    print("\n" + "=" * 60)
    for name, code in results:
        print("  %-9s %s" % (name, "ok" if code == 0 else "FAILED (exit %d)" % code))
    print("  var/    %s" % paths.VAR)
    print("  assets/ %s" % paths.ASSETS)
    return 0 if all(c == 0 for _, c in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
