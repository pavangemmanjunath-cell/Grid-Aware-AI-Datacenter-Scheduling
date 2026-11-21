"""Export the solved schedules and QAOA results as one JSON file for the web app's static (offline) mode.

The web app's static mode never solves anything itself.  It replays the hour-by-hour MILP
solutions computed here by the independent Python/SciPy reference model
(``verify/verify_python.py``, run in a temporary workspace) and shows the published
scenario table read from ``data/research_results_gridflex.csv``.

Usage::

    python scripts/export_static_snapshot.py            # writes webapp/frontend/public/data/qh2dc.json
    python scripts/export_static_snapshot.py --out x.json

The only browser-side computation is the 12-qubit QAOA state vector, which the
web app evaluates exactly from the QUBO energies exported here.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from qh2dc_reference import REPO, run_reference_model  # noqa: E402

DEFAULT_OUT = REPO / "webapp" / "frontend" / "public" / "data" / "qh2dc.json"


def r(x, nd=5):
    """Round arrays/scalars for a compact JSON payload."""
    a = np.asarray(x, dtype=float)
    out = np.round(a, nd)
    out[np.abs(out) < 10 ** -nd] = 0.0
    return out.tolist() if a.ndim else float(out)


def sig(x, digits=6):
    """Significant-figure rounding for probabilities that span many decades."""
    return [float(f"{v:.{digits}g}") for v in np.asarray(x, dtype=float)]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(g: dict) -> dict:
    T = int(g["T"])
    d = g["d"]
    res = g["res"]
    fix, flx, ren = g["FIX"], g["FLX"], g["REN"]

    caps = {
        "R0": None,
        "R1": None,
        "R2": np.full(T, res["R2"]["mincap"]),
        "R3": np.full(T, res["R3"]["mincap"]),
        "R4": g["CAP_NF"],
        "R5": g["CAP_PH"],
    }
    scen = {}
    zero = np.zeros(T)
    for key in ("R0", "R1", "R2", "R3", "R4", "R5"):
        s = res[key]
        if key == "R0":  # grid-only reference: import equals baseline demand
            series = dict(grid=fix + flx, electrolyser=zero, fuelcell=zero, curtailed=zero,
                          h2=zero, flexLoad=flx, renewableUsed=zero)
            delays = np.zeros(int(g["J"]), dtype=int)
        else:
            series = dict(grid=s["pg"], electrolyser=s["pe"], fuelcell=s["pf"], curtailed=s["pc"],
                          h2=s["h"], flexLoad=s["sched"], renewableUsed=ren - s["pc"] - s["pe"])
            delays = s["delays"]
        cap = caps[key]
        scen[key] = {
            "series": {k: r(v, 4) for k, v in series.items()},
            "cap": None if cap is None else r(cap, 4),
            "bundleDelays": [int(x) for x in delays],
        }
    # Fig. 5 counterfactual: H2 dispatch with bundles pinned, replayed against the envelope
    scen["R2_unconstrained"] = {"series": {"grid": r(res["R2u"]["pg"], 4)}}

    with open(REPO / "data" / "research_results_gridflex.csv", newline="") as fh:
        table = [{k: (v if k == "scenario" else float(v)) for k, v in row.items()} for row in csv.DictReader(fh)]

    summary = json.loads((REPO / "data" / "verification_summary.json").read_text())

    Ecost, onehot = g["Ecost"], g["onehot"]
    qaoa = g["qaoa_res"]
    return {
        "meta": {
            "title": "Grid-Connection-Aware Scheduling of AI Data Centres with Green Hydrogen "
                     "and Quantum-Assisted Workload Placement",
            "generatedUtc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "generator": "scripts/export_static_snapshot.py -> verify/verify_python.py (SciPy milp / HiGHS)",
            "note": "Hourly series are the MILP solutions of the independent Python reference model. "
                    "The scenario table is read verbatim from data/research_results_gridflex.csv. "
                    "The benchmark is a deterministic synthetic week, not operator data.",
            "sourceSha256": {
                name: sha256(REPO / "data" / name)
                for name in ("research_benchmark_168h.csv", "research_results_gridflex.csv",
                             "verification_summary.json")
            },
        },
        "params": {
            "T": T, "electrolyserMW": 4.0, "etaEL": 0.72, "fuelCellMW": 2.0, "etaFC": 0.55,
            "h2MaxMWh": 20.0, "h2InitMWh": 5.0, "nonfirmNormalMW": 10.7, "nonfirmReducedMW": 6.5,
            "nonfirmWindow": [8, 14], "phasedLevelsMW": [8.7, 9.7, 10.7], "phasedStageH": 56,
            "candidateOffsetsH": [0, 3, 7], "bundles": int(g["J"]),
        },
        "benchmark": {
            "hourOfDay": [int(x) for x in d.hour_of_day.values],
            "fixedLoad": r(fix, 4), "flexBaseline": r(flx, 4), "solar": r(g["SOL"], 4),
            "wind": r(g["WND"], 4), "renewable": r(ren, 4), "carbon": r(g["CI"], 2),
            "capNonfirm": r(g["CAP_NF"], 3), "capPhased": r(g["CAP_PH"], 3),
        },
        "bundles": [
            {"baselineHour": int(t0), "energyMWh": round(float(e), 4), "candidates": [int(c) for c in cands]}
            for t0, e, cands in zip(g["jt"], g["E"], g["CANDS"])
        ],
        "scenarios": scen,
        "table": table,
        "qaoa": {
            "nQubits": int(g["nq"]), "bundles": int(g["Jd"]), "slots": int(g["Kd"]),
            "baselineHours": [int(x) for x in g["jj"]],
            "candidateHours": [[int(x) for x in row] for row in g["cd"]],
            "energies": r(Ecost, 5),
            "feasible": [int(i) for i in np.where(onehot)[0]],
            "bestIndex": int(g["best"]),
            "bestEnergy": float(Ecost[g["best"]]),
            "assignmentHours": summary["assignment_hours"],
            "pinnedAngles": {str(p): [float(v) for v in qaoa[p]["par"]] for p in (1, 2)},
            "results": {str(p): {k: float(qaoa[p][k]) for k in ("exp", "feas_mass", "p_opt", "gap")}
                        | {"match": bool(qaoa[p]["match"])} for p in (1, 2)},
            "probabilities": {str(p): sig(qaoa[p]["pr"]) for p in (1, 2)},
            "landscape": {"gamma": r(g["gs"], 4), "beta": r(g["bs"], 4), "cost": r(g["land"], 3)},
        },
        "summary": summary,
        "datasets": json.loads((REPO / "data" / "public_datasets.json").read_text(encoding="utf-8")),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    payload = build(run_reference_model())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, separators=(",", ":")))
    print(f"wrote {args.out} ({args.out.stat().st_size / 1024:.0f} KiB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
