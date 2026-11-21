"""Contract of the read-only research API (/api/...) used by the dashboard."""
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.services.simulation import published_table

from .conftest import DATA


@pytest.fixture(scope="module")
def client():
    with TestClient(create_app()) as c:
        yield c


def test_meta(client):
    m = client.get("/api/meta").json()
    assert m["benchmark_seed"] == 20260430 and "no quantum advantage" in m["banner"]
    assert m["paper_doi"] is None and m["software_doi"] is None  # never invented
    assert "Paper ID 1939" in m["citation"]


def test_scenarios_kind_and_values(client):
    rows = client.get("/api/scenarios").json()
    pub = published_table(str(DATA))
    assert [r["id"] for r in rows] == ["R0", "R1", "R2", "R3", "R4", "R5"]
    for r in rows:
        assert r["connection_capacity_MW"] == pub[r["id"]]["connection_capacity_MW"]
        expected = "imposed_envelope" if r["id"] in ("R4", "R5") else "capacity_search"
        assert r["kind"] == expected
    assert rows[4]["capacity_label"] == "Peak import under the imposed envelope"


@pytest.mark.parametrize("path", ["/api/dispatch?scenario=R9", "/api/jobs?scenario=x", "/api/components/grid?scenario=R7",
                                  "/api/dispatch", "/api/components/grid?scenario=R3&hour=200", "/api/components/grid?scenario=R3&hour=x"])
def test_bad_parameters_are_400_with_text_detail(client, path):
    r = client.get(path)
    assert r.status_code == 400 and isinstance(r.json()["detail"], str)


def test_no_negative_zero_or_noise_in_bus_payload(client):
    raw = client.get("/api/components/bus?scenario=R4&hour=0").text
    assert "-0.0" not in raw
    assert all(v == 0.0 for v in client.get("/api/components/bus?scenario=R4&hour=0").json()["series"])


def test_dispatch_and_jobs(client):
    d = client.get("/api/dispatch?scenario=R4").json()
    assert len(d["rows"]) == 168 and d["kind"] == "imposed_envelope"
    assert all(r["grid_import_MW"] <= r["envelope_MW"] + 1e-6 for r in d["rows"])
    j = client.get("/api/jobs?scenario=R4").json()["rows"]
    assert len(j) == 28 and sum(r["delay_h"] > 0 for r in j) == 6


def test_qaoa(client):
    q = client.get("/api/qaoa").json()
    assert q["states"] == 4096 and q["feasible"] == 81
    assert [round(x["feasible_mass_pct"], 2) for x in q["depths"]] == [27.16, 67.13]


def test_components_graph_and_balance(client):
    g = client.get("/api/components").json()
    assert len(g["nodes"]) == 9 and len(g["edges"]) == 9
    for s in ("R0", "R3", "R4"):
        bus = client.get(f"/api/components/bus?scenario={s}&hour=37").json()
        assert max(abs(v) for v in bus["series"]) < 1e-3, s  # supply - demand = 0 every hour
    grid = client.get("/api/components/grid?scenario=R4&hour=37").json()
    disp = client.get("/api/dispatch?scenario=R4").json()["rows"][37]
    assert grid["value_at_hour"] == pytest.approx(disp["grid_import_MW"], abs=1e-4)
    assert grid["extra_at_hour"]["envelope_MW"] == pytest.approx(6.5)
    assert "grid_import_MW" in grid["fields"] and grid["endpoint"].startswith("/api/components/grid")
    assert client.get("/api/components/nope?scenario=R3").status_code == 404


def test_cache_headers_and_etag(client):
    r = client.get("/api/scenarios")
    assert r.headers["cache-control"] == "public, max-age=86400" and r.headers["etag"]
    assert client.get("/api/scenarios", headers={"if-none-match": r.headers["etag"]}).status_code == 304
    assert "etag" not in client.get("/api/v1/health").headers


def test_download_whitelist(client):
    assert client.get("/api/download/research_results_gridflex.csv").status_code == 200
    assert client.get("/api/download/..%2Fsecret").status_code == 404
