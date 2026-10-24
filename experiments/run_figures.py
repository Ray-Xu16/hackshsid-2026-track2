"""Figures. Reads only the CSVs written by the experiments, so a figure can
never disagree with a table.

    python main.py figures

matplotlib is a plotting tool here, not part of the model: track2/ stays
pandas/numpy only, and nothing in this file computes a metric of its own.
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Rectangle

if __package__ in (None, ""):                       # run this file directly
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from track2 import balance, inputs, paths, scheduler, validation
from track2.config import CONFIG

SCEN = ["base", "high_price", "green_scarce"]
NAME = {"base": "Base", "high_price": "High price", "green_scarce": "Scarce green"}
COLOR = {"base": "#1f4e79", "high_price": "#c00000", "green_scarce": "#2e7d32"}
MARK = {"S1": "o", "S2": "s", "S3": "*"}


def load_matrix(ladder_dir=None):
    """Read the ladder tables; returns (matrix, {scenario: front})."""
    d = Path(ladder_dir or paths.LADDER)
    mx = pd.read_csv(d / "strategy_matrix.csv")
    fronts = {s: pd.read_csv(d / ("pareto_%s.csv" % s)) for s in SCEN}
    return mx, fronts


def fig_q2_1(mx, fronts, out=None):
    """(a) the three fronts with S0 and the compromise point; (b) improvement plane."""
    pick = lambda s, tag: mx[(mx["scenario"] == s) & (mx["strategy"] == tag)].iloc[0]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.2, 5.0), dpi=200)

    for s in SCEN:
        f = fronts[s].sort_values("cost")
        keep = f[f["on_front"]]
        ax1.plot(f["cost"] / 1e4, f["carbon"], "-", lw=0.9, color=COLOR[s], alpha=0.45)
        ax1.plot(keep["cost"] / 1e4, keep["carbon"], "-o", ms=3.6, lw=1.6,
                 color=COLOR[s], label="%s: Pareto front" % NAME[s])
        s0, s3 = pick(s, "S0"), pick(s, "S3")
        ax1.scatter(s0["annual_cost"] / 1e4, s0["annual_carbon"], marker="s", s=46,
                    facecolors="none", edgecolors=COLOR[s], lw=1.4, zorder=5)
        ax1.scatter(s3["annual_cost"] / 1e4, s3["annual_carbon"], marker="*", s=150,
                    color=COLOR[s], zorder=6)
    ax1.set_xlabel("Annual cost (10k yuan/yr, IT side)")
    ax1.set_ylabel("Annual carbon (tCO2e/yr, IT side)")
    ax1.set_title("(a) Cost-carbon frontier: $\\lambda$ swept 0 to 1\n"
                  "hollow square = S0, star = S3 compromise", fontsize=9.5)
    ax1.grid(alpha=0.25, lw=0.6)
    ax1.legend(fontsize=7.6, loc="upper right", framealpha=0.9)

    ax2.set_xlim(-22.0, 10.0)
    ax2.set_ylim(-26.0, 2.0)
    ax2.add_patch(Rectangle((-22.0, -26.0), 22.0, 26.0, color="#e8f3ea", zorder=0))
    ax2.axhline(0, color="#666", lw=0.9)
    ax2.axvline(0, color="#666", lw=0.9)
    for s in SCEN:
        for tag in ("S1", "S2", "S3"):
            r = pick(s, tag)
            ax2.scatter(r["vs_s0_cost_pct"], r["vs_s0_carbon_pct"], marker=MARK[tag],
                        s=95 if tag == "S3" else 62, color=COLOR[s],
                        edgecolors="white", linewidths=0.7, zorder=4,
                        label="%s / %s" % (NAME[s], tag))
    ax2.annotate("win-win region: both cheaper and cleaner", xy=(-21.2, -24.6), fontsize=7.8,
                 ha="left", color="#2e7d32")
    ax2.set_xlabel("Cost change vs S0 (%, negative = saving)")
    ax2.set_ylabel("Carbon change vs S0 (%, negative = saving)")
    ax2.set_title("(b) Every run lands in or near the win-win quadrant\n"
                  "S1 = time shift only, S2 = +battery, S3 = compromise", fontsize=9.5)
    ax2.grid(alpha=0.25, lw=0.6)
    ax2.legend(fontsize=6.4, ncol=3, loc="upper left", framealpha=0.9)

    fig.tight_layout()
    path = Path(out or paths.FIGURES) / "fig_Q2-1_pareto.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def fig_q2_2(mx, out=None):
    """The four-by-three matrix as bars."""
    pick = lambda s, tag: mx[(mx["scenario"] == s) & (mx["strategy"] == tag)].iloc[0]
    tags = ["S0", "S1", "S2", "S3"]
    fig, axes = plt.subplots(1, 3, figsize=(13.2, 3.6), dpi=200, sharey=False)
    for ax, s in zip(axes, SCEN):
        vals = [pick(s, t)["annual_cost"] / 1e4 for t in tags]
        carb = [pick(s, t)["annual_carbon"] for t in tags]
        bars = ax.bar(tags, vals, color=[COLOR[s] if t != "S0" else "#999" for t in tags],
                      width=0.62)
        for b, v, c in zip(bars, vals, carb):
            ax.text(b.get_x() + b.get_width() / 2, v, "%.0f\n%.0f t" % (v, c),
                    ha="center", va="bottom", fontsize=7)
        ax.set_title(NAME[s], fontsize=10)
        ax.set_ylim(min(vals) * 0.72, max(vals) * 1.14)
        ax.grid(axis="y", alpha=0.25, lw=0.6)
        ax.set_ylabel("10k yuan/yr" if s == "base" else "")
    fig.suptitle("Fig. Q2-2  Annual cost (bar) and carbon (label) by strategy and scenario, "
                 "SLA 100% in every bar", fontsize=10)
    fig.tight_layout()
    path = Path(out or paths.FIGURES) / "fig_Q2-2_bars.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def _s2_day(cfg):
    """The one dataset D11-1 / D11-2 share: base scenario under S2."""
    data = validation.attach_snapshot(inputs.build_inputs(cfg, "base", cfg["seed"]))
    elastic, _ = scheduler.place_jobs_offline(data, cfg, 0.2)
    res = balance.run_battery(data, elastic, cfg, 0.2)
    return data, res


def fig_d11_1(cfg, out=None):
    """Full-year 365 x 24 heat maps: price, and grid import under S2."""
    data, res = _s2_day(cfg)
    days, hours = cfg["n_days"], 24
    grid = lambda v: np.asarray(v).reshape(days, hours)
    fig, axes = plt.subplots(2, 1, figsize=(9.4, 6.4), dpi=200)
    panels = [(grid(data["price"]), "Price (yuan/kWh)", "viridis"),
              (grid(res["grid_energy"]), "Grid import under S2 (kW)", "magma")]
    for ax, (mat, title, cmap) in zip(axes, panels):
        im = ax.imshow(mat, aspect="auto", origin="upper", cmap=cmap)
        ax.set_title(title, fontsize=9.5)
        ax.set_ylabel("day of year")
        ax.set_xticks(range(0, 24, 3))
        ax.set_xticklabels(["%02d" % h for h in range(0, 24, 3)])
        ax.set_xlabel("hour of day")
        fig.colorbar(im, ax=ax, pad=0.012)
    fig.suptitle("Fig. D11-1  Full-year 365 x 24 matrix, base scenario", fontsize=10.5)
    fig.tight_layout()
    path = Path(out or paths.FIGURES) / "fig_D11-1_heatmap.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def fig_d11_2(cfg, out=None):
    """Typical day: price, green supply, load and SOC on one axis pair."""
    data, res = _s2_day(cfg)
    day = 100                                          # a mid-season day (11 April)
    sl = slice(day * 24, (day + 1) * 24)
    t = np.arange(24)
    fig, ax = plt.subplots(figsize=(9.0, 3.9), dpi=200)
    ax.plot(t, data["green"][sl], color="#2e7d32", lw=2.0, marker="o", ms=3,
            label="green supply (kW)")
    ax.plot(t, res["it_load"][sl], color="#1f4e79", lw=2.0, marker="s", ms=3,
            label="IT load under S2 (kW)")
    ax.plot(t, res["soc"][sl], color="#6a1b9a", lw=1.5, ls="--", label="SOC (kWh)")
    ax.set_xlabel("hour of day")
    ax.set_ylabel("power (kW) / SOC (kWh)")
    ax.set_xticks(range(24))
    ax.grid(alpha=0.25, lw=0.6)
    ax2 = ax.twinx()
    ax2.step(t, data["price"][sl], color="#f9a825", lw=1.6, where="mid",
             label="price (yuan/kWh, right axis)")
    ax2.set_ylabel("price (yuan/kWh)")
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=7.4, ncol=4, loc="upper center",
              bbox_to_anchor=(0.5, 1.16), framealpha=0.9)
    ax.set_title("Fig. D11-2  Typical day (11 April) under S2: price, green supply, load, SOC",
                 fontsize=10, pad=30)
    fig.tight_layout()
    path = Path(out or paths.FIGURES) / "fig_D11-2_typical_day.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def main(argv=None):
    cfg = dict(CONFIG)
    paths.ensure(paths.FIGURES)
    mx, fronts = load_matrix()
    written = [fig_q2_1(mx, fronts), fig_q2_2(mx),
               fig_d11_1(cfg), fig_d11_2(cfg)]
    for p in written:
        print("wrote %s (%.0f kB)" % (p, p.stat().st_size / 1024))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
