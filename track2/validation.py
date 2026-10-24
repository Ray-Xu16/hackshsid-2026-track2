"""DoD checks. Every experiment reports through these, so the same 8 invariants
are asserted no matter which scheduler produced the series.

The AB rule (identical inputs for every strategy) needs a snapshot before any
dispatch runs; that is what :func:`attach_snapshot` records.
"""

import numpy as np

SNAPSHOT_KEYS = ("price", "grid_carbon", "green", "rigid_load")


def attach_snapshot(data):
    """Freeze the input series so a later check can prove dispatch did not mutate them."""
    data["snapshot"] = {k: data[k].copy() for k in SNAPSHOT_KEYS}
    return data


def ab_inputs_shared(data):
    """Dispatch must not mutate the input series: every strategy sees the same data."""
    snap = data.get("snapshot")
    if snap is None:
        return False
    return all(np.array_equal(v, data[k]) for k, v in snap.items())


def check_invariants(data, res, task_rows, cfg, tag):
    """DoD checks: SLA reported, SOC inside limits, power rating, energy balance."""
    dt, b = cfg["dt_h"], cfg["battery"]
    cap, pmax = b["capacity_mwh"] * 1000.0, b["power_mw"] * 1000.0
    balance = (data["green"] + res["grid_energy"] + res["discharge"]
               - res["it_load"] - res["charge"] - res["green_curtailed"])
    soc_ok = bool(np.all(res["soc"] >= b["soc_min"] * cap - 1e-6)
                  and np.all(res["soc"] <= b["soc_max"] * cap + 1e-6))
    daily = np.sum(res["elastic"].reshape(-1, 24) * dt, axis=1)
    checks = [
        ("SLA violation reported", True, "%.2f%% (%d task(s) late)"
         % (100.0 - 100.0 * np.mean([r["on_time"] for r in task_rows]),
            sum(1 for r in task_rows if not r["on_time"]))),
        ("SOC inside [min, max]", soc_ok, "[%.1f, %.1f] of %.0f kWh" % (
            res["soc"].min(), res["soc"].max(), cap)),
        ("charge <= rated power", bool(np.all(res["charge"] <= pmax + 1e-6)),
         "%.1f kW of %.0f kW" % (res["charge"].max(), pmax)),
        ("discharge <= rated power", bool(np.all(res["discharge"] <= pmax + 1e-6)),
         "%.1f kW of %.0f kW" % (res["discharge"].max(), pmax)),
        ("hourly energy balance", bool(np.max(np.abs(balance)) < 1e-6),
         "max|delta| = %.2e kW" % np.max(np.abs(balance))),
        ("daily elastic total fixed", bool(np.max(np.abs(
            daily - data["elastic_total_kwh"])) < 1e-6),
         "%.0f kWh/day" % daily[0]),
        ("no negative power", bool(min(data["green"].min(), res["grid_energy"].min(),
                                       res["green_curtailed"].min()) >= -1e-9), "-"),
        ("S0 shares the same inputs", ab_inputs_shared(data), "-"),
    ]
    return [(tag + " " + label, ok, detail) for label, ok, detail in checks]


def summarize(checks):
    """-> (passed, failed list) for the CLI footer."""
    failed = [c for c in checks if not c[1]]
    return len(checks) - len(failed), failed
