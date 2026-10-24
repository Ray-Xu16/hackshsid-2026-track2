"""Q2 experiment: the S0 / S1 / S2 / S3 ladder across all three scenarios.

    python main.py ladder [--scenario all] [--lam 0.2] [--outdir var/ladder]

No second physics model here: the strategies come from ``track2.strategies`` and
the balance from ``track2.balance``, both on the Part 1 names and units. This
file only loops, checks and writes tables.
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

if __package__ in (None, ""):                       # run this file directly
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from track2 import inputs, metrics, paths, strategies, validation
from track2.config import CONFIG, LAM_LADDER, LAM_LADDER_SWEEP, SCENARIOS
from track2.reporting import report_table, write_markdown


def ladder(data, cfg, lam, lb, name, grid=LAM_LADDER_SWEEP):
    """Run the four strategies on one scenario -> (rows, Pareto front, checks)."""
    runs = {"S0": strategies.run_flat(data, cfg),
            "S1": strategies.run_shifted(data, cfg, lam, False),
            "S2": strategies.run_shifted(data, cfg, lam, True)}
    base = metrics.evaluate(data, runs["S0"][0], runs["S0"][1], cfg)
    base = metrics.add_comparisons(base, base, lb)
    front = strategies.sweep(data, cfg, lb, grid)
    knee = strategies.knee_point(front, base)

    rows, checks = [], []
    for tag in ("S0", "S1", "S2"):
        res, task_rows, cfg_run = runs[tag]
        m = base if tag == "S0" else strategies.score(data, res, task_rows, cfg_run, base, lb)
        rows.append(dict(scenario=name, strategy=tag, lam=lam,
                         annual_cost=m["annual_cost"], annual_carbon=m["annual_carbon"],
                         green_utilization=m["green_utilization"],
                         sla_on_time=m["sla_on_time"],
                         vs_s0_cost_pct=m["vs_baseline"]["cost_pct"],
                         vs_s0_carbon_pct=m["vs_baseline"]["carbon_pct"],
                         gap_lb_cost_pct=m["gap_to_LB"]["cost_pct"],
                         gap_lb_carbon_pct=m["gap_to_LB"]["carbon_pct"],
                         battery_throughput_kwh=m["battery_throughput_kwh"],
                         green_curtailed_kwh=m["green_curtailed_kwh"],
                         soc_min_kwh=m["soc_min_kwh"], soc_max_kwh=m["soc_max_kwh"]))
        checks += strategies_check(data, res, task_rows, cfg_run, tag)
    rows.append(dict(scenario=name, strategy="S3", lam=float(knee["lam"]),
                     annual_cost=knee["cost"], annual_carbon=knee["carbon"],
                     green_utilization=knee["green"], sla_on_time=knee["sla"],
                     vs_s0_cost_pct=100.0 * (knee["cost"] / base["annual_cost"] - 1.0),
                     vs_s0_carbon_pct=100.0 * (knee["carbon"] / base["annual_carbon"] - 1.0),
                     gap_lb_cost_pct=knee["gap_lb_cost_pct"],
                     gap_lb_carbon_pct=knee["gap_lb_carbon_pct"],
                     battery_throughput_kwh=knee["throughput_kwh"],
                     green_curtailed_kwh=knee["curtailed_kwh"],
                     soc_min_kwh=np.nan, soc_max_kwh=np.nan))
    checks.append(("strategies share one load and one price series",
                   strategies.runs_share_one_load(data, runs), "-"))
    checks.append(("S1 battery idle (isolates the S2 effect)",
                   bool(np.all(runs["S1"][0]["charge"] == 0)
                        and np.all(runs["S1"][0]["discharge"] == 0)), "-"))
    checks.append(("LB not beaten by any strategy",
                   bool(min(r["annual_cost"] for r in rows) >= lb["lb_cost"] - 1e-6
                        and min(r["annual_carbon"] for r in rows)
                        >= lb["lb_carbon"] - 1e-6), "-"))
    return rows, front, checks


def strategies_check(data, res, rows, cfg, tag):
    """Program-of-record checks, plus the Q2-specific daily-total check."""
    checks = validation.check_invariants(data, res, rows, cfg, tag)
    daily = np.sum(res["elastic"].reshape(-1, 24) * cfg["dt_h"], axis=1)
    checks.append((tag + " daily Class B total fixed",
                   bool(np.max(np.abs(daily - data["elastic_total_kwh"])) < 1e-6),
                   "%.0f kWh/day" % daily[0]))
    return checks


def main(argv=None):
    ap = argparse.ArgumentParser(description="Q2 strategy ladder on the track2 contract")
    ap.add_argument("--scenario", default="all", choices=["all", *SCENARIOS])
    ap.add_argument("--seed", type=int, default=CONFIG["seed"])
    ap.add_argument("--lam", type=float, default=LAM_LADDER)
    ap.add_argument("--outdir", default=str(paths.LADDER))
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    cfg = dict(CONFIG, lam=args.lam)

    names = list(SCENARIOS) if args.scenario == "all" else [args.scenario]
    rows_all, fronts, lbs, checks = [], {}, {}, []
    for name in names:
        data = validation.attach_snapshot(inputs.build_inputs(cfg, name, args.seed))
        lb = metrics.lower_bound(data, cfg)
        rows, front, block = ladder(data, cfg, args.lam, lb, name)
        rows_all += rows
        fronts[name], lbs[name] = front, lb
        checks += block
        front.round(2).to_csv(outdir / ("pareto_%s.csv" % name),
                              index=False, encoding="utf-8-sig")

    mx = pd.DataFrame(rows_all).round(2)
    mx.to_csv(outdir / "strategy_matrix.csv", index=False, encoding="utf-8-sig")
    write_markdown(mx, fronts, lbs["base"], outdir / "Q2_strategy_matrix.md", cfg, args.lam)

    if not args.quiet:
        print(report_table(mx) + "\n\nS3 front (base):\n"
              + fronts["base"][["lam", "cost", "carbon", "green", "on_front"]]
              .round(2).to_string(index=False))
    passed, failed = validation.summarize(checks)
    print("\nDoD checks: %d passed, %d failed" % (passed, len(failed)))
    print("\n".join("   FAIL  %s  %s" % (l, d) for l, _, d in failed))
    print("SLA min %.2f%%; SOC [%.0f, %.0f] kWh of %.0f; Class B %.0f kWh/day; out: %s"
          % (mx["sla_on_time"].min(), mx["soc_min_kwh"].min(skipna=True),
             mx["soc_max_kwh"].max(skipna=True), cfg["battery"]["capacity_mwh"] * 1000,
             data["elastic_total_kwh"], outdir / "strategy_matrix.csv"))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
