"""The web engine must reproduce the published reference numbers exactly.

Reference values are read from data/research_results_gridflex.csv and
data/verification_summary.json (produced by the MATLAB/Python reference code).
"""
import json

import numpy as np
import pytest

from app.engine.benchmark import load_benchmark
from app.engine.quantum import PUBLISHED_ANGLES, assignment_hours, cached_qubo, qaoa_statistics
from app.engine.scenarios import SCENARIOS, run_scenario
from app.services.simulation import published_table

from .conftest import DATA

COLS = {
    "grid_energy_MWh": "grid_energy_MWh",
    "operational_CO2_t": "operational_CO2_t",
    "renewable_utilization_pct": "renewable_utilization_pct",
    "average_workload_delay_h": "average_workload_delay_h",
    "jobs_shifted_pct": "jobs_shifted_pct",
    "violation_energy_MWh": "violation_energy_MWh",
}


@pytest.fixture(scope="module")
def solved():
    b = load_benchmark(str(DATA))
    return {k: run_scenario(b, k) for k in SCENARIOS}


@pytest.mark.parametrize("key", list(SCENARIOS))
def test_scenario_matches_published_row(solved, key):
    pub = published_table(str(DATA))[key]
    res = solved[key]
    assert res.feasible
    assert res.connection_capacity_MW == pytest.approx(pub["connection_capacity_MW"], rel=1e-6)
    for col, metric in COLS.items():
        assert res.metrics[metric] == pytest.approx(pub[col], rel=1e-5, abs=1e-6), col


def test_hydrogen_bookkeeping(solved):
    summary = json.loads((DATA / "verification_summary.json").read_text())
    assert solved["R1"].metrics["curtailed_MWh"] == pytest.approx(summary["R1_curt"], rel=1e-6)
    assert solved["R2"].metrics["electrolyser_MWh"] == pytest.approx(summary["R2_EL"], rel=1e-6)
    assert solved["R2"].metrics["fuel_cell_MWh"] == pytest.approx(summary["R2_FC"], rel=1e-6)
    for k in ("R2", "R3", "R4", "R5"):
        assert solved[k].metrics["h2_terminal_MWh"] == pytest.approx(5.0, abs=1e-6)


def test_r4_infeasible_without_flexibility():
    from app.engine.dispatch import solve_dispatch
    b = load_benchmark(str(DATA))
    assert solve_dispatch(b, b.cap_nonfirm, use_h2=True, flexible=False) is None


def test_qubo_and_qaoa_match_published():
    summary = json.loads((DATA / "verification_summary.json").read_text())
    q = cached_qubo(str(DATA))
    assert 2 ** q.n == summary["n_states"] and len(q.feasible) == summary["n_feasible"]
    assert q.energies[q.best] == pytest.approx(summary["best_energy"], rel=1e-9)
    assert assignment_hours(q, q.best) == summary["assignment_hours"]
    for p in (1, 2):
        s = qaoa_statistics(q, PUBLISHED_ANGLES[p], p)
        ref = summary["qaoa"][str(p)]
        assert s["feasible_mass_pct"] == pytest.approx(ref["feas_mass"], rel=1e-9)
        assert s["optimum_probability_pct"] == pytest.approx(ref["p_opt"], rel=1e-9)
        assert s["expected_cost"] == pytest.approx(ref["exp"], rel=1e-9)
        assert s["most_probable_is_optimum"] and s["optimality_gap"] == 0.0
        assert np.isclose(s["probabilities"].sum(), 1.0)
