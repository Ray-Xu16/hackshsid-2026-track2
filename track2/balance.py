"""Hour-by-hour energy balance for a given dispatch rule.

This is the only place where the physical balance lives, so every strategy
(S0, S1, S2, ...) is a choice of *rule*, never a second model:

    s(t) = green(t) + grid_energy(t) + discharge(t)
         = it_load(t) + charge(t) + green_curtailed(t)

charge(t) and discharge(t) are AC power; the round-trip efficiency is applied
inside the SOC update, so the AC balance above holds exactly (and is checked
every run by track2.validation.check_invariants).
"""

import numpy as np

from .scheduler import priority_index


def run_battery(data, elastic, cfg, lam):
    """Green-first energy balance: direct green, then battery, then grid."""
    n = data["n"]
    dt = cfg["dt_h"]
    b = cfg["battery"]
    eta = np.sqrt(b["eta_roundtrip"])                  # one-way efficiency
    cap = b["capacity_mwh"] * 1000.0                   # kWh
    pmax = b["power_mw"] * 1000.0                      # kW
    e_lo, e_hi = b["soc_min"] * cap, b["soc_max"] * cap
    soc = b["soc_init"] * cap

    idx = priority_index(data["price"], data["grid_carbon"], lam)
    discharge_thr = float(np.median(idx))              # above-median-index hours
    charge_thr = float(np.percentile(idx, 25))         # best quartile of hours
    it_load = data["rigid_load"] + elastic

    grid_energy = np.zeros(n)
    green_used = np.zeros(n)
    green_curtailed = np.zeros(n)
    charge = np.zeros(n)
    discharge = np.zeros(n)
    soc_series = np.zeros(n)

    for t in range(n):
        green = data["green"][t]
        g = min(green, it_load[t])                     # 1. direct green
        surplus = green - g
        serve = it_load[t] - g

        d = 0.0                                        # 2. discharge in bad hours
        if serve > 0 and soc > e_lo and idx[t] > discharge_thr:
            d = min(pmax, (soc - e_lo) * eta / dt, serve)
            soc -= d / eta * dt
            serve -= d

        c = max(0.0, min(pmax, surplus, (e_hi - soc) / (eta * dt)))  # 3a. store surplus green
        soc += c * eta * dt

        cg = 0.0                                       # 3b. top up from the grid
        if idx[t] < charge_thr:
            cg = max(0.0, min(pmax - c, (e_hi - soc) / (eta * dt)))
            soc += cg * eta * dt

        grid_energy[t] = serve + cg                    # 4. grid covers the rest
        charge[t] = c + cg
        discharge[t] = d
        green_used[t] = g + c
        green_curtailed[t] = surplus - c
        soc_series[t] = soc

    return dict(grid_energy=grid_energy, green_used=green_used,
                green_curtailed=green_curtailed, charge=charge, discharge=discharge,
                soc=soc_series, it_load=it_load, elastic=elastic)


def run_baseline(data, cfg):
    """S0: no scheduling. Even spread of Class B, no battery, direct green only."""
    n = data["n"]
    elastic = np.zeros(n)
    task_schedule = {}
    for task in data["task_attrs"]:
        hours = np.arange(task["release_h"], task["deadline_h"] + 1)
        per_hour = task["energy_kwh"] / len(hours)
        elastic[hours] += per_hour
        task_schedule[task["task_id"]] = [(int(h), per_hour) for h in hours]
    it_load = data["rigid_load"] + elastic
    green_used = np.minimum(data["green"], it_load)
    zeros = np.zeros(n)
    return dict(grid_energy=it_load - green_used, green_used=green_used,
                green_curtailed=data["green"] - green_used,
                charge=zeros.copy(), discharge=zeros.copy(),
                soc=np.full(n, cfg["battery"]["soc_init"] * cfg["battery"]["capacity_mwh"] * 1000.0),
                it_load=it_load, elastic=elastic, task_schedule=task_schedule)
