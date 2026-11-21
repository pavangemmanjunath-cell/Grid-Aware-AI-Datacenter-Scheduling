# Quantum layer: QUBO / QAOA — justification, scope and frameworks

## Why a QUBO at all

The scheduling model has exactly one discrete decision: which of three slots each delay-tolerant bundle
runs in. Everything else — grid import, electrolyser and fuel-cell power, hydrogen inventory — is
continuous and is solved classically. That discrete block has the structure QUBO solvers are designed
for: one-hot assignment with pairwise interactions (two bundles in the same hour stress the connection
together). Writing it as a QUBO therefore:

1. makes the placement sub-problem portable to any QUBO solver (classical heuristics, annealers, QAOA);
2. keeps the quantum register small — it scales with bundles per day × slots (here 4 × 3 = 12), not with
   the 168-hour horizon or the continuous physics;
3. produces an instance whose **entire** state space (2¹² = 4,096 states, 3⁴ = 81 feasible) can be
   enumerated, so every quantum result is checked against exact ground truth.

This follows the decomposition used in power-system quantum studies (Ling et al. 2024, Singha et al. 2025, Pan et al. 2024, Lee et al. 2025 — refs [19]–[22] of the paper):
isolate the combinatorial block, keep the physics classical, verify by enumeration.

## What is and is not claimed

| Claimed | Not claimed |
|---|---|
| The data layer emits a compact, connection-aware QUBO whose feasible set is fully verifiable | Any quantum speed-up, scalability or solution-quality advantage |
| An ideal p = 1 / p = 2 QAOA puts 27.16 % / 67.13 % of its probability mass on feasible states and its most probable feasible state is the exact optimum | That QAOA beats classical solvers — a 12-variable problem is solved instantly by enumeration or branch-and-bound |
| The results are reproducible across four independent implementations (below) | Behaviour on noisy hardware (no noise model is included) |

## Formulation (summary)

QUBO terms per bundle j and slot k: connection stress (energy above the slot's non-firm headroom, weight 6),
carbon (weight 1), renewable coincidence (reward 1.5), deferral (0.30 per hour); one-hot penalty A = 40;
collision 2.5·E_j·E_j′/10 for two bundles in the same hour. Binary-to-spin mapping x = (1 − Z)/2 gives
the Ising cost Hamiltonian H_C = c₀ + Σ hᵢZᵢ + Σ Jᵢⱼ ZᵢZⱼ (14 ZZ couplings for day 0). The circuit is the
standard alternating-operator ansatz: Hadamards, then p layers of exp(−iγH_C/max|E|) and
exp(−iβΣXᵢ). Full detail: [methodology.md](methodology.md#qubo--qaoa-placement-sub-problem).

## Four independent implementations agree

| Implementation | How the cost layer is applied | Result |
|---|---|---|
| `matlab/qh2dc_qaoa.m` | diagonal phase on a 4,096-vector | produced the published angles and Table 3 |
| `verify/verify_python.py`, `webapp/backend/app/engine/quantum.py` | diagonal phase (NumPy) | 27.16 % / 67.13 % at the published angles |
| `webapp/frontend/src/lib/qaoa.ts` | diagonal phase (TypeScript, in the browser) | same values, live in the Quantum lab |
| `scripts/pennylane_crosscheck.py` | **gate by gate** in PennyLane: RZ + IsingZZ + RX on `default.qubit` | PASS at p = 1 and p = 2: feasible mass, optimum probability and ⟨C⟩ equal to the published values; full distribution agrees to 7·10⁻¹⁸ |

Run the PennyLane check:

```bash
python -m pip install -r requirements.txt -r requirements-quantum.txt
python scripts/pennylane_crosscheck.py
```

## Frameworks and licences

The core code needs **no quantum SDK**: the QAOA is a plain state-vector simulation in MATLAB, NumPy and
TypeScript. Standard SDKs can be used alongside it without licence conflicts with this repository's
Apache-2.0 licence:

| Framework | Licence (verified 2026-11-21) | Used here |
|---|---|---|
| [PennyLane](https://github.com/PennyLaneAI/pennylane) | Apache-2.0 (PyPI 0.45.1) | optional cross-check script; `requirements-quantum.txt` |
| [Qiskit](https://github.com/Qiskit/qiskit) | Apache-2.0 (PyPI 2.6.2) | not used; compatible |

Using a framework's simulator involves no cloud service, account or credential. Running on real quantum
hardware through a provider would involve that provider's terms of service and is outside this
release.

## Known sensitivity

The depth-2 statistics depend on the classical angle optimiser: MATLAB R2026a's `fminsearch` finds a
different local optimum (93.11 % feasible mass) from the run that produced the paper (67.13 %). The
published values came from the MATLAB optimisation run and are reproduced exactly with those angles pinned; the qualitative result (most probable
feasible state = exact optimum) holds in both. See [reproducibility.md](reproducibility.md).
