"""HTTP contract tests for /api/v1."""
import time

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture(scope="module")
def client():
    with TestClient(create_app()) as c:
        yield c


def test_health(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200 and r.json()["benchmark_hours"] == 168
    assert "x-request-id" in r.headers


def test_openapi_document(client):
    spec = client.get("/openapi.json").json()
    assert spec["info"]["license"]["name"] == "Apache-2.0"
    assert "/api/v1/scenarios/{key}" in spec["paths"]


def test_benchmark_is_labelled_synthetic(client):
    body = client.get("/api/v1/benchmark").json()
    assert body["synthetic"] is True and len(body["fixed_load_MW"]) == 168 and len(body["bundles"]) == 28


def test_scenarios_list_and_detail(client):
    rows = client.get("/api/v1/scenarios").json()
    assert [r["key"] for r in rows] == ["R0", "R1", "R2", "R3", "R4", "R5"]
    r3 = client.get("/api/v1/scenarios/r3").json()
    assert round(r3["connection_capacity_MW"], 2) == 8.94
    assert len(r3["series"]["grid_import_MW"]) == 168
    assert max(r3["series"]["grid_import_MW"]) <= r3["connection_capacity_MW"] + 1e-4  # series rounded to 4 dp
    assert client.get("/api/v1/scenarios/R9").status_code == 404


def test_datasets_are_not_claimed_as_sources(client):
    rows = client.get("/api/v1/datasets").json()
    assert len(rows) >= 5 and not any(r["used_in_published_results"] for r in rows)


def test_quantum_problem_and_published_angles(client):
    prob = client.get("/api/v1/quantum/problem").json()
    assert prob["qubits"] == 12 and len(prob["feasible_states"]) == 81 and len(prob["energies"]) == 4096
    r = client.post("/api/v1/quantum/evaluate", json={"p": 2, "angles": prob["published_angles"]["2"]})
    assert r.status_code == 200
    assert round(r.json()["feasible_mass_pct"], 2) == 67.13 and r.json()["most_probable_is_optimum"]


def test_quantum_validation_errors(client):
    assert client.post("/api/v1/quantum/evaluate", json={"p": 2, "angles": [0.1, 0.2]}).status_code == 422


def test_whatif_validation(client):
    bad = client.post("/api/v1/simulations", json={"h2_init_mwh": 30, "h2_max_mwh": 20})
    assert bad.status_code == 422
    assert client.post("/api/v1/simulations", json={"electrolyser_mw": -1}).status_code == 422


def _wait(client, job_id, timeout=120):
    t0 = time.time()
    while time.time() - t0 < timeout:
        job = client.get(f"/api/v1/simulations/{job_id}").json()
        if job["status"] in ("succeeded", "failed"):
            return job
        time.sleep(0.2)
    raise AssertionError("simulation did not finish")


def test_whatif_defaults_reproduce_r4_and_are_labelled_exploratory(client):
    r = client.post("/api/v1/simulations", json={"mode": "nonfirm"})
    assert r.status_code == 202
    job = _wait(client, r.json()["id"])
    assert job["status"] == "succeeded", job["error"]
    res = job["result"]
    assert res["exploratory"] is True and "NOT results of the paper" in res["disclaimer"]
    assert res["connection_capacity_MW"] == pytest.approx(10.7, abs=1e-6)
    assert res["metrics"]["jobs_shifted_pct"] == pytest.approx(21.428571, abs=1e-4)


def test_whatif_infeasible_case_is_reported(client):
    # no hydrogen, no room in the envelope: the non-firm cut cannot be met
    r = client.post("/api/v1/simulations", json={"mode": "nonfirm", "electrolyser_mw": 0, "fuel_cell_mw": 0,
                                                 "nonfirm_reduced_mw": 2.0})
    job = _wait(client, r.json()["id"])
    assert job["status"] == "succeeded" and job["result"]["feasible"] is False


@pytest.mark.parametrize("payload,key", [
    ({"mode": "min-uniform-flexible"}, "R3"),
    ({"mode": "min-uniform"}, "R2"),
    ({"mode": "phased"}, "R5"),
])
def test_whatif_defaults_reproduce_published_scenarios(client, payload, key):
    from app.services.simulation import published_table

    from .conftest import DATA
    job = _wait(client, client.post("/api/v1/simulations", json=payload).json()["id"])
    assert job["status"] == "succeeded", job["error"]
    pub = published_table(str(DATA))[key]
    assert job["result"]["connection_capacity_MW"] == pytest.approx(pub["connection_capacity_MW"], abs=1e-5)
    assert job["result"]["metrics"]["operational_CO2_t"] == pytest.approx(pub["operational_CO2_t"], rel=1e-5)


def test_whatif_nonfirm_without_flexibility_is_infeasible(client):
    job = _wait(client, client.post("/api/v1/simulations", json={"mode": "nonfirm", "workload_flexibility": False}).json()["id"])
    assert job["status"] == "succeeded" and job["result"]["feasible"] is False


def test_whatif_custom_offsets_and_scales_validate(client):
    assert client.post("/api/v1/simulations", json={"candidate_offsets_h": [3, 7]}).status_code == 422
    assert client.post("/api/v1/simulations", json={"candidate_offsets_h": [0, 7, 3]}).status_code == 422
    job = _wait(client, client.post("/api/v1/simulations", json={"candidate_offsets_h": [0, 2, 4, 6], "solar_scale": 1.5,
                                                                  "wind_scale": 0.5, "demand_scale": 1.3}).json()["id"])
    assert job["status"] == "succeeded", job["error"]
    if job["result"]["feasible"]:
        assert set(job["result"]["bundle_delays_h"]) <= {0, 2, 4, 6}


def test_no_renewables_does_not_break_job_endpoints(client):
    job = _wait(client, client.post("/api/v1/simulations", json={"solar_scale": 0, "wind_scale": 0, "mode": "min-uniform"}).json()["id"])
    assert job["status"] == "succeeded", job["error"]
    assert job["result"]["metrics"]["renewable_utilization_pct"] == 0.0
    assert client.get("/api/v1/simulations").status_code == 200


def test_quantum_rejects_nan_and_oversized_budgets(client):
    r = client.post("/api/v1/quantum/evaluate", content='{"p": 1, "angles": [NaN, 0]}', headers={"content-type": "application/json"})
    assert r.status_code == 422
    assert client.post("/api/v1/quantum/optimise", json={"p": 1, "restarts": 20, "max_evals": 1000}).status_code == 422


def test_job_queue_is_bounded():
    import threading

    from app.schemas import WhatIfRequest
    from app.services.jobs import JobManager, QueueFull
    gate = threading.Event()
    jm = JobManager(max_workers=1, max_retained=10, max_active=2)
    slow = lambda req, progress: gate.wait(5)  # noqa: E731
    jm.submit(WhatIfRequest(), slow)
    jm.submit(WhatIfRequest(), slow)
    with pytest.raises(QueueFull):
        jm.submit(WhatIfRequest(), slow)
    gate.set()
    jm.shutdown()


def test_assistant_disabled(client):
    assert client.get("/api/v1/assistant").json()["enabled"] is False
    assert client.post("/api/v1/assistant/ask", json={"question": "What is R3?"}).status_code == 501
