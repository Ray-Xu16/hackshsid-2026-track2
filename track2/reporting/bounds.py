"""Q3: the relaxed bound, the gap decomposition, and why it stays unreachable.

Kept separate from the model because it is an argument, not a computation: two
candidate bound formulas are printed side by side so a reader can see that the
all-load variant of Part 1 fails in this setting (on-site green has zero
marginal cost, so cost can fall below load x min(price)).
"""

from .. import balance, metrics, scheduler
from ..config import LAM_GREEN_FIRST


def bound_report(data, cfg, scenario="base"):
    lb = metrics.lower_bound(data, cfg)
    dt = cfg["dt_h"]
    E, G, R = lb["lb_load_kwh"], lb["lb_green_kwh"], lb["lb_grid_kwh"]
    s0 = balance.run_baseline(data, cfg)
    m0 = metrics.evaluate(data, s0, metrics.summarize_tasks(data, s0["task_schedule"], cfg), cfg)
    elastic, schedule = scheduler.place_jobs_offline(data, cfg, LAM_GREEN_FIRST)
    res = balance.run_battery(data, elastic, cfg, LAM_GREEN_FIRST)
    m2 = metrics.evaluate(data, res, metrics.summarize_tasks(data, schedule, cfg), cfg)
    e0, p_bar = m0["grid_energy_kwh"], m0["annual_cost"] / m0["grid_energy_kwh"]
    gap = m0["annual_cost"] - lb["lb_cost"]
    volume, price = (e0 - R) * p_bar, R * (p_bar - lb["lb_price_min"])
    close = lambda a, b, c: 100.0 * (a - b) / (a - c)
    lines = [
        "Q3 relaxed bound  (scenario %s, seed %d, dt = %d h)" % (scenario, cfg["seed"], dt),
        "  E_load %.0f kWh | E_green %.0f kWh | residual E_grid %.0f kWh (%.1f%% of load)"
        % (E, G, R, 100.0 * R / E),
        "  min price %.4f yuan/kWh at hour %d | min carbon %.1f g/kWh at hour %d"
        % (lb["lb_price_min"], lb["lb_price_min_hour"], lb["lb_carbon_min"], lb["lb_carbon_min_hour"]),
        "",
        "  LB_formula                                        cost (yuan)   carbon (t)",
        "  (a) all load x min          -> INVALID here  %14.0f %12.1f"
        % (lb["lb_cost_allload"], lb["lb_carbon_allload"]),
        "  (b) residual load x min     -> used below   %14.0f %12.1f"
        % (lb["lb_cost"], lb["lb_carbon"]),
        "",
        "  strategy              cost      vs LB    closes   carbon    vs LB    closes",
        "  S0 no scheduling  %10.0f %+9.1f%% %7.1f%% %9.1f %+8.1f%% %7.1f%%" % (
            m0["annual_cost"], 100 * (m0["annual_cost"] / lb["lb_cost"] - 1),
            close(m0["annual_cost"], m0["annual_cost"], lb["lb_cost"]),
            m0["annual_carbon"], 100 * (m0["annual_carbon"] / lb["lb_carbon"] - 1),
            close(m0["annual_carbon"], m0["annual_carbon"], lb["lb_carbon"])),
        "  S2 green+battery  %10.0f %+9.1f%% %7.1f%% %9.1f %+8.1f%% %7.1f%%" % (
            m2["annual_cost"], 100 * (m2["annual_cost"] / lb["lb_cost"] - 1),
            close(m0["annual_cost"], m2["annual_cost"], lb["lb_cost"]),
            m2["annual_carbon"], 100 * (m2["annual_carbon"] / lb["lb_carbon"] - 1),
            close(m0["annual_carbon"], m2["annual_carbon"], lb["lb_carbon"])),
        "",
        "  gap S0 -> LB = %.0f yuan, split into %.0f (extra kWh bought, %.1f%%) "
        "+ %.0f (price above the minimum, %.1f%%)"
        % (gap, volume, 100 * volume / gap, price, 100 * price / gap),
        "  reachability: LB needs %.0f kWh inside hour %d, i.e. %.0f kW held for 1 h; rigid peak "
        "is %.0f kW (x%.0f), battery holds %.0f kWh (%.2f%% of that energy)"
        % (R, lb["lb_price_min_hour"], R / dt, lb["peak_rigid_kw"],
           R / dt / lb["peak_rigid_kw"], cfg["battery"]["capacity_mwh"] * 1000,
           100.0 * cfg["battery"]["capacity_mwh"] * 1000 / R),
    ]
    return "\n".join(lines)
