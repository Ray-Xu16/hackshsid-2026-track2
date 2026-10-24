"""Contract tests: the properties the whole project depends on.

    python tests/test_contract.py          # no pytest needed
    pytest tests/                          # also works

Each test is a claim made in the paper, reduced to the smallest series that can
falsify it (30 days instead of 365 keeps the run under a second).
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments import run_bench
from track2 import inputs, metrics, strategies, validation
from track2.config import CONFIG, SCENARIOS

CFG = dict(CONFIG, n_days=30)          # short horizon: the claims are structural


def dataset(scenario="base"):
    return validation.attach_snapshot(inputs.build_inputs(CFG, scenario, CFG["seed"]))


def test_bench_and_program_agree_on_s0():
    """The bench summary and the program table must report the same S0 row."""
    _, summary, _, _, _ = run_bench.build_scenario("base", CFG, CFG["seed"])
    data = dataset()
    res, rows, cfg = strategies.run_flat(data, CFG)
    m = metrics.evaluate(data, res, rows, cfg)
    assert abs(summary["annual_cost"] - m["annual_cost"]) < 1.0
    assert abs(summary["annual_carbon"] - m["annual_carbon"]) < 0.1


def test_s0_never_beats_the_bound():
    """The relaxed bound must survive every strategy, or it is not a bound."""
    data = dataset()
    lb = metrics.lower_bound(data, CFG)
    for tag, (res, rows, cfg) in (("S0", strategies.run_flat(data, CFG)),
                                  ("S1", strategies.run_shifted(data, CFG, 0.2, False)),
                                  ("S2", strategies.run_shifted(data, CFG, 0.2, True))):
        m = metrics.evaluate(data, res, rows, cfg)
        assert m["annual_cost"] >= lb["lb_cost"] - 1e-6, tag
        assert m["annual_carbon"] >= lb["lb_carbon"] - 1e-6, tag


def test_every_run_keeps_sla_and_soc():
    """DoD: SLA reported (and not violated), SOC inside limits, energy balanced."""
    data = dataset()
    for tag, (res, rows, cfg) in (("S0", strategies.run_flat(data, CFG)),
                                  ("S1", strategies.run_shifted(data, CFG, 0.2, False)),
                                  ("S2", strategies.run_shifted(data, CFG, 0.2, True))):
        checks = validation.check_invariants(data, res, rows, cfg, tag)
        failed = [c[0] for c in checks if not c[1]]
        assert not failed, failed
        assert all(r["on_time"] for r in rows), tag


def test_cost_and_carbon_are_energy_times_price():
    """The unit convention: cost = sum(grid_energy * price * dt), no x1000 step."""
    data = dataset()
    res, rows, cfg = strategies.run_shifted(data, CFG, 0.2, True)
    m = metrics.evaluate(data, res, rows, cfg)
    assert np.isclose(m["annual_cost"], np.sum(res["grid_energy"] * data["price"] * CFG["dt_h"]))
    assert np.isclose(m["annual_carbon"],
                      np.sum(res["grid_energy"] * data["grid_carbon"]) * CFG["dt_h"] / 1e6)


def test_scenarios_are_paired():
    """Only the knobs move: weather and load are identical across scenarios."""
    base, high = dataset("base"), dataset("high_price")
    assert np.array_equal(base["green"], high["green"])
    assert np.array_equal(base["rigid_load"], high["rigid_load"])
    assert not np.array_equal(base["price"], high["price"])


def test_s1_is_s2_with_the_battery_off():
    """S1 must be the same placement rule, so the S2-S1 gap is storage alone."""
    data = dataset()
    s1 = strategies.run_shifted(data, CFG, 0.2, False)[0]
    s2 = strategies.run_shifted(data, CFG, 0.2, True)[0]
    assert np.all(s1["charge"] == 0) and np.all(s1["discharge"] == 0)
    assert np.array_equal(s1["elastic"], s2["elastic"])


def test_green_accounting_closes():
    """green_used + green_curtailed == green, for every scenario and strategy."""
    for name in SCENARIOS:
        data, cfg = dataset(name), CFG
        for res in (strategies.run_flat(data, cfg)[0],
                    strategies.run_shifted(data, cfg, 0.2, True)[0]):
            assert np.allclose(res["green_used"] + res["green_curtailed"], data["green"])


def test_dispatch_does_not_mutate_inputs():
    """AB rule: the input series are frozen before any strategy runs."""
    data = dataset()
    strategies.run_shifted(data, CFG, 0.2, True)
    strategies.run_flat(data, CFG)
    assert validation.ab_inputs_shared(data)


def main():
    tests = [(k, v) for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print("ok    %s" % name)
        except AssertionError as exc:
            failed += 1
            print("FAIL  %s  %s" % (name, exc))
    print("\n%d/%d passed" % (len(tests) - failed, len(tests)))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
