"""Optional: rebuild the QAOA circuit gate by gate in PennyLane and check it against the published numbers.

The repository's QAOA (``matlab/qh2dc_qaoa.m``, ``verify/verify_python.py``, the web engine and the browser)
applies the cost operator directly as a diagonal phase.  This script is an independent check in a
standard quantum SDK: it converts the QUBO to an Ising Hamiltonian with x = (1 - Z)/2, implements
exp(-i*gamma*H_C) with RZ and IsingZZ gates and the mixer exp(-i*beta*X) with RX gates, simulates the
12-qubit circuit on PennyLane's ``default.qubit`` and compares the measurement statistics with
``data/verification_summary.json``.

    python -m pip install -r requirements-quantum.txt
    python scripts/pennylane_crosscheck.py

PennyLane is Apache-2.0 licensed and is not needed for anything else in the repository.  Like the rest
of the quantum layer this is an ideal, noiseless simulation of an instance small enough to enumerate;
it is not evidence of quantum advantage.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "webapp" / "backend"))

import pennylane as qml  # noqa: E402

from app.engine.benchmark import load_benchmark  # noqa: E402
from app.engine.quantum import PUBLISHED_ANGLES, build_qubo  # noqa: E402


def ising_from_qubo(Q: np.ndarray, const: float):
    """E(x) = sum_i Q_ii x_i + sum_{i<j} Q_ij x_i x_j + const with x = (1 - z)/2  ->  c0 + sum h_i z_i + sum J_ij z_i z_j."""
    n = Q.shape[0]
    U = np.triu(Q)
    h = np.zeros(n)
    J = {}
    c0 = const
    for i in range(n):
        c0 += U[i, i] / 2
        h[i] -= U[i, i] / 2
        for j in range(i + 1, n):
            if U[i, j] != 0.0:
                c0 += U[i, j] / 4
                h[i] -= U[i, j] / 4
                h[j] -= U[i, j] / 4
                J[(i, j)] = U[i, j] / 4
    return c0, h, J


def main() -> int:
    q = build_qubo(load_benchmark(str(ROOT / "data")), day=0)
    n = q.n
    c0, h, J = ising_from_qubo(q.Q, q.const)

    # Sanity: the Ising form reproduces every one of the 4,096 QUBO energies.
    states = np.arange(2 ** n)
    z = 1 - 2 * ((states[:, None] >> np.arange(n)) & 1)
    e_ising = c0 + z @ h + sum(Jij * z[:, i] * z[:, j] for (i, j), Jij in J.items())
    assert np.allclose(e_ising, q.energies), "QUBO -> Ising conversion mismatch"

    scale = np.max(np.abs(q.energies))  # same rescaling of the cost operator as the reference code
    # Variable k is held in bit k of the state index; PennyLane's wire 0 is the most significant bit.
    wire = {k: n - 1 - k for k in range(n)}
    dev = qml.device("default.qubit", wires=n)

    @qml.qnode(dev)
    def circuit(angles, p):
        for w in range(n):
            qml.Hadamard(wires=w)
        for layer in range(p):
            g, b = angles[layer], angles[p + layer]
            for k in range(n):
                qml.RZ(2 * g * h[k] / scale, wires=wire[k])
            for (i, j), Jij in J.items():
                qml.IsingZZ(2 * g * Jij / scale, wires=[wire[i], wire[j]])
            for w in range(n):
                qml.RX(2 * b, wires=w)
        return qml.probs(wires=range(n))

    ref = json.loads((ROOT / "data" / "verification_summary.json").read_text())
    ok = True
    print(f"PennyLane {qml.__version__}: {n} qubits, {len(J)} ZZ couplings, {len(q.feasible)} feasible states")
    for p in (1, 2):
        # With variable k on wire n-1-k, PennyLane's big-endian probability index equals the repository's
        # state index (bit k = variable k), so no reordering is needed.
        pr = np.asarray(circuit(np.array(PUBLISHED_ANGLES[p]), p))
        feas = 100 * pr[q.feasible].sum()
        popt = 100 * pr[q.best]
        exp = float(pr @ q.energies)
        top = int(q.feasible[np.argmax(pr[q.feasible])])
        r = ref["qaoa"][str(p)]
        match = (np.isclose(feas, r["feas_mass"], rtol=1e-6) and np.isclose(popt, r["p_opt"], rtol=1e-6)
                 and np.isclose(exp, r["exp"], rtol=1e-6) and top == q.best)
        ok &= bool(match)
        print(f"p={p}: feasible mass {feas:.4f}% (published {r['feas_mass']:.4f}%), "
              f"P(optimum) {popt:.4f}% (published {r['p_opt']:.4f}%), <C> {exp:.4f} (published {r['exp']:.4f}), "
              f"mode = optimum: {top == q.best}  ->  {'PASS' if match else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
