"""Connection-aware mixed-integer scheduler (grid, electrolyser, fuel cell, H2, placement).

Library implementation of the formulation in the paper (Sec. 4) and in
``matlab/qh2dc_dispatch.m`` / ``verify/verify_python.py``.  It is a separate,
importable implementation; the published reference code is not modified.  The
parity test in ``webapp/backend/tests/test_engine_parity.py`` checks that the
defaults reproduce every number in ``data/research_results_gridflex.csv``.

Variables per hour t (T = 168):
    pg  grid import            [0, C(t)]
    pe  electrolyser intake    [0, EL_max]
    pf  fuel-cell output       [0, FC_max]
    pc  renewable curtailment  [0, REN(t)]
    h   hydrogen inventory     [0, H_max], h(T) = H_final
and one binary per (bundle, candidate slot) with a one-hot constraint per bundle.

Constraints:
    pg - pe - pc + pf - sum_j E_j x_jt = FIX(t) - REN(t)      (campus bus balance)
    h(t) - h(t-1) - eta_el pe(t) + pf(t)/eta_fc = 0, h(-1) = H_init
    pe(t) + pc(t) <= REN(t)                                   (H2 is renewable-backed)
Objective (no electricity price):
    sum w_co2 CI(t) pg(t)/1000 + w_curt pc + w_cycle (pe + pf) + w_delay * delay
Connection capacity is not in the objective; it is found by bisection as the
smallest uniform cap for which the programme is feasible.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import scipy.sparse as sp
from scipy.optimize import Bounds, LinearConstraint, milp

from .benchmark import CANDIDATE_OFFSETS, Benchmark


@dataclass(frozen=True)
class PlantConfig:
    electrolyser_mw: float = 4.0
    eta_el: float = 0.72
    fuel_cell_mw: float = 2.0
    eta_fc: float = 0.55
    h2_max_mwh: float = 20.0
    h2_init_mwh: float = 5.0
    w_co2: float = 1.0
    w_curt: float = 1.0
    w_cycle: float = 0.02
    w_delay: float = 5.0
    candidate_offsets: tuple[int, ...] = CANDIDATE_OFFSETS
    time_limit_s: float = 300.0


@dataclass
class Schedule:
    pg: np.ndarray
    pe: np.ndarray
    pf: np.ndarray
    pc: np.ndarray
    h: np.ndarray
    delays: np.ndarray
    flex_load: np.ndarray
    cap: np.ndarray
    metrics: dict = field(default_factory=dict)


def solve_dispatch(b: Benchmark, cap: np.ndarray, cfg: PlantConfig = PlantConfig(),
                   use_h2: bool = True, flexible: bool = False) -> Schedule | None:
    """Solve one scenario under the hourly import cap ``cap``. Returns None if infeasible."""
    T = b.T
    jt = b.bundle_hours
    E = b.bundle_energy
    cands = b.candidates(cfg.candidate_offsets)
    J = len(jt)
    K = [len(c) for c in cands]
    off = np.cumsum([0] + K)
    nb = int(off[-1])
    N = 5 * T + nb
    PG, PE, PF, PC, H = (slice(k * T, (k + 1) * T) for k in range(5))
    X0 = 5 * T

    # --- bus balance -------------------------------------------------------
    r, c, v = [], [], []
    for t in range(T):
        for k, val in ((0, 1.0), (1, -1.0), (3, -1.0), (2, 1.0)):
            r.append(t); c.append(k * T + t); v.append(val)
    for j in range(J):
        for kk, t in enumerate(cands[j]):
            r.append(t); c.append(X0 + off[j] + kk); v.append(-E[j])
    A1 = sp.coo_matrix((v, (r, c)), shape=(T, N))
    b1 = b.fixed - b.renewable

    # --- hydrogen inventory -----------------------------------------------
    r, c, v = [], [], []
    for t in range(T):
        r.append(t); c.append(4 * T + t); v.append(1.0)
        if t > 0:
            r.append(t); c.append(4 * T + t - 1); v.append(-1.0)
        r.append(t); c.append(T + t); v.append(-cfg.eta_el)
        r.append(t); c.append(2 * T + t); v.append(1.0 / cfg.eta_fc)
    A2 = sp.coo_matrix((v, (r, c)), shape=(T, N))
    b2 = np.zeros(T)
    b2[0] = cfg.h2_init_mwh if use_h2 else 0.0

    # --- one-hot placement -------------------------------------------------
    r, c, v = [], [], []
    for j in range(J):
        for kk in range(K[j]):
            r.append(j); c.append(X0 + off[j] + kk); v.append(1.0)
    A3 = sp.coo_matrix((v, (r, c)), shape=(J, N))

    # --- renewable backing: pe + pc <= REN --------------------------------
    r, c, v = [], [], []
    for t in range(T):
        r.append(t); c.append(T + t); v.append(1.0)
        r.append(t); c.append(3 * T + t); v.append(1.0)
    A4 = sp.coo_matrix((v, (r, c)), shape=(T, N))

    lb = np.zeros(N)
    ub = np.full(N, np.inf)
    ub[PG] = cap
    ub[PE] = cfg.electrolyser_mw if use_h2 else 0.0
    ub[PF] = cfg.fuel_cell_mw if use_h2 else 0.0
    ub[PC] = b.renewable
    ub[H] = cfg.h2_max_mwh if use_h2 else 0.0
    lb[5 * T - 1] = ub[5 * T - 1] = cfg.h2_init_mwh if use_h2 else 0.0  # terminal = initial
    ub[X0:] = 1.0
    if not flexible:
        for j in range(J):
            lb[X0 + off[j]] = ub[X0 + off[j]] = 1.0
            ub[X0 + off[j] + 1: X0 + off[j] + K[j]] = 0.0

    cost = np.zeros(N)
    cost[PG] = cfg.w_co2 * b.carbon / 1000.0
    cost[PC] = cfg.w_curt
    cost[PE] = cfg.w_cycle
    cost[PF] = cfg.w_cycle
    for j in range(J):
        for kk, t in enumerate(cands[j]):
            cost[X0 + off[j] + kk] = cfg.w_delay * (t - jt[j])

    integrality = np.zeros(N)
    integrality[X0:] = 1
    res = milp(
        c=cost,
        constraints=[LinearConstraint(A1, b1, b1), LinearConstraint(A2, b2, b2),
                     LinearConstraint(A3, np.ones(J), np.ones(J)),
                     LinearConstraint(A4, -np.inf, b.renewable)],
        bounds=Bounds(lb, ub), integrality=integrality,
        options={"time_limit": cfg.time_limit_s, "mip_rel_gap": 0.0},
    )
    if res.status != 0:
        return None
    x = res.x
    delays = np.array([cands[j][int(np.argmax(x[X0 + off[j]: X0 + off[j] + K[j]]))] - jt[j] for j in range(J)])
    flex_load = np.zeros(T)
    for j in range(J):
        flex_load[jt[j] + delays[j]] += E[j]
    s = Schedule(pg=x[PG], pe=x[PE], pf=x[PF], pc=x[PC], h=x[H], delays=delays,
                 flex_load=flex_load, cap=np.asarray(cap, dtype=float) * np.ones(T))
    s.metrics = schedule_metrics(b, s)
    return s


def schedule_metrics(b: Benchmark, s: Schedule) -> dict:
    """The six quantities of paper Sec. 4.2 for one solved schedule."""
    finite = np.isfinite(s.cap)
    return {
        "grid_energy_MWh": float(s.pg.sum()),
        "peak_import_MW": float(s.pg.max()),
        "operational_CO2_t": float((s.pg * b.carbon).sum() / 1000.0),
        # no on-site generation -> nothing to utilise; report 0 rather than 0/0
        "renewable_utilization_pct": float(100.0 * (1.0 - s.pc.sum() / b.renewable.sum())) if b.renewable.sum() > 0 else 0.0,
        "curtailed_MWh": float(s.pc.sum()),
        "electrolyser_MWh": float(s.pe.sum()),
        "fuel_cell_MWh": float(s.pf.sum()),
        "average_workload_delay_h": float(s.delays.mean()),
        "max_workload_delay_h": int(s.delays.max()),
        "jobs_shifted_pct": float(100.0 * np.mean(s.delays > 0)),
        "violation_energy_MWh": float(np.maximum(0.0, s.pg[finite] - s.cap[finite]).sum()),
        "h2_terminal_MWh": float(s.h[-1]),
    }


def min_uniform_capacity(b: Benchmark, cfg: PlantConfig = PlantConfig(), use_h2: bool = True,
                         flexible: bool = False, lo: float = 0.0, hi: float = 16.0,
                         iterations: int = 24, progress=None) -> float | None:
    """Smallest uniform connection capacity that keeps the scheduler feasible (bisection).

    Feasibility is monotone in the cap, so bisection is exact to its resolution
    ((hi - lo) / 2**iterations, below 1e-6 MW with the defaults).  Returns None if even
    ``hi`` is infeasible.
    """
    if solve_dispatch(b, np.full(b.T, hi), cfg, use_h2, flexible) is None:
        return None
    for i in range(iterations):
        mid = 0.5 * (lo + hi)
        if solve_dispatch(b, np.full(b.T, mid), cfg, use_h2, flexible) is not None:
            hi = mid
        else:
            lo = mid
        if progress:
            progress((i + 1) / iterations)
    return hi
