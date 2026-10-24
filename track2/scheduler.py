"""Hour selection: which hour is "good" and where each Class B task goes.

Two schedulers, one scoring rule:
  offline (Case A) perfect foresight, tasks placed before the year starts
  online  (Case B) rolling horizon, one hour committed at a time

Both are greedy and rule-based on purpose: no solver, no ML (Workflow Section
5.5). The scoring rule is shared so the two cases differ only in information,
never in objective.
"""

import numpy as np


def priority_index(price, grid_carbon, lam):
    """Lower = better hour. Normalised by the 99th percentile (Part 2 Section 2.1).

    lam = weight on cost, 1 - lam = weight on carbon. One rule, so "cheap" and
    "clean" are only ever a single knob apart.
    """
    p = price / np.percentile(price, 99)
    c = grid_carbon / np.percentile(grid_carbon, 99)
    return lam * p + (1 - lam) * c


def place_jobs_offline(data, cfg, lam):
    """Case A. Perfect foresight: fill each task from its best hours first."""
    idx = priority_index(data["price"], data["grid_carbon"], lam)
    elastic = np.zeros(data["n"])
    task_schedule = {}
    for task in data["task_attrs"]:
        window = np.arange(task["release_h"], task["deadline_h"] + 1)
        order = window[np.argsort(idx[window])]
        remaining, runs = task["energy_kwh"], []
        for h in order:
            if remaining <= 1e-9:
                break
            kwh = min(task["pmax_kw"] * cfg["dt_h"], remaining)
            elastic[h] += kwh
            runs.append((int(h), kwh))
            remaining -= kwh
        task_schedule[task["task_id"]] = runs
    return elastic, task_schedule


def place_jobs_online(data, cfg, lam):
    """Case B. Rolling horizon: re-plan every hour, commit only the next hour."""
    rng = np.random.default_rng(cfg["seed"] + 1)
    n = data["n"]
    f_price = data["price"] * (1 + rng.normal(0, cfg["forecast_noise"], n))
    f_carbon = data["grid_carbon"] * (1 + rng.normal(0, cfg["forecast_noise"], n))
    f_idx = priority_index(f_price, f_carbon, lam)
    horizon = cfg["horizon_h"]
    elastic = np.zeros(n)
    tasks = [dict(t, remaining=t["energy_kwh"]) for t in data["task_attrs"]]
    task_schedule = {t["task_id"]: [] for t in tasks}

    for t in range(n):
        for task in tasks:
            if not (task["release_h"] <= t <= task["deadline_h"]) or task["remaining"] <= 1e-9:
                continue
            window = np.arange(t, min(task["deadline_h"], t + horizon) + 1)
            need = min(int(np.ceil(task["remaining"] / task["pmax_kw"])), len(window))
            order = window[np.argsort(f_idx[window])]
            if t not in set(order[:need].tolist()):
                continue                                            # wait for a better hour
            power = task["pmax_kw"]
            if f_idx[t] > np.percentile(f_idx[window], 60):          # forced into a bad hour
                hours_left = task["deadline_h"] - t + 1
                power = max(task["pmax_kw"] * cfg["throttle_frac"],
                            task["remaining"] / max(1, hours_left))  # throttle, never miss
            kwh = min(power, task["remaining"])
            elastic[t] += kwh
            task["remaining"] -= kwh
            task_schedule[task["task_id"]].append((t, kwh))
    return elastic, tasks, task_schedule
