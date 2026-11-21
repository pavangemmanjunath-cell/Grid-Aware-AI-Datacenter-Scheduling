"""Export the hourly MILP dispatch of every scenario as versioned CSV files.

The published scenario table only stores weekly totals; the hourly schedules behind Figs. 5 and 6
existed only inside ``solve()`` at run time.  This script runs the independent reference MILP
(``verify/verify_python.py``, SciPy ``milp`` / HiGHS) in a temporary workspace and writes

    data/dispatch/research_dispatch_<R0..R5>.csv   168 rows per scenario
    data/dispatch/research_job_placement.csv       28 bundles x 6 scenarios

Every weekly total of these files equals the published table (checked by
``tests/unit/test_dispatch_files.py``).  R2 and R3 are solved AT the capacity they report.

    python scripts/export_dispatch.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from qh2dc_reference import REPO, run_reference_model  # noqa: E402

OUT = REPO / "data" / "dispatch"
COLUMNS = ["hour", "day", "hour_of_day", "envelope_MW", "grid_import_MW", "electrolyser_MW", "fuel_cell_MW",
           "curtailment_MW", "h2_inventory_MWh", "flex_load_MW"]


def fmt(v: float | None) -> str:
    return "" if v is None or not np.isfinite(v) else f"{v:.6f}"


def main() -> int:
    g = run_reference_model()
    T, res = int(g["T"]), g["res"]
    fix, flx = g["FIX"], g["FLX"]
    zero = np.zeros(T)
    envelopes = {"R0": None, "R1": None, "R2": np.full(T, res["R2"]["mincap"]), "R3": np.full(T, res["R3"]["mincap"]),
                 "R4": g["CAP_NF"], "R5": g["CAP_PH"]}
    OUT.mkdir(parents=True, exist_ok=True)
    placement = []
    for key, env in envelopes.items():
        if key == "R0":
            s = dict(pg=fix + flx, pe=zero, pf=zero, pc=zero, h=zero, sched=flx, delays=np.zeros(int(g["J"]), dtype=int))
        else:
            s = res[key]
        with open(OUT / f"research_dispatch_{key}.csv", "w", newline="") as fh:
            w = csv.writer(fh, lineterminator="\n")
            w.writerow(COLUMNS)
            for t in range(T):
                w.writerow([t, t // 24, t % 24, fmt(None if env is None else env[t]), fmt(s["pg"][t]), fmt(s["pe"][t]),
                            fmt(s["pf"][t]), fmt(s["pc"][t]), fmt(s["h"][t]), fmt(s["sched"][t])])
        for j, (t0, d) in enumerate(zip(g["jt"], s["delays"], strict=True)):
            placement.append([key, j + 1, int(t0) // 24, int(t0), int(t0) + int(d), int(d), f"{g['E'][j]:.6f}"])
    with open(OUT / "research_job_placement.csv", "w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["scenario", "job_id", "day", "baseline_hour", "chosen_hour", "delay_h", "energy_MWh"])
        w.writerows(placement)
    print(f"wrote {len(envelopes)} dispatch files and {len(placement)} placement rows to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
