"""Annual metrics and the relaxed bound.

Definitions follow Part 1 Section 1.2 rows 4-11, so a number quoted in the paper
can be traced to exactly one function here.
"""

import numpy as np


def summarize_tasks(data, task_schedule, cfg):
    """task_schedule output of Part 1 Section 1.2 row 4: when, how much, finish, lateness."""
    rows = []
    for task in data["task_attrs"]:
        runs = task_schedule.get(task["task_id"], [])
        delivered = sum(k for _, k in runs)
        finish = max((h for h, _ in runs), default=task["release_h"] - 1)
        lateness = max(0, finish - task["deadline_h"])
        on_time = bool(delivered >= task["energy_kwh"] - 1e-6 and lateness == 0)
        rows.append(dict(task_id=task["task_id"], priority_class=task["priority_class"],
                         energy_kwh=task["energy_kwh"], delivered_kwh=delivered,
                         peak_kw=max((k / cfg["dt_h"] for _, k in runs), default=0.0),
                         finish_h=finish, lateness_h=lateness, on_time=on_time))
    return rows


def evaluate(data, res, task_rows, cfg):
    """Annual cost, carbon, green utilization and SLA (Part 1 Section 1.2 rows 5-8)."""
    dt, pue = cfg["dt_h"], cfg["pue"]
    grid_kwh = float(np.sum(res["grid_energy"] * dt))
    annual_cost = float(np.sum(res["grid_energy"] * data["price"] * dt))
    annual_carbon = float(np.sum(res["grid_energy"] * data["grid_carbon"] * dt)) / 1e6
    green_total = float(np.sum(data["green"] * dt))
    curtailed = float(np.sum(res["green_curtailed"] * dt))
    on_time = [row["on_time"] for row in task_rows]
    return dict(
        annual_cost=annual_cost, annual_carbon=annual_carbon,
        annual_cost_facility=annual_cost * pue, annual_carbon_facility=annual_carbon * pue,
        green_utilization=100.0 * (1.0 - curtailed / green_total),
        sla_on_time=100.0 * float(np.mean(on_time)),
        sla_violation=100.0 * (1.0 - float(np.mean(on_time))),
        tasks_late=int(sum(1 for row in task_rows if not row["on_time"])),
        grid_energy_kwh=grid_kwh,
        green_used_kwh=float(np.sum(res["green_used"] * dt)),
        green_curtailed_kwh=curtailed,
        annual_load_kwh=float(np.sum(res["it_load"] * dt)),
        battery_throughput_kwh=float(np.sum(res["discharge"] * dt)),
        soc_min_kwh=float(np.min(res["soc"])), soc_max_kwh=float(np.max(res["soc"])),
    )


def lower_bound(data, cfg):
    """Relaxed bound (Part 2 Section 4): Class A movable, storage lossless and
    unlimited, all on-site green usable at zero marginal cost, the residual load
    billed at the cheapest / cleanest grid hour. No schedule can beat it.
    """
    dt = cfg["dt_h"]
    load_total = float(np.sum(data["rigid_load"] * dt)) + float(
        sum(t["energy_kwh"] for t in data["task_attrs"]))
    green_total = float(np.sum(data["green"] * dt))
    from_grid = max(0.0, load_total - green_total)
    p_min, c_min = float(np.min(data["price"])), float(np.min(data["grid_carbon"]))
    return dict(lb_cost=from_grid * p_min, lb_carbon=from_grid * c_min / 1e6,
                lb_load_kwh=load_total, lb_green_kwh=green_total, lb_grid_kwh=from_grid,
                # All-load variant of Part 1's note. Kept only to show that it fails:
                # green energy is free here, so cost can drop below load x min(price).
                lb_cost_allload=load_total * p_min, lb_carbon_allload=load_total * c_min / 1e6,
                lb_price_min=p_min, lb_carbon_min=c_min,
                lb_price_min_hour=int(np.argmin(data["price"])),
                lb_carbon_min_hour=int(np.argmin(data["grid_carbon"])),
                peak_rigid_kw=float(np.max(data["rigid_load"])))


def add_comparisons(m, base, lb):
    """vs_baseline and gap_to_LB (Part 1 Section 1.2 rows 10-11)."""
    m["vs_baseline"] = dict(cost_pct=100.0 * (m["annual_cost"] / base["annual_cost"] - 1.0),
                            carbon_pct=100.0 * (m["annual_carbon"] / base["annual_carbon"] - 1.0))
    m["gap_to_LB"] = dict(cost_pct=100.0 * (m["annual_cost"] / lb["lb_cost"] - 1.0),
                          carbon_pct=100.0 * (m["annual_carbon"] / lb["lb_carbon"] - 1.0))
    return m
