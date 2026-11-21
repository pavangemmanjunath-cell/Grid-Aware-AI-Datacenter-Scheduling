"""End-to-end reproduction with the independent Python/SciPy model.

Solves all six scenarios (including two 24-step capacity bisections), rebuilds the
12-variable QUBO, replays the QAOA angles, and compares everything against the
artefacts shipped in data/.  Runs in a temporary workspace; no tracked file is
written.  Takes about 20-60 s.
"""
import json
import math
from pathlib import Path

import numpy as np
import pytest

from crosscheck import compare

pytestmark = pytest.mark.integration


def test_every_published_number_reproduces(reference_model):
    failures = [row for row in compare(reference_model) if not row[3]]
    assert not failures, "\n".join(f"{n}: published {a} vs computed {b}" for n, a, b, _ in failures)


def test_schedules_are_physically_valid(reference_model):
    g = reference_model
    T, ren = g["T"], g["REN"]
    for key in ("R1", "R2", "R3", "R4", "R5"):
        s = g["res"][key]
        # campus bus balance: g + f + renewables = fixed + flexible + electrolyser + curtailed
        lhs = s["pg"] + s["pf"] + ren
        rhs = g["FIX"] + s["sched"] + s["pe"] + s["pc"]
        np.testing.assert_allclose(lhs, rhs, atol=1e-6, err_msg=key)
        assert s["pe"].max() <= 4.0 + 1e-6 and s["pf"].max() <= 2.0 + 1e-6
        assert s["h"].min() >= -1e-6 and s["h"].max() <= 20.0 + 1e-6
        if key != "R1":
            assert s["h"][-1] == pytest.approx(5.0, abs=1e-6), key  # terminal = initial inventory
        assert math.isclose(s["sched"].sum(), g["E"].sum(), rel_tol=1e-9)  # energy is conserved when moved
    assert len(g["res"]["R1"]["pg"]) == T


def test_r4_needs_workload_flexibility(reference_model):
    """Paper Sec. 6.2: with bundles pinned the non-firm case is infeasible."""
    g = reference_model
    assert g["solve"](g["CAP_NF"], True, False) is None
    r2u = g["res"]["R2u"]["pg"]
    excess = np.maximum(0.0, r2u - g["CAP_NF"])
    assert int((excess > 1e-6).sum()) == 10
    assert excess.sum() == pytest.approx(23.21, abs=0.01)


def test_static_snapshot_matches_published_table(reference_model, tmp_path):
    from export_static_snapshot import build
    payload = build(reference_model)
    out = tmp_path / "qh2dc.json"
    out.write_text(json.dumps(payload))
    data = json.loads(out.read_text())
    assert len(data["benchmark"]["fixedLoad"]) == 168
    assert len(data["qaoa"]["energies"]) == 4096 and len(data["qaoa"]["feasible"]) == 81
    for row in data["table"]:
        key = row["scenario"].split()[0]
        peak = max(data["scenarios"][key]["series"]["grid"])
        if key in ("R0", "R1", "R4", "R5"):  # reported figure is the peak import
            assert peak == pytest.approx(row["connection_capacity_MW"], abs=1e-3)
        else:  # R2, R3: smallest feasible uniform cap, import never exceeds it
            assert peak <= row["connection_capacity_MW"] + 1e-3
    assert sum(data["qaoa"]["probabilities"]["1"]) == pytest.approx(1.0, abs=1e-4)
