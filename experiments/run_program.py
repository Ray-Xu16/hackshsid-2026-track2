"""Program of record: the Case A / Case B table of Part 2 Section 4.

    python main.py program [--scenario base] [--seed 42] [--bound] [--variables]
    python main.py program --inputs var/bench/sim_base.csv     # read the bench table

This is the entry point the paper's numbers come from. It only orchestrates:
inputs come from ``track2.inputs``, schedulers from ``track2.scheduler``, the
energy balance from ``track2.balance``, and the table is rendered by
``track2.reporting``.
"""

import argparse
import sys
from pathlib import Path

import numpy as np

if __package__ in (None, ""):                       # run this file directly
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from track2 import balance, inputs, metrics, paths, scheduler, validation
from track2.config import (CONFIG, LAMBDA_SWEEP, LAM_COST_FIRST, LAM_GREEN_FIRST,
                           SCENARIOS, VARIABLE_MAP)
from track2.reporting import bound_report, print_table, report


def program(cfg, data, quiet=False):
    """Run S0, the Case A lambda sweep and the two Case B variants on one dataset."""
    lb = metrics.lower_bound(data, cfg)
    checks, table = [], []

    s0 = balance.run_baseline(data, cfg)
    rows0 = metrics.summarize_tasks(data, s0["task_schedule"], cfg)
    m0 = metrics.evaluate(data, s0, rows0, cfg)
    m0 = metrics.add_comparisons(m0, m0, lb)         # S0 vs itself -> 0 % on both axes
    checks += validation.check_invariants(data, s0, rows0, cfg, "S0")

    if not quiet:
        print("Relaxed lower bound (best case): cost %.0f yuan, carbon %.1f t"
              % (lb["lb_cost"], lb["lb_carbon"]))
        report("S0 baseline (no scheduling)", m0)
    table.append(("Relaxed lower bound (best case)", "%d" % lb["lb_cost"],
                  "%.1f" % lb["lb_carbon"], "-", "-", "-"))
    table.append(("S0: no scheduling", "%d" % m0["annual_cost"], "%.1f" % m0["annual_carbon"],
                  "%.1f%%" % m0["green_utilization"], "-", "-"))

    # Case A: lam sweep. lam = weight on cost, 1-lam = weight on carbon.
    case_a = {}
    for lam in LAMBDA_SWEEP:
        elastic, schedule = scheduler.place_jobs_offline(data, cfg, lam)
        res = balance.run_battery(data, elastic, cfg, lam)
        rows = metrics.summarize_tasks(data, schedule, cfg)
        m = metrics.add_comparisons(metrics.evaluate(data, res, rows, cfg), m0, lb)
        case_a[lam] = (m, res, rows)
        checks += validation.check_invariants(data, res, rows, cfg, "A lam=%.1f" % lam)
        tag = "  <- greenness-first" if lam == LAM_GREEN_FIRST else (
            "  <- cost-first" if lam == LAM_COST_FIRST else "")
        if not quiet:
            report("Case A offline lam=%.1f" % lam, m, tag)
        if lam in (LAM_GREEN_FIRST, LAM_COST_FIRST):
            label = "Case A, lam = %.1f (%s)" % (
                lam, "greenness-first" if lam == LAM_GREEN_FIRST else "cost-first")
            table.append((label, "%d" % m["annual_cost"], "%.1f" % m["annual_carbon"],
                          "%.1f%%" % m["green_utilization"],
                          "%+.1f%%" % m["vs_baseline"]["cost_pct"],
                          "%+.1f%%" % m["vs_baseline"]["carbon_pct"]))

    # Case B: same lam, noisy forecast and perfect forecast.
    for noise, label in ((cfg["forecast_noise"], "Case B, noisy forecast"),
                         (0.0, "Case B, perfect forecast")):
        cfg_b = dict(cfg, forecast_noise=noise)
        elastic, tasks, schedule = scheduler.place_jobs_online(data, cfg_b, LAM_GREEN_FIRST)
        res = balance.run_battery(data, elastic, cfg_b, LAM_GREEN_FIRST)
        rows = metrics.summarize_tasks(data, schedule, cfg_b)
        m = metrics.add_comparisons(metrics.evaluate(data, res, rows, cfg_b), m0, lb)
        checks += validation.check_invariants(data, res, rows, cfg_b, label)
        if not quiet:
            report("%s lam=%.1f" % (label, LAM_GREEN_FIRST), m)
        table.append(("%s, lam = %.1f" % (label, LAM_GREEN_FIRST), "%d" % m["annual_cost"],
                      "%.1f" % m["annual_carbon"], "%.1f%%" % m["green_utilization"],
                      "%+.1f%%" % m["vs_baseline"]["cost_pct"],
                      "%+.1f%%" % m["vs_baseline"]["carbon_pct"]))

    print_table(table)

    m_green = case_a[LAM_GREEN_FIRST][0]
    print("\nLoad check: rigid %.0f MWh + elastic %.0f MWh = %.0f MWh/yr; green %.0f MWh/yr"
          % (float(np.sum(data["rigid_load"])) / 1000,
             float(sum(t["energy_kwh"] for t in data["task_attrs"])) / 1000,
             lb["lb_load_kwh"] / 1000, lb["lb_green_kwh"] / 1000))
    print("Facility side (pue = %.2f): S0 cost %.0f yuan, carbon %.1f t; "
          "greenness-first cost %.0f yuan, carbon %.1f t"
          % (cfg["pue"], m0["annual_cost_facility"], m0["annual_carbon_facility"],
             m_green["annual_cost_facility"], m_green["annual_carbon_facility"]))
    print("Battery throughput %.0f kWh/yr against %.0f kWh/yr of annual load (%.1f%% of load)"
          % (m_green["battery_throughput_kwh"], m_green["annual_load_kwh"],
             100.0 * m_green["battery_throughput_kwh"] / m_green["annual_load_kwh"]))
    return lb, m0, checks


def main(argv=None):
    ap = argparse.ArgumentParser(description="Track 2 scheduler (8,760 h, 1 h step)")
    ap.add_argument("--scenario", default="base", choices=list(SCENARIOS))
    ap.add_argument("--seed", type=int, default=CONFIG["seed"])
    ap.add_argument("--inputs", default=None,
                    help="CSV from the bench instead of the synthetic series")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--variables", action="store_true",
                    help="print the paper-to-program variable map")
    ap.add_argument("--bound", action="store_true",
                    help="print the Q3 relaxed-bound report and exit")
    args = ap.parse_args(argv)
    if args.variables:
        print(VARIABLE_MAP)
        return 0

    cfg = dict(CONFIG)
    if args.bound:
        print(bound_report(inputs.build_inputs(cfg, args.scenario, args.seed), cfg, args.scenario))
        return 0
    if args.inputs:
        data = inputs.load_inputs(args.inputs, cfg)
    else:
        data = inputs.build_inputs(cfg, args.scenario, args.seed)
    validation.attach_snapshot(data)

    _, _, checks = program(cfg, data, args.quiet)
    paths.ensure()
    passed, failed = validation.summarize(checks)
    print("\nDoD checks: %d passed, %d failed" % (passed, len(failed)))
    for label, _, detail in failed:
        print("   FAIL  %-52s %s" % (label, detail))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
