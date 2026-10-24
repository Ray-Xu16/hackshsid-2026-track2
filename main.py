#!/usr/bin/env python3
"""Single entry point for the Track 2 project.

    python main.py bench       # 8,760 h x 3 scenarios  -> var/bench/
    python main.py program     # Case A / Case B table  -> stdout
    python main.py ladder      # S0/S1/S2/S3 + Pareto   -> var/ladder/
    python main.py figures     # four figures           -> assets/figures/
    python main.py all         # the four stages above, in order
    python main.py variables   # paper <-> program name map
    python main.py bound       # Q3 relaxed-bound report

Every flag of a stage is forwarded unchanged, e.g.
    python main.py ladder --lam 0.4 --scenario base
"""

import sys

from experiments import run_all, run_bench, run_figures, run_ladder, run_program

STAGES = {
    "bench": run_bench.main,
    "program": run_program.main,
    "ladder": run_ladder.main,
    "figures": run_figures.main,
    "all": run_all.main,
}
ALIASES = {
    "variables": (run_program.main, ["--variables"]),
    "bound": (run_program.main, ["--bound"]),
}


def usage():
    return __doc__.strip()


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(usage())
        return 0 if argv else 2
    cmd, rest = argv[0], argv[1:]
    if cmd in STAGES:
        return STAGES[cmd](rest)
    if cmd in ALIASES:
        entry, fixed = ALIASES[cmd]
        return entry(fixed + rest)
    print("unknown command: %s\n\n%s" % (cmd, usage()))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
