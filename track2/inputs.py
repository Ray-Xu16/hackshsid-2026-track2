"""Input series: synthesis, external CSV loading, scenario scaling.

One generator for the whole project. Both the program of record and the
experiment bench call into this module, which is what keeps the two from
drifting into separate conventions.
"""

import csv

import numpy as np

from .config import SCENARIOS


def tou_segment_of(hod):
    """TOU segment label per hour of day (valley / flat / peak / sharp)."""
    seg = np.full(hod.shape, "flat", dtype=object)
    seg[(hod >= 23) | (hod < 7)] = "valley"
    seg[((hod >= 12) & (hod < 14)) | ((hod >= 18) & (hod < 21))] = "peak"
    seg[(hod >= 18) & (hod < 20)] = "sharp"
    return seg


def synthesize_inputs(cfg, seed=None):
    """Build one year of hourly inputs plus the Class B task list.

    All parameters are placeholders; task D2 replaces them with anchored data
    (TOU tariff catalog, grid emission factors, PVWatts / ERA5 profiles,
    MLPerf-based workload split, Hithium datasheet storage parameters).
    """
    rng = np.random.default_rng(cfg["seed"] if seed is None else seed)
    n = cfg["n_days"] * 24
    hod = np.arange(n) % 24
    seg = tou_segment_of(hod)

    price = np.full(n, cfg["price_flat"])
    price[seg == "valley"] = cfg["price_valley"]
    price[seg == "peak"] = cfg["price_peak"]
    price[seg == "sharp"] = cfg["price_sharp"]
    price = price * (1.0 + rng.normal(0.0, cfg["price_noise_sd"], n))

    daylight = np.clip((hod - 6) / 12.0, 0.0, 1.0)
    solar_norm = np.clip(np.sin(np.pi * daylight), 0.0, 1.0)
    grid_carbon = (cfg["carbon_midday"]
                   + (cfg["carbon_valley"] - cfg["carbon_midday"]) * (1.0 - solar_norm))
    grid_carbon = np.clip(grid_carbon + rng.normal(0.0, cfg["carbon_noise_sd"], n),
                          cfg["carbon_floor"], cfg["carbon_ceil"])

    # Solar: sine-shaped day, cloud attenuation clipped at nameplate (inverter limit).
    solar = cfg["solar_peak_kw"] * solar_norm * np.clip(
        1.0 + rng.normal(0.0, cfg["solar_cloud_sd"], n), cfg["solar_cloud_floor"], 1.0)
    wind = np.clip(cfg["wind_mean_kw"] + rng.normal(0.0, cfg["wind_std_kw"], n), 0.0, None)

    rigid_load = (cfg["rigid_base_kw"]
                  + cfg["rigid_amp_kw"] * np.sin(2 * np.pi * (hod - 8) / 24.0)
                  + rng.normal(0.0, cfg["rigid_noise_sd"], n))
    rigid_load = np.clip(rigid_load, cfg["rigid_floor_kw"], None)

    # One Class B task per day: fixed daily energy, 24 h window, no overlap.
    task_attrs = [dict(task_id="T%03d" % d, energy_kwh=cfg["elastic_total_kwh"],
                       release_h=d * 24, deadline_h=d * 24 + 23,
                       pmax_kw=cfg["job_pmax_kw"], priority_class="B")
                  for d in range(cfg["n_days"])]
    return dict(n=n, hod=hod, tou_segment=seg, price=price, grid_carbon=grid_carbon,
                solar=solar, wind=wind, green=solar + wind, rigid_load=rigid_load,
                elastic_total_kwh=cfg["elastic_total_kwh"], task_attrs=task_attrs)


def load_inputs(csv_path, cfg):
    """Read the hourly table written by the bench and rebuild the input dict.

    Case A with external files: the columns are the Part 1 names, so the
    offline scheduler consumes the same series as the experiment bench.
    """
    cols = {k: [] for k in ("price", "grid_carbon", "solar", "wind", "rigid_load",
                            "elastic_total_kwh")}
    with open(csv_path, newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            for k in cols:
                cols[k].append(float(row[k]))
    for k, v in cols.items():
        cols[k] = np.asarray(v)
    n = len(cols["price"])
    if n % 24:
        raise ValueError("hourly table is not a whole number of days: %d rows" % n)
    hod = np.arange(n) % 24
    n_days = n // 24
    daily = cols["elastic_total_kwh"].reshape(n_days, 24)
    if not np.allclose(daily, daily[:, :1]):
        raise ValueError("elastic_total is not constant inside a day (Part 1 Section 1.1 row 6)")
    task_attrs = [dict(task_id="T%03d" % d, energy_kwh=float(daily[d, 0]),
                       release_h=d * 24, deadline_h=d * 24 + 23,
                       pmax_kw=cfg["job_pmax_kw"], priority_class="B")
                  for d in range(n_days)]
    return dict(n=n, hod=hod, tou_segment=tou_segment_of(hod),
                price=cols["price"], grid_carbon=cols["grid_carbon"],
                solar=cols["solar"], wind=cols["wind"], green=cols["solar"] + cols["wind"],
                rigid_load=cols["rigid_load"],
                elastic_total_kwh=float(daily[0, 0]), task_attrs=task_attrs)


def apply_scenario(data, cfg, scenario):
    """Scale the nominal series. No random draw, so scenarios are paired."""
    sc = SCENARIOS[scenario]
    mult = np.ones(data["n"])
    for name, value in sc["price_mult"].items():
        mult[data["tou_segment"] == name] = value
    out = dict(data)
    out["price"] = data["price"] * mult
    out["solar"] = data["solar"] * sc["solar_mult"]
    out["wind"] = data["wind"] * sc["wind_mult"]
    out["green"] = out["solar"] + out["wind"]
    return out


def build_inputs(cfg, scenario="base", seed=None):
    """Synthesise then scale: the one call every experiment starts from."""
    return apply_scenario(synthesize_inputs(cfg, seed), cfg, scenario)
