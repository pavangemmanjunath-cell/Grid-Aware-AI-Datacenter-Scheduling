"""Internal-consistency checks on the published scenario table and QAOA summary.

Nothing here re-solves the model.  Each test checks an arithmetic relation that
the published numbers must satisfy, or recomputes a quantity that follows directly
from the benchmark without optimisation (the grid-only reference R0).
"""
import itertools

import numpy as np
import pytest

SCEN = ("R0", "R1", "R2", "R3", "R4", "R5")


def test_all_scenarios_present(results):
    assert tuple(results) == SCEN


def test_reference_r0_follows_from_benchmark(bench, results):
    load = bench.fixed_ai_load_MW + bench.baseline_flexible_load_MW
    r0 = results["R0"]
    assert r0["grid_energy_MWh"] == pytest.approx(load.sum(), rel=1e-9)
    assert r0["connection_capacity_MW"] == pytest.approx(load.max(), rel=1e-9)
    assert r0["operational_CO2_t"] == pytest.approx((load * bench.grid_carbon_kgCO2_per_MWh).sum() / 1000, rel=1e-9)


def test_capacity_reduction_is_relative_to_r0(results):
    c0 = results["R0"]["connection_capacity_MW"]
    for s in SCEN:
        red = 100 * (1 - results[s]["connection_capacity_MW"] / c0)
        assert results[s]["capacity_reduction_pct"] == pytest.approx(red, abs=1e-6)


def test_headline_figures(results):
    cap = {s: results[s]["connection_capacity_MW"] for s in SCEN}
    assert round(cap["R0"], 2) == 15.16
    assert round(cap["R3"], 2) == 8.94
    assert round(results["R3"]["capacity_reduction_pct"], 1) == 41.0
    # sequential (not factorial) decomposition quoted in the paper
    assert round(cap["R0"] - cap["R1"], 2) == 2.58
    assert round(cap["R1"] - cap["R2"], 2) == 2.00
    assert round(cap["R2"] - cap["R3"], 2) == 1.64


def test_envelopes_and_violation(results, bench):
    assert results["R4"]["connection_capacity_MW"] <= bench.nonfirm_connection_cap_MW.max() + 1e-9
    assert results["R5"]["connection_capacity_MW"] <= bench.phased_connection_cap_MW.max() + 1e-9
    for s in SCEN:
        assert results[s]["violation_energy_MWh"] == 0


def test_shifted_share_is_a_whole_number_of_bundles(results):
    for s in SCEN:
        n = results[s]["jobs_shifted_pct"] / 100 * 28
        assert n == pytest.approx(round(n), abs=1e-6), s
    assert round(results["R3"]["jobs_shifted_pct"] / 100 * 28) == 3
    assert round(results["R4"]["jobs_shifted_pct"] / 100 * 28) == 6
    assert round(results["R5"]["jobs_shifted_pct"] / 100 * 28) == 1


def test_average_delay_uses_candidate_offsets(results):
    """Mean delay x 28 must be a sum of offsets drawn from {0, 3, 7}."""
    reachable = {sum(c) for k in range(0, 8) for c in itertools.combinations_with_replacement((3, 7), k)}
    for s in ("R3", "R4", "R5"):
        total = results[s]["average_workload_delay_h"] * 28
        assert round(total) in reachable and total == pytest.approx(round(total), abs=1e-6), s


def test_hydrogen_inventory_closes(summary):
    """Cyclic inventory: hydrogen produced equals hydrogen consumed."""
    produced = 0.72 * summary["R2_EL"]
    consumed = summary["R2_FC"] / 0.55
    assert produced == pytest.approx(consumed, rel=1e-6)
    # electrolyser can only absorb what would otherwise be curtailed
    assert summary["R2_EL"] <= summary["R1_curt"] + 1e-9


def test_qubo_search_space(summary):
    assert summary["n_states"] == 2 ** 12
    assert summary["n_feasible"] == 3 ** 4  # one slot per bundle, 4 bundles x 3 slots
    for hour, base in zip(summary["assignment_hours"], summary["baseline_hours"]):
        assert hour - base in (0, 3, 7)


def test_qaoa_statistics(summary):
    q1, q2 = summary["qaoa"]["1"], summary["qaoa"]["2"]
    assert round(q1["feas_mass"], 2) == 27.16 and round(q1["p_opt"], 3) == 0.392
    assert round(q2["feas_mass"], 2) == 67.13 and round(q2["p_opt"], 3) == 1.042
    for q in (q1, q2):
        assert q["match"] is True and q["gap"] == 0.0
        assert 0 < q["p_opt"] <= q["feas_mass"] <= 100


def test_fallback_capacities_match_milp(results):
    """The toolbox-free MATLAB path reproduces all six capacities (benchmarks/results).

    The CSV predates the terminal-inventory fix; capacities were unaffected by it, which the
    recorded 2026-11-21 run (matlab_R2026a_fallback_2026-11-21.txt) confirms.
    """
    import csv
    from conftest import REPO
    with open(REPO / "benchmarks" / "results" / "research_results_gridflex_FALLBACK.csv", newline="") as fh:
        fb = {r["scenario"].split()[0]: float(r["connection_capacity_MW"]) for r in csv.DictReader(fh)}
    run = dict(line.strip().split("=", 1) for line in
               (REPO / "benchmarks" / "results" / "matlab_R2026a_fallback_2026-11-21.txt").read_text().splitlines()
               if "=" in line)
    assert run["status"] == "COMPLETED" and run["solver_used"] == "fallback"
    for s in SCEN:
        assert fb[s] == pytest.approx(results[s]["connection_capacity_MW"], abs=1e-3), s
        assert float(run[f"{s}_conn_MW"]) == pytest.approx(results[s]["connection_capacity_MW"], abs=1e-6), s
    assert np.isfinite(list(fb.values())).all()
