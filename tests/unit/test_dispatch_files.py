"""The exported hourly dispatch must add up to the published scenario table."""
import numpy as np
import pandas as pd
import pytest

from conftest import DATA

SCEN = ("R0", "R1", "R2", "R3", "R4", "R5")


@pytest.fixture(scope="module")
def dispatch():
    return {k: pd.read_csv(DATA / "dispatch" / f"research_dispatch_{k}.csv") for k in SCEN}


@pytest.fixture(scope="module")
def placement():
    return pd.read_csv(DATA / "dispatch" / "research_job_placement.csv")


def test_shape(dispatch):
    for k, d in dispatch.items():
        assert len(d) == 168 and d.hour.tolist() == list(range(168)), k


def test_weekly_totals_match_published_table(dispatch, results, bench):
    for k, d in dispatch.items():
        r = results[k]
        assert d.grid_import_MW.sum() == pytest.approx(r["grid_energy_MWh"], rel=1e-5), k
        co2 = (d.grid_import_MW * bench.grid_carbon_kgCO2_per_MWh).sum() / 1000
        assert co2 == pytest.approx(r["operational_CO2_t"], rel=1e-5), k
        if k != "R0":
            util = 100 * (1 - d.curtailment_MW.sum() / bench.renewable_MW.sum())
            assert util == pytest.approx(r["renewable_utilization_pct"], abs=1e-4), k


def test_capacity_and_envelope(dispatch, results):
    assert dispatch["R0"].grid_import_MW.max() == pytest.approx(results["R0"]["connection_capacity_MW"], abs=1e-6)  # CSV holds 6 dp
    for k in ("R2", "R3", "R4", "R5"):
        d = dispatch[k]
        assert (d.grid_import_MW <= d.envelope_MW + 1e-6).all(), k
    for k in ("R4", "R5"):
        assert dispatch[k].grid_import_MW.max() == pytest.approx(results[k]["connection_capacity_MW"], abs=1e-5)
    for k in ("R2", "R3"):
        assert dispatch[k].envelope_MW.iloc[0] == pytest.approx(results[k]["connection_capacity_MW"], abs=1e-6)
    assert dispatch["R0"].envelope_MW.isna().all() and dispatch["R1"].envelope_MW.isna().all()


def test_bus_balance_every_hour(dispatch, bench):
    for k, d in dispatch.items():
        ren = bench.renewable_MW if k != "R0" else 0 * bench.renewable_MW
        residual = (d.grid_import_MW + d.fuel_cell_MW + ren) - (bench.fixed_ai_load_MW + d.flex_load_MW + d.electrolyser_MW + d.curtailment_MW)
        assert np.abs(residual).max() < 1e-5, k


def test_job_placement_matches_table(placement, results):
    for k in SCEN:
        p = placement[placement.scenario == k]
        assert len(p) == 28
        assert (p.chosen_hour - p.baseline_hour == p.delay_h).all()
        assert set(p.delay_h) <= {0, 3, 7}
        assert 100 * (p.delay_h > 0).mean() == pytest.approx(results[k]["jobs_shifted_pct"], abs=1e-6), k
        assert p.delay_h.mean() == pytest.approx(results[k]["average_workload_delay_h"], abs=1e-6), k
