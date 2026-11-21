"""Reproduce the paper's scenario table and QAOA statistics with Python/SciPy.

Runs the independent reference implementation (``verify/verify_python.py``) in a
temporary workspace and compares what it computes against the artefacts shipped in
``data/``.  Reference values are read from those files, never retyped here.

Usage::

    python scripts/crosscheck.py

Exit status is 0 when every comparison passes and 1 otherwise.  Runtime is about
20-60 s on a laptop; most of it is the 2 x 24 bisection MILP solves.
"""
from __future__ import annotations

import csv
import json
import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from qh2dc_reference import REPO, run_reference_model  # noqa: E402

REL_TOL = 1e-4   # relative tolerance for energy / carbon / capacity figures
ABS_TOL = 1e-3   # absolute floor (MW, MWh, t, %, h)

# CSV column  ->  key in verify_python.py's per-scenario result row
COLUMNS = {
    "grid_energy_MWh": "grid_MWh",
    "connection_capacity_MW": "conn_MW",
    "capacity_reduction_pct": "red_pct",
    "operational_CO2_t": "co2_t",
    "renewable_utilization_pct": "ren_util",
    "average_workload_delay_h": "avg_delay",
    "jobs_shifted_pct": "shifted",
    "violation_energy_MWh": "viol",
}


def close(a: float, b: float) -> bool:
    return math.isclose(a, b, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def compare(g: dict) -> list[tuple[str, float, float, bool]]:
    rows = []
    with open(REPO / "data" / "research_results_gridflex.csv", newline="") as fh:
        published = list(csv.DictReader(fh))
    computed = g["out"].to_dict("records")
    for pub, comp in zip(published, computed):
        tag = pub["scenario"].split()[0]
        for col, key in COLUMNS.items():
            a, b = float(pub[col]), float(comp[key])
            rows.append((f"{tag} {col}", a, b, close(a, b)))

    summary = json.loads((REPO / "data" / "verification_summary.json").read_text())
    qaoa = g["qaoa_res"]
    for p in (1, 2):
        for key in ("exp", "feas_mass", "p_opt", "gap"):
            a, b = float(summary["qaoa"][str(p)][key]), float(qaoa[p][key])
            rows.append((f"QAOA p={p} {key}", a, b, close(a, b)))
        rows.append((f"QAOA p={p} mode is exact optimum", 1.0, float(qaoa[p]["match"]), bool(qaoa[p]["match"])))
    rows.append(("QUBO feasible states", summary["n_feasible"], len(g["feas"]), summary["n_feasible"] == len(g["feas"])))
    rows.append(("QUBO basis states", summary["n_states"], 2 ** g["nq"], summary["n_states"] == 2 ** g["nq"]))
    rows.append(("QUBO best energy", summary["best_energy"], float(g["Ecost"][g["best"]]),
                 close(summary["best_energy"], float(g["Ecost"][g["best"]]))))
    for key, val in (("R1_curt", g["res"]["R1"]["curt"]), ("R2_EL", g["res"]["R2"]["EL"]),
                     ("R2_FC", g["res"]["R2"]["FC"])):
        rows.append((key, summary[key], float(val), close(summary[key], float(val))))
    return rows


def main() -> int:
    t0 = time.perf_counter()
    g = run_reference_model()
    rows = compare(g)
    width = max(len(r[0]) for r in rows)
    for name, pub, comp, ok in rows:
        print(f"{name:<{width}}  published={pub:<14.6g} computed={comp:<14.6g} {'PASS' if ok else 'FAIL'}")
    n_fail = sum(not r[3] for r in rows)
    print(f"\n{len(rows) - n_fail}/{len(rows)} checks passed in {time.perf_counter() - t0:.1f} s")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
