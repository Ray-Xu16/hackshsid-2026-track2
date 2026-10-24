"""The Q2 strategy ladder: S0 / S1 / S2, and S3 as a lambda sweep.

S1 is S2 with the battery switched off (power_mw = 0), so the S2 - S1 gap is
attributable to storage alone and not to a different placement rule. That
property is why this module exists: the four strategies are four settings of
the same code path, not four programs.
"""

import numpy as np
import pandas as pd

from . import balance, metrics, scheduler
from .validation import ab_inputs_shared


def without_battery(cfg):
    """S1 runs the same balance code with a zero-power battery."""
    return dict(cfg, battery=dict(cfg["battery"], power_mw=0.0))


def run_flat(data, cfg):
    """S0: no scheduling at all."""
    res = balance.run_baseline(data, cfg)
    return res, metrics.summarize_tasks(data, res["task_schedule"], cfg), cfg


def run_shifted(data, cfg, lam, storage):
    """S1 / S2: place Class B greedily, then run the energy balance."""
    cfg = cfg if storage else without_battery(cfg)
    elastic, schedule = scheduler.place_jobs_offline(data, cfg, lam)
    res = balance.run_battery(data, elastic, cfg, lam)
    res["task_schedule"] = schedule
    return res, metrics.summarize_tasks(data, schedule, cfg), cfg


def score(data, res, rows, cfg, base, lb):
    """Annual metrics plus vs-S0 and gap-to-LB (Part 1 Section 1.2 rows 5-11)."""
    return metrics.add_comparisons(metrics.evaluate(data, res, rows, cfg), base, lb)


def sweep(data, cfg, lb, grid):
    """S3: scan lam over the grid, then mark the non-dominated points honestly."""
    pts = []
    for lam in grid:
        res, rows, c = run_shifted(data, cfg, float(lam), True)
        m = metrics.evaluate(data, res, rows, c)
        pts.append(dict(lam=float(lam), cost=m["annual_cost"], carbon=m["annual_carbon"],
                        green=m["green_utilization"], sla=m["sla_on_time"],
                        throughput_kwh=m["battery_throughput_kwh"],
                        curtailed_kwh=m["green_curtailed_kwh"]))
    df = pd.DataFrame(pts)
    c, g = df["cost"].values[:, None], df["carbon"].values[:, None]
    df["on_front"] = ~((c >= c.T) & (g >= g.T) & ((c > c.T) | (g > g.T))).any(axis=1)
    df["gap_lb_cost_pct"] = 100.0 * (df["cost"] / lb["lb_cost"] - 1.0)
    df["gap_lb_carbon_pct"] = 100.0 * (df["carbon"] / lb["lb_carbon"] - 1.0)
    return df


def knee_point(front, base):
    """Fair compromise: maximise the worse of the two improvements vs S0.

    A pure "closest to the ideal corner" rule would drift to the cheap end and
    report a carbon gain of ~2%, which is no compromise at all. Maximin asks
    instead: which point leaves neither objective badly behind.
    """
    f = front[front["on_front"]].copy()
    f["gain_cost"] = 1.0 - f["cost"] / base["annual_cost"]
    f["gain_carbon"] = 1.0 - f["carbon"] / base["annual_carbon"]
    f["worst_gain"] = f[["gain_cost", "gain_carbon"]].min(axis=1)
    return f.loc[f["worst_gain"].idxmax()]


def runs_share_one_load(data, runs):
    """DoD: every strategy serves the same load from the same unmutated inputs."""
    loads = [r[0]["it_load"].sum() for r in runs.values()]
    return bool(np.ptp(loads) < 1e-6 and ab_inputs_shared(data))
