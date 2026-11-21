"""Read-only research API consumed by the dashboard (/api/...).

Every value served here is read from a versioned file in ``data/``:

* ``research_results_gridflex.csv``        published scenario table (paper Table 2)
* ``research_benchmark_168h.csv``          synthetic 168-h benchmark (Fig. 2)
* ``dispatch/research_dispatch_<R>.csv``   hourly MILP dispatch per scenario (Figs. 5-6)
* ``dispatch/research_job_placement.csv``  chosen slot of every bundle per scenario
* ``verification_summary.json``            QUBO enumeration and QAOA statistics (Fig. 3, Table 3)

Nothing is re-solved on request.  Units are in field names; hours are integers 0-167.
"""
from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse

from ..config import Settings, get_settings

router = APIRouter(prefix="/api", tags=["research (read-only)"])

SCENARIOS = ("R0", "R1", "R2", "R3", "R4", "R5")
LABELS = {
    "R0": ("Grid only", "capacity_search", "Grid-only reference; its peak import is the firm connection requested today."),
    "R1": ("+ Renewables", "capacity_search", "Adds on-site solar and wind."),
    "R2": ("+ Green hydrogen", "capacity_search", "Adds electrolyser, hydrogen tank and fuel cell; smallest uniform cap by bisection."),
    "R3": ("+ Workload flexibility", "capacity_search", "Bundles may move +3 h or +7 h; smallest uniform cap by bisection."),
    "R4": ("Non-firm envelope", "imposed_envelope", "Envelope 10.7 MW, contracting to 6.5 MW for hours 08-14 (7 h) daily."),
    "R5": ("Phased envelope", "imposed_envelope", "Envelope 8.7 -> 9.7 -> 10.7 MW across three 56-hour stages."),
}
RESULT_FIELDS = ("grid_energy_MWh", "connection_capacity_MW", "capacity_reduction_pct", "operational_CO2_t",
                 "renewable_utilization_pct", "average_workload_delay_h", "jobs_shifted_pct", "violation_energy_MWh")
DOWNLOADS = {
    "research_benchmark_168h.csv": "research_benchmark_168h.csv",
    "research_flexible_jobs.csv": "research_flexible_jobs.csv",
    "research_results_gridflex.csv": "research_results_gridflex.csv",
    "verification_summary.json": "verification_summary.json",
    "research_job_placement.csv": "dispatch/research_job_placement.csv",
    "public_datasets.json": "public_datasets.json",
    **{f"research_dispatch_{k}.csv": f"dispatch/research_dispatch_{k}.csv" for k in SCENARIOS},
}
CITATION = ('P. Manjunath, T. Prüfer, Gunaseelan S, K. Durai and N. K. R. Chichili, "Grid-Connection-Aware Scheduling of '
            'AI Data Centres with Green Hydrogen and Quantum-Assisted Workload Placement," Procedia Computer Science (accepted, to appear), 5th '
            'Int. Conf. on Machine Learning and Data Engineering (ICMLDE 2026), Paper ID 1939.')
BANNER = ("Synthetic 168-h benchmark · decision support, not a site forecast · "
          "QAOA is an exact simulation, no quantum advantage claimed")
ETA_EL, ETA_FC, EL_MAX, FC_MAX, H_MAX = 0.72, 0.55, 4.0, 2.0, 20.0


def data_dir(settings: Settings = Depends(get_settings)) -> str:
    return str(settings.data_dir)


def check_scenario(scenario: str | None) -> str:
    s = (scenario or "").upper()
    if s not in SCENARIOS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"scenario must be one of R0-R5, got '{scenario}'")
    return s


def _r(x, nd=6):
    if x is None or not np.isfinite(float(x)):
        return None
    v = round(float(x), nd)
    return 0.0 if abs(v) < 10 ** -nd else v + 0.0  # no -0.0, no solver noise in the payload


# ------------------------------------------------------------------ loaders --
@lru_cache(maxsize=2)
def results_table(d: str) -> pd.DataFrame:
    df = pd.read_csv(Path(d) / "research_results_gridflex.csv")
    df.insert(0, "id", [s.split()[0] for s in df.scenario])
    return df.set_index("id")


@lru_cache(maxsize=2)
def bench(d: str) -> pd.DataFrame:
    return pd.read_csv(Path(d) / "research_benchmark_168h.csv")


@lru_cache(maxsize=12)
def dispatch_df(d: str, s: str) -> pd.DataFrame:
    return pd.read_csv(Path(d) / "dispatch" / f"research_dispatch_{s}.csv")


@lru_cache(maxsize=2)
def placement(d: str) -> pd.DataFrame:
    return pd.read_csv(Path(d) / "dispatch" / "research_job_placement.csv")


@lru_cache(maxsize=2)
def data_version(d: str) -> str:
    h = hashlib.sha256()
    for f in sorted(set(DOWNLOADS.values())):  # every file any endpoint reads or serves
        h.update(f.encode())
        h.update((Path(d) / f).read_bytes())
    return h.hexdigest()[:16]


# ---------------------------------------------------------------- endpoints --
@router.get("/meta", summary="Title, citation, model version, seed, solver, banner text")
def meta(settings: Settings = Depends(get_settings), d: str = Depends(data_dir)):
    b = bench(d)
    return {
        "title": "Grid-Connection-Aware Scheduling of AI Data Centres with Green Hydrogen and Quantum-Assisted Workload Placement",
        "short_name": "QH2DC",
        "authors": ["Pavan Manjunath", "Thomas Prüfer", "Gunaseelan S", "Karthiganesh Durai", "Naveen Kumar Reddy Chichili"],
        "orcid_first_author": "https://orcid.org/0000-0002-2694-8807",
        "citation": CITATION,
        "code_citation": "QH2DC reproducibility package (MATLAB + Python cross-check, 168-h benchmark), P. Manjunath et al., 2026.",
        "paper_url": None, "paper_doi": None, "software_doi": None,
        "model_version": settings.version, "data_version": data_version(d),
        "benchmark_seed": 20260430, "horizon_h": int(len(b)),
        "solver": {
            "published_table": "MATLAB intlinprog MILP run (data/research_results_gridflex.csv)",
            "hourly_dispatch": "independent reference MILP, SciPy milp / HiGHS (verify/verify_python.py, scripts/export_dispatch.py); "
                               "weekly totals equal the published table",
        },
        "generator": {"solar_clear_sky_amplitude_MW": 8.6, "wind_bounds_MW": [0.3, 5.0],
                      "solar_max_in_benchmark_MW": _r(b.solar_MW.max(), 3), "wind_max_in_benchmark_MW": _r(b.wind_MW.max(), 3),
                      "note": "The benchmark has no nameplate parameter; these are generator settings and observed maxima."},
        "known_differences_from_manuscript": [
            "R2 CO2: published table 242.64 t (schedule solved at the reported 10.59 MW cap); manuscript 242.25 t is the uncapped R2 schedule.",
            "Solar / wind: manuscript Table 1 lists 4.0 MW / 3.0 MW; the benchmark generator uses an 8.6 MW clear-sky amplitude and wind bounded to 0.3-5.0 MW.",
        ],
        "assumptions": {
            "electrolyser_MW": 4.0, "electrolyser_efficiency": 0.72, "fuel_cell_MW": 2.0, "fuel_cell_efficiency": 0.55,
            "h2_tank_MWh": 20.0, "h2_start_end_MWh": 5.0, "candidate_offsets_h": [0, 3, 7], "bundles": 28,
            "nonfirm_envelope_MW": {"normal": 10.7, "reduced": 6.5, "window_hours": [8, 14]},
            "phased_envelope_MW": [8.7, 9.7, 10.7], "phased_stage_h": 56,
            "objective_weights": {"w_co2_per_t": 1.0, "w_curtailment_per_MWh": 1.0, "w_h2_cycling_per_MWh": 0.02,
                                  "w_delay_per_bundle_h": 5.0, "w_unserved_per_MWh_matlab_only": 1e4},
            "bisection": {"interval_MW": [0.0, 16.0], "iterations": 24},
            "qubo_weights": {"one_hot": 40.0, "stress": 6.0, "carbon": 1.0, "renewable": 1.5, "delay": 0.30, "collision": 2.5},
            "source": "matlab/qh2dc_config.m",
        },
        "banner": BANNER,
    }


@router.get("/scenarios", summary="Six scenario rows with the eight published result fields (Table 2)")
def scenarios(d: str = Depends(data_dir)):
    t = results_table(d)
    out = []
    for s in SCENARIOS:
        label, kind, tip = LABELS[s]
        row = {"id": s, "label": label, "kind": kind, "tooltip": tip,
               "capacity_label": "Required grid connection" if kind == "capacity_search" else "Peak import under the imposed envelope",
               "citation": "Table 2"}
        row.update({f: float(t.loc[s, f]) for f in RESULT_FIELDS})
        out.append(row)
    return out


@router.get("/benchmark", summary="168 hourly rows of the synthetic benchmark (Fig. 2)")
def benchmark(d: str = Depends(data_dir)):
    b = bench(d)
    return {"synthetic": True, "seed": 20260430, "citation": "Fig. 2", "rows": [
        {"hour": int(r.hour_index), "day": int(r.day), "hour_of_day": int(r.hour_of_day),
         "fixed_ai_load_MW": _r(r.fixed_ai_load_MW), "flex_baseline_MW": _r(r.baseline_flexible_load_MW),
         "solar_MW": _r(r.solar_MW), "wind_MW": _r(r.wind_MW), "renewable_MW": _r(r.renewable_MW),
         "carbon_kgCO2_per_MWh": _r(r.grid_carbon_kgCO2_per_MWh, 3), "nonfirm_envelope_MW": _r(r.nonfirm_connection_cap_MW, 3),
         "phased_envelope_MW": _r(r.phased_connection_cap_MW, 3), "nonfirm_window": bool(r.nonfirm_constraint_event)}
        for r in b.itertuples()]}


@router.get("/dispatch", summary="168 hourly MILP dispatch rows for one scenario (Figs. 5-6)")
def dispatch(scenario: str | None = Query(None, description="R0-R5"), d: str = Depends(data_dir)):
    s = check_scenario(scenario)
    df = dispatch_df(d, s)
    rows = []
    for r in df.itertuples():
        rows.append({"hour": int(r.hour), "day": int(r.day), "hour_of_day": int(r.hour_of_day),
                     "envelope_MW": _r(r.envelope_MW), "grid_import_MW": _r(r.grid_import_MW),
                     "electrolyser_MW": _r(r.electrolyser_MW), "fuel_cell_MW": _r(r.fuel_cell_MW),
                     "curtailment_MW": _r(r.curtailment_MW), "h2_inventory_MWh": _r(r.h2_inventory_MWh),
                     "flex_load_MW": _r(r.flex_load_MW)})
    return {"scenario": s, "kind": LABELS[s][1], "citation": "Figs. 5-6",
            "source": f"data/dispatch/research_dispatch_{s}.csv", "rows": rows}


@router.get("/jobs", summary="28 flexible bundles with baseline and chosen hour for one scenario")
def jobs(scenario: str | None = Query(None, description="R0-R5"), d: str = Depends(data_dir)):
    s = check_scenario(scenario)
    p = placement(d)
    p = p[p.scenario == s]
    return {"scenario": s, "citation": "Fig. 5", "source": "data/dispatch/research_job_placement.csv", "rows": [
        {"id": int(r.job_id), "day": int(r.day), "energy_MWh": _r(r.energy_MWh, 4), "baseline_hour": int(r.baseline_hour),
         "chosen_hour": int(r.chosen_hour), "delay_h": int(r.delay_h)} for r in p.itertuples()]}


@router.get("/qaoa", summary="QUBO enumeration and QAOA statistics (Fig. 3, Table 3)")
def qaoa(d: str = Depends(data_dir)):
    v = json.loads((Path(d) / "verification_summary.json").read_text())
    return {"qubits": 12, "bundles": 4, "slots": 3, "states": v["n_states"], "feasible": v["n_feasible"],
            "best_energy": v["best_energy"], "baseline_hours": v["baseline_hours"], "assignment_hours": v["assignment_hours"],
            "depths": [{"p": int(p), "feasible_mass_pct": q["feas_mass"], "optimum_probability_pct": q["p_opt"],
                        "expected_cost": q["exp"], "gap": q["gap"], "most_probable_is_optimum": q["match"]}
                       for p, q in sorted(v["qaoa"].items())],
            "citation": "Fig. 3", "source": "data/verification_summary.json",
            "note": "Exact state-vector simulation of an enumerable instance; no quantum advantage claimed."}


# --------------------------------------------------------- component graph --
NODES = [
    ("grid", "Grid connection", "source", "MW"), ("solar", "Solar PV", "source", "MW"), ("wind", "Wind", "source", "MW"),
    ("bus", "Campus bus", "bus", "MW"), ("data_hall", "AI data hall", "sink", "MW"),
    ("job_queue", "Flexible job queue", "source", "MW"), ("electrolyser", "Electrolyser", "sink", "MW"),
    ("tank", "Hydrogen tank", "storage", "MWh-H2"), ("fuel_cell", "Fuel cell", "source", "MW"),
]
EDGES = [
    ("grid", "bus", "grid_import_MW", "MW"), ("solar", "bus", "solar_MW", "MW"), ("wind", "bus", "wind_MW", "MW"),
    ("fuel_cell", "bus", "fuel_cell_MW", "MW"), ("bus", "data_hall", "fixed_ai_load_MW", "MW"),
    ("job_queue", "data_hall", "flex_load_MW", "MW"), ("bus", "electrolyser", "electrolyser_MW", "MW"),
    ("electrolyser", "tank", "h2_produced_MWh_per_h", "MWh-H2/h"), ("tank", "fuel_cell", "h2_used_MWh_per_h", "MWh-H2/h"),
]


@router.get("/components", summary="Nine nodes and nine edges of the campus component graph")
def components():
    return {"nodes": [{"id": i, "label": l, "kind": k, "unit": u} for i, l, k, u in NODES],
            "edges": [{"id": f"{a}->{b}", "from": a, "to": b, "field": f, "unit": u} for a, b, f, u in EDGES],
            "balance": "grid + fuel cell + solar + wind = AI load (fixed + flexible) + electrolyser + curtailment",
            "citation": "Fig. 1"}


def _series(d: str, s: str) -> dict[str, np.ndarray]:
    b, x = bench(d), dispatch_df(d, s)
    has_ren = s != "R0"
    out = {
        "grid_import_MW": x.grid_import_MW.to_numpy(), "envelope_MW": x.envelope_MW.to_numpy(),
        "solar_MW": b.solar_MW.to_numpy() * has_ren, "wind_MW": b.wind_MW.to_numpy() * has_ren,
        "curtailment_MW": x.curtailment_MW.to_numpy(), "fixed_ai_load_MW": b.fixed_ai_load_MW.to_numpy(),
        "flex_load_MW": x.flex_load_MW.to_numpy(), "electrolyser_MW": x.electrolyser_MW.to_numpy(),
        "fuel_cell_MW": x.fuel_cell_MW.to_numpy(), "h2_inventory_MWh": x.h2_inventory_MWh.to_numpy(),
    }
    out["h2_produced_MWh_per_h"] = ETA_EL * out["electrolyser_MW"]
    out["h2_used_MWh_per_h"] = out["fuel_cell_MW"] / ETA_FC
    out["supply_MW"] = out["grid_import_MW"] + out["fuel_cell_MW"] + out["solar_MW"] + out["wind_MW"]
    out["demand_MW"] = out["fixed_ai_load_MW"] + out["flex_load_MW"] + out["electrolyser_MW"] + out["curtailment_MW"]
    out["balance_residual_MW"] = out["supply_MW"] - out["demand_MW"]
    return out


@router.get("/components/{node_id}", summary="One node: value at the hour, 168-h series, week total, peak, limits, fields used")
def component(node_id: str, scenario: str | None = Query(None, description="R0-R5"),
              hour: str = Query("0", description="integer 0-167"), d: str = Depends(data_dir)):
    s = check_scenario(scenario)
    if not hour.isdigit() or not 0 <= int(hour) <= 167:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"hour must be an integer 0-167, got '{hour}'")
    hour = int(hour)
    node = {i: (l, k, u) for i, l, k, u in NODES}.get(node_id)
    if node is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"unknown component '{node_id}'")
    S = _series(d, s)
    env = S["envelope_MW"]
    h2 = s in ("R2", "R3", "R4", "R5")
    week_supply = float(S["supply_MW"].sum())
    week_load = float((S["fixed_ai_load_MW"] + S["flex_load_MW"]).sum())
    spec = {  # field, extra fields, share basis, limit test, limit reason, in scenario
        "grid": ("grid_import_MW", ["envelope_MW"], "supply",
                 (S["grid_import_MW"] >= env - 1e-6) if np.isfinite(env).all() else np.zeros(168, bool),
                 "import at the connection envelope", True),
        "solar": ("solar_MW", ["curtailment_MW"], "supply", S["curtailment_MW"] > 1e-6, "renewable output curtailed (all renewables)", s != "R0"),
        "wind": ("wind_MW", ["curtailment_MW"], "supply", S["curtailment_MW"] > 1e-6, "renewable output curtailed (all renewables)", s != "R0"),
        "bus": ("balance_residual_MW", ["supply_MW", "demand_MW"], None, np.zeros(168, bool), "", True),
        "data_hall": ("fixed_ai_load_MW+flex_load_MW", ["fixed_ai_load_MW", "flex_load_MW"], "load", np.zeros(168, bool), "", True),
        "job_queue": ("flex_load_MW", [], "load", np.zeros(168, bool), "", True),
        "electrolyser": ("electrolyser_MW", ["h2_produced_MWh_per_h"], None, S["electrolyser_MW"] >= EL_MAX - 1e-6, "at rated power (4 MW)", h2),
        "tank": ("h2_inventory_MWh", [], None, (S["h2_inventory_MWh"] <= 1e-6) | (S["h2_inventory_MWh"] >= H_MAX - 1e-6), "empty or full", h2),
        "fuel_cell": ("fuel_cell_MW", ["h2_used_MWh_per_h"], "supply", S["fuel_cell_MW"] >= FC_MAX - 1e-6, "at rated power (2 MW)", h2),
    }[node_id]
    field, extras, basis, limited, reason, in_scen = spec
    series = S["fixed_ai_load_MW"] + S["flex_load_MW"] if node_id == "data_hall" else S[field]
    total = float(series.sum())
    share = None
    if basis == "supply" and week_supply > 0:
        share = 100 * total / week_supply
    elif basis == "load" and week_load > 0:
        share = 100 * total / week_load
    pk = int(np.argmax(np.abs(series))) if node_id == "bus" else int(np.argmax(series))
    resp = {
        "id": node_id, "label": node[0], "kind": node[1], "unit": node[2], "scenario": s, "hour": hour, "in_scenario": in_scen,
        "value_at_hour": _r(series[hour], 4),
        "extra_at_hour": {e: _r(S[e][hour], 4) for e in extras},
        "series": [_r(v, 4) for v in series], "extra_series": {e: [_r(v, 4) for v in S[e]] for e in extras},
        "week_total": _r(total, 3), "week_total_unit": "MWh-H2·h" if node_id == "tank" else "MWh",
        "peak": {"value": _r(series[pk], 4), "hour": pk},
        "share_pct": _r(share, 2), "share_basis": basis,
        "limited_hours": [int(t) for t in np.where(limited)[0]], "limit_reason": reason,
        "fields": [field] + extras, "endpoint": f"/api/components/{node_id}?scenario={s}&hour={hour}",
        "source_files": [f"data/dispatch/research_dispatch_{s}.csv", "data/research_benchmark_168h.csv"],
        "citation": "Fig. 1",
    }
    if node_id == "job_queue":
        p = placement(d)
        p = p[p.scenario == s]
        resp["jobs"] = {"bundles": int(len(p)), "moved": int((p.delay_h > 0).sum()), "mean_delay_h": _r(p.delay_h.mean(), 4),
                        "running_at_hour": [int(j) for j in p.job_id[p.chosen_hour == hour]]}
    return resp


@router.get("/download/{name}", summary="Download a published data file")
def download(name: str, d: str = Depends(data_dir)):
    rel = DOWNLOADS.get(name)
    if rel is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unknown file")
    return FileResponse(Path(d) / rel, filename=name)
