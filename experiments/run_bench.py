"""Experiment bench: 8,760 h x 1 h, three scenarios, one row per hour.

    python main.py bench [--scenario all] [--seed 42] [--outdir var/bench]

Not the scoring program - this is the data arm behind Q2 (baseline) and Q3
(distance to the relaxed bound). Every series is produced by
``track2.inputs``, i.e. the same generator the program of record uses, so the
S0 row printed here is identical to the S0 row of ``run_program``.
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

if __package__ in (None, ""):                       # run this file directly
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from track2 import balance, inputs, metrics, paths, validation
from track2.config import CONFIG, DATA_DICT, EXCEL_HINT, HOURLY_COLUMNS, SCENARIOS


def build_scenario(name, cfg, seed):
    """One scenario -> (hourly table, annual metrics). All series from track2.inputs."""
    data = validation.attach_snapshot(inputs.build_inputs(cfg, name, seed))
    res = balance.run_baseline(data, cfg)
    rows = metrics.summarize_tasks(data, res["task_schedule"], cfg)
    m = metrics.evaluate(data, res, rows, cfg)
    lb = metrics.lower_bound(data, cfg)
    metrics.add_comparisons(m, m, lb)

    stamp = pd.date_range("2026-01-01 00:00", periods=data["n"], freq="h")
    df = pd.DataFrame({
        "hour": np.arange(data["n"]),
        "timestamp": stamp,
        "day": np.arange(data["n"]) // 24 + 1,
        "hour_of_day": data["hod"],
        "tou_segment": data["tou_segment"],
        "price": data["price"],
        "grid_carbon": data["grid_carbon"],
        "solar": data["solar"],
        "wind": data["wind"],
        "green": data["green"],
        "rigid_load": data["rigid_load"],
        "elastic_total_kwh": data["elastic_total_kwh"],
        "elastic_load": res["elastic"],
        "it_load": res["it_load"],
        "grid_energy": res["grid_energy"],
        "green_used": res["green_used"],
        "green_curtailed": res["green_curtailed"],
        "soc": res["soc"],
        "charge": res["charge"],
        "discharge": res["discharge"],
        "scenario": name,
    })[HOURLY_COLUMNS]

    summary = dict(
        scenario=name, label=SCENARIOS[name]["label"], hours=data["n"], pue=cfg["pue"],
        annual_load_kwh=round(m["annual_load_kwh"], 1),
        annual_load_mwh=round(m["annual_load_kwh"] / 1000, 1),
        elastic_total_kwh_day=data["elastic_total_kwh"],
        green_kwh=round(lb["lb_green_kwh"], 1),
        grid_energy_kwh=round(m["grid_energy_kwh"], 1),
        green_used_kwh=round(m["green_used_kwh"], 1),
        green_curtailed_kwh=round(m["green_curtailed_kwh"], 1),
        green_utilization=round(m["green_utilization"], 2),
        sla_on_time=round(m["sla_on_time"], 2),
        annual_cost=round(m["annual_cost"], 0),
        annual_cost_facility=round(m["annual_cost_facility"], 0),
        annual_carbon=round(m["annual_carbon"], 1),
        annual_carbon_facility=round(m["annual_carbon_facility"], 1),
        lb_cost=round(lb["lb_cost"], 0), lb_carbon=round(lb["lb_carbon"], 1),
        gap_to_LB_cost_pct=round(m["gap_to_LB"]["cost_pct"], 2),
        gap_to_LB_carbon_pct=round(m["gap_to_LB"]["carbon_pct"], 2),
        battery_capacity_mwh=cfg["battery"]["capacity_mwh"],
        battery_power_mw=cfg["battery"]["power_mw"],
        battery_eta_roundtrip=cfg["battery"]["eta_roundtrip"],
        soc_min_frac=cfg["battery"]["soc_min"], soc_max_frac=cfg["battery"]["soc_max"],
        price_min=round(float(df["price"].min()), 4),
        price_max=round(float(df["price"].max()), 4),
        price_mean=round(float(df["price"].mean()), 4),
        grid_carbon_min=round(float(df["grid_carbon"].min()), 1),
        grid_carbon_max=round(float(df["grid_carbon"].max()), 1),
        grid_carbon_mean=round(float(df["grid_carbon"].mean()), 1),
        solar_peak_kw=round(float(df["solar"].max()), 1),
        wind_mean_kw=round(float(df["wind"].mean()), 1),
        seed=seed,
    )
    return df, summary, data, res, lb


def verify(df, summary, data, res, cfg):
    """DoD checks: run through, plus the unit / definition conventions of Part 1."""
    b = cfg["battery"]
    cap = b["capacity_mwh"] * 1000.0
    balance_gap = (df["green"] + df["grid_energy"] + df["discharge"]
                   - df["it_load"] - df["charge"] - df["green_curtailed"]).abs().max()
    daily = df.groupby("day")["elastic_load"].sum()
    cost_per_kwh = summary["annual_cost"] / summary["grid_energy_kwh"]
    carbon_per_kwh = summary["annual_carbon"] * 1e6 / summary["grid_energy_kwh"]
    return [
        ("8760 rows", len(df) == cfg["n_days"] * 24, len(df)),
        ("no missing value", int(df.isna().sum().sum()) == 0, "-"),
        ("no negative power", bool((df[["solar", "wind", "grid_energy",
                                        "green_curtailed"]] >= -1e-9).all().all()), "-"),
        ("hourly energy balance", bool(balance_gap < 1e-6),
         "max|delta| = %.2e kW" % balance_gap),
        ("daily elastic total fixed",
         bool((daily - data["elastic_total_kwh"]).abs().max() < 1e-6),
         "%.0f kWh/day" % daily.iloc[0]),
        ("solar <= nameplate", bool(df["solar"].max() <= cfg["solar_peak_kw"] + 1e-6),
         "%.0f kW of %.0f kW" % (df["solar"].max(), cfg["solar_peak_kw"])),
        ("soc inside limits", bool(df["soc"].between(b["soc_min"] * cap - 1e-6,
                                                     b["soc_max"] * cap + 1e-6).all()),
         "[%.0f, %.0f] of %.0f kWh" % (df["soc"].min(), df["soc"].max(), cap)),
        ("green utilization in 0-100", bool(0 <= summary["green_utilization"] <= 100),
         "%.2f%%" % summary["green_utilization"]),
        ("unit: cost per kWh inside price range",
         bool(summary["price_min"] * 0.9 <= cost_per_kwh <= summary["price_max"] * 1.1),
         "%.3f yuan/kWh" % cost_per_kwh),
        ("unit: carbon per kWh inside carbon range",
         bool(cfg["carbon_floor"] - 1e-6 <= carbon_per_kwh <= cfg["carbon_ceil"] + 1e-6),
         "%.0f gCO2e/kWh" % carbon_per_kwh),
        ("LB is not beaten", bool(summary["annual_cost"] >= summary["lb_cost"] - 1e-6
                                  and summary["annual_carbon"] >= summary["lb_carbon"] - 1e-6),
         "gap %.1f%% / %.1f%%" % (summary["gap_to_LB_cost_pct"],
                                  summary["gap_to_LB_carbon_pct"])),
        ("inputs untouched by dispatch", validation.ab_inputs_shared(data), "-"),
        ("SLA reported", bool(summary["sla_on_time"] >= 0), "%.2f%%" % summary["sla_on_time"]),
    ]


def main(argv=None):
    ap = argparse.ArgumentParser(description="Track 2 experiment bench (8,760 h)")
    ap.add_argument("--scenario", default="all", choices=["all", *SCENARIOS])
    ap.add_argument("--seed", type=int, default=CONFIG["seed"])
    ap.add_argument("--outdir", default=str(paths.BENCH))
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    cfg = dict(CONFIG)
    names = list(SCENARIOS) if args.scenario == "all" else [args.scenario]
    summaries, ok_all = [], True
    for name in names:
        df, summary, data, res, _ = build_scenario(name, cfg, args.seed)
        checks = verify(df, summary, data, res, cfg)
        ok = all(c[1] for c in checks)
        ok_all &= ok
        df.to_csv(outdir / ("sim_%s.csv" % name), index=False, encoding="utf-8-sig")
        summaries.append(summary)
        if not args.quiet:
            print("\n%s\n[%s] %s   checks %s" % ("=" * 78, name, summary["label"],
                                                 "passed" if ok else "FAILED"))
            for label, passed, detail in checks:
                print("   %s %-46s %s" % ("ok  " if passed else "FAIL", label, detail))

    summary_df = pd.DataFrame(summaries)
    summary_df.to_csv(outdir / "scenario_summary.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(DATA_DICT, columns=["column", "paper reference", "unit", "definition"]).to_csv(
        outdir / "data_dictionary.csv", index=False, encoding="utf-8-sig")

    cols = ["scenario", "annual_load_mwh", "green_kwh", "green_utilization", "grid_energy_kwh",
            "annual_cost", "annual_carbon", "gap_to_LB_cost_pct", "gap_to_LB_carbon_pct"]
    print("\n" + "=" * 78 + "\nScenario summary (S0 baseline, IT side)")
    print(summary_df[cols].to_string(index=False))
    print("\noutdir: %s" % outdir)
    print(EXCEL_HINT)
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())
