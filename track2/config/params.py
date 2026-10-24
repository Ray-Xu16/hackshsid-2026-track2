"""All numeric parameters of the model, in one dict. Nothing else holds numbers.

Every value is a placeholder that task D2 replaces with anchored data (TOU
tariff catalogue, grid emission factors, PVWatts / ERA5 profiles, MLPerf-based
workload split, Hithium datasheet storage parameters). Because they live here
and nowhere else, "what changed" is always a diff of this one file.

Units: price yuan/kWh; grid_carbon gCO2e/kWh; power kW; energy kWh; dt = 1 h,
so a power of x kW held for one hour equals x kWh.
"""

CONFIG = dict(
    n_days=365, dt_h=1.0, seed=42,
    # TOU price (yuan/kWh). Part 1 Section 1.1 row 1: peak / flat / valley
    # segments plus noise; the evening sharp-peak tier is the sub-peak of the
    # peak segment (declared in the data dictionary of the bench).
    price_valley=0.30, price_flat=0.60, price_peak=1.00, price_sharp=1.40,
    price_noise_sd=0.03,
    # grid carbon intensity (gCO2e/kWh). Part 1 Section 1.1 row 2.
    carbon_valley=640.0, carbon_midday=430.0, carbon_noise_sd=20.0,
    carbon_floor=300.0, carbon_ceil=800.0,
    # green supply (kW). Part 1 Section 1.1 rows 3-4.
    solar_peak_kw=800.0, solar_cloud_sd=0.25, solar_cloud_floor=0.20,
    wind_mean_kw=200.0, wind_std_kw=120.0,
    # workload (kW, kWh/day). Part 1 Section 1.1 rows 5-8.
    rigid_base_kw=500.0, rigid_amp_kw=150.0, rigid_noise_sd=30.0, rigid_floor_kw=100.0,
    elastic_total_kwh=6000.0, job_pmax_kw=900.0, throttle_frac=0.35,
    # battery: capacity, max power, efficiency, state-of-charge limits.
    battery=dict(capacity_mwh=2.0, power_mw=1.0, eta_roundtrip=0.90,
                 soc_min=0.10, soc_max=1.00, soc_init=0.50),
    # objective weight and online settings. Part 1 Section 1.1 rows 9-10.
    lam=0.70, horizon_h=24, forecast_noise=0.15,
    # facility overhead: IT power != total power. Part 1 Section 1.2 row 9.
    pue=1.20,
)
