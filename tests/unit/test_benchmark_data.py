"""Structural checks on the shipped 168-hour benchmark and bundle table.

These mirror the validation gate in matlab/qh2dc_load_benchmark.m and the
configuration in matlab/qh2dc_config.m, so a corrupted or regenerated data file
is caught before any optimisation runs.
"""
import numpy as np
import pytest

EXPECTED_COLUMNS = [
    "hour_index", "day", "hour_of_day", "fixed_ai_load_MW", "baseline_flexible_load_MW",
    "total_baseline_load_MW", "solar_MW", "wind_MW", "renewable_MW",
    "grid_carbon_kgCO2_per_MWh", "nonfirm_connection_cap_MW", "phased_connection_cap_MW",
    "nonfirm_constraint_event",
]


def test_schema_and_horizon(bench):
    assert list(bench.columns) == EXPECTED_COLUMNS
    assert len(bench) == 168
    assert bench.hour_index.tolist() == list(range(168))
    assert (bench.day == bench.hour_index // 24).all()
    assert (bench.hour_of_day == bench.hour_index % 24).all()
    assert not bench.isna().any().any()


def test_additive_identities(bench):
    # same gate as qh2dc_load_benchmark.m
    np.testing.assert_allclose(bench.total_baseline_load_MW,
                               bench.fixed_ai_load_MW + bench.baseline_flexible_load_MW, atol=1e-9)
    np.testing.assert_allclose(bench.renewable_MW, bench.solar_MW + bench.wind_MW, atol=1e-9)


def test_physical_bounds(bench):
    for col in ("fixed_ai_load_MW", "baseline_flexible_load_MW", "solar_MW", "wind_MW"):
        assert (bench[col] >= 0).all(), col
    # solar only inside 07:00-18:00 (qh2dc_build_benchmark.m)
    night = bench[(bench.hour_of_day < 7) | (bench.hour_of_day > 18)]
    assert (night.solar_MW == 0).all()
    assert bench.grid_carbon_kgCO2_per_MWh.min() >= 180.0  # generator floor


def test_documented_ranges(bench):
    """Ranges quoted in data/README.md, read back from the file."""
    assert bench.fixed_ai_load_MW.min() == pytest.approx(6.508, abs=1e-3)
    assert bench.fixed_ai_load_MW.max() == pytest.approx(7.982, abs=1e-3)
    assert bench.solar_MW.max() == pytest.approx(8.480, abs=1e-3)
    assert bench.wind_MW.min() == pytest.approx(0.860, abs=1e-3)
    assert bench.wind_MW.max() == pytest.approx(4.661, abs=1e-3)
    assert bench.renewable_MW.sum() == pytest.approx(760.42, abs=0.01)


def test_nonfirm_envelope(bench):
    window = bench.hour_of_day.between(8, 14)
    assert (bench.loc[window, "nonfirm_connection_cap_MW"] == 6.5).all()
    assert (bench.loc[~window, "nonfirm_connection_cap_MW"] == 10.7).all()
    assert (bench.nonfirm_constraint_event == window.astype(int)).all()
    assert bench.nonfirm_constraint_event.sum() == 49  # 7 h x 7 days


def test_phased_envelope(bench):
    stages = bench.phased_connection_cap_MW.values.reshape(3, 56)
    for stage, level in zip(stages, (8.7, 9.7, 10.7)):
        assert (stage == level).all()


def test_bundle_table(bench, jobs):
    flex_hours = np.where(bench.baseline_flexible_load_MW > 0)[0]
    assert len(jobs) == 28 == len(flex_hours)
    assert jobs.baseline_hour.tolist() == flex_hours.tolist()
    assert sorted(set(jobs.baseline_hour % 24)) == [6, 8, 11, 14]
    np.testing.assert_allclose(jobs.energy_MWh, bench.baseline_flexible_load_MW.values[flex_hours])
    for _, j in jobs.iterrows():
        assert [j.cand_1, j.cand_2, j.cand_3] == [j.baseline_hour, j.baseline_hour + 3, j.baseline_hour + 7]
        assert j.release_h == j.baseline_hour and j.deadline_h == j.cand_3
