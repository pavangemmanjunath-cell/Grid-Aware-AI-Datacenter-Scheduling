"""Connection-aware QUBO for the daily placement sub-problem and an exact QAOA simulator.

Mirrors ``matlab/qh2dc_qubo.m`` / ``qh2dc_qaoa.m`` and ``verify/verify_python.py``:
four bundles x three candidate slots = 12 binary variables (4,096 basis states, 81
one-hot feasible).  The QAOA is an ideal state-vector simulation with the standard
alternating-operator ansatz and a transverse-field mixer.  It is a formulation and
verification study; the 12-variable instance is enumerated exhaustively and nothing
here is evidence of quantum advantage.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from scipy.optimize import minimize

from .benchmark import CANDIDATE_OFFSETS, Benchmark


@dataclass(frozen=True)
class QuboWeights:
    one_hot: float = 40.0     # A: one-hot penalty
    stress: float = 6.0       # connection-headroom violation at the candidate hour
    carbon: float = 1.0       # carbon of running the bundle in that hour
    renew: float = 1.5        # reward for coincidence with surplus renewables
    delay: float = 0.30       # deferral penalty per hour
    collide: float = 2.5      # two bundles in the same hour, scaled by E_j E_j' / 10


@dataclass
class Qubo:
    Q: np.ndarray             # upper-triangular QUBO matrix
    const: float
    n: int
    bundles: int
    slots: int
    baseline_hours: list[int]
    candidate_hours: list[list[int]]
    energies: np.ndarray      # cost of every basis state (index bit q = variable q)
    feasible: np.ndarray      # indices of one-hot states
    best: int                 # exact best feasible state


def build_qubo(b: Benchmark, day: int = 0, w: QuboWeights = QuboWeights()) -> Qubo:
    jj = [t for t in range(24 * day, 24 * (day + 1)) if b.flex[t] > 0]
    E = [b.flex[t] for t in jj]
    J, K = len(jj), len(CANDIDATE_OFFSETS)
    cd = [[min(b.T - 1, t0 + o) for o in CANDIDATE_OFFSETS] for t0 in jj]
    n = J * K
    Q = np.zeros((n, n))
    const = 0.0

    def vi(j, k):
        return j * K + k

    for j in range(J):
        for k in range(K):
            t = cd[j][k]
            head = b.cap_nonfirm[t] - (b.fixed[t] - b.renewable[t])
            Q[vi(j, k), vi(j, k)] += (w.stress * max(0.0, E[j] - head) + w.carbon * b.carbon[t] * E[j] / 1000.0
                                      - w.renew * min(E[j], max(0.0, b.renewable[t] - b.fixed[t]))
                                      + w.delay * (cd[j][k] - jj[j]))
    for j in range(J):  # one-hot: A (1 - sum_k x_jk)^2 expanded
        for k in range(K):
            Q[vi(j, k), vi(j, k)] -= w.one_hot
            for l in range(k + 1, K):
                Q[vi(j, k), vi(j, l)] += 2 * w.one_hot
        const += w.one_hot
    for j in range(J):
        for j2 in range(j + 1, J):
            for k in range(K):
                for l in range(K):
                    if cd[j][k] == cd[j2][l]:
                        Q[vi(j, k), vi(j2, l)] += w.collide * E[j] * E[j2] / 10.0

    bits = ((np.arange(2 ** n)[:, None] >> np.arange(n)) & 1).astype(float)
    energies = np.einsum("si,ij,sj->s", bits, np.triu(Q), bits) + const
    onehot = np.all(bits.reshape(-1, J, K).sum(axis=2) == 1, axis=1)
    feasible = np.where(onehot)[0]
    best = int(feasible[np.argmin(energies[feasible])])
    return Qubo(Q=Q, const=const, n=n, bundles=J, slots=K, baseline_hours=jj, candidate_hours=cd,
                energies=energies, feasible=feasible, best=best)


def assignment_hours(q: Qubo, state: int) -> list[int]:
    bits = [(state >> i) & 1 for i in range(q.n)]
    return [q.candidate_hours[j][int(np.argmax(bits[j * q.slots:(j + 1) * q.slots]))] for j in range(q.bundles)]


def qaoa_state(q: Qubo, angles: np.ndarray, p: int) -> np.ndarray:
    """State vector after p layers; angles = [gamma_1..gamma_p, beta_1..beta_p]."""
    es = q.energies / np.max(np.abs(q.energies))  # rescaled diagonal cost operator
    psi = np.full(2 ** q.n, 1 / np.sqrt(2 ** q.n), dtype=complex)
    g, bt = angles[:p], angles[p:]
    for i in range(p):
        psi = psi * np.exp(-1j * g[i] * es)
        cb, sb = np.cos(bt[i]), -1j * np.sin(bt[i])
        psi = psi.reshape([2] * q.n)
        for qb in range(q.n):
            psi = np.moveaxis(psi, qb, 0)
            a0, a1 = psi[0].copy(), psi[1].copy()
            psi[0] = cb * a0 + sb * a1
            psi[1] = sb * a0 + cb * a1
            psi = np.moveaxis(psi, 0, qb)
        psi = psi.reshape(-1)
    return psi


def qaoa_statistics(q: Qubo, angles, p: int) -> dict:
    angles = np.asarray(angles, dtype=float)
    pr = np.abs(qaoa_state(q, angles, p)) ** 2
    top = int(q.feasible[np.argmax(pr[q.feasible])])
    return {
        "p": p,
        "angles": angles.tolist(),
        "expected_cost": float(pr @ q.energies),
        "feasible_mass_pct": float(100 * pr[q.feasible].sum()),
        "optimum_probability_pct": float(100 * pr[q.best]),
        "most_probable_feasible_state": top,
        "most_probable_is_optimum": top == q.best,
        "optimality_gap": float(abs(q.energies[top] - q.energies[q.best])),
        "most_probable_assignment_hours": assignment_hours(q, top),
        "probabilities": pr,
    }


def optimise_angles(q: Qubo, p: int, restarts: int = 5, seed: int = 7, max_evals: int = 600) -> dict:
    """Nelder-Mead from random restarts (exploratory; results depend on seed and optimiser)."""
    rng = np.random.default_rng(seed)

    def f(a):
        return float(np.abs(qaoa_state(q, a, p)) ** 2 @ q.energies)

    runs = []
    for _ in range(restarts):
        x0 = np.concatenate([rng.uniform(0, 2 * np.pi, p), rng.uniform(-np.pi / 2, np.pi / 2, p)])
        r = minimize(f, x0, method="Nelder-Mead", options={"maxfev": max_evals, "xatol": 1e-6, "fatol": 1e-9})
        runs.append({"start": x0.tolist(), "angles": r.x.tolist(), "expected_cost": float(r.fun), "evaluations": int(r.nfev)})
    best = min(runs, key=lambda r: r["expected_cost"])
    return {"runs": runs, "best": best}


# Angles returned by the MATLAB reference run (fminsearch, five restarts, seed 7) and
# replayed by verify/verify_python.py.  These produce the published Table 3 values.
PUBLISHED_ANGLES = {
    1: [8.7833172550, -0.3786942217],
    2: [7.9399897710, 23.0519631284, 2.7535202027, 2.9468156799],
}


@lru_cache(maxsize=2)
def cached_qubo(data_dir: str) -> Qubo:
    from .benchmark import load_benchmark
    return build_qubo(load_benchmark(data_dir))
