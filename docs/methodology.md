# Methodology

All parameter values on this page are read from `matlab/qh2dc_config.m`, the single source of truth;
the Python cross-check and the web engine use the same values and are tested against the published
outputs.

## Research objective

Find the **smallest grid connection** an AI campus needs, and quantify how much of it each resource —
on-site renewables, a small green-hydrogen chain, and workload flexibility — removes, under firm, phased
and non-firm connection envelopes, with zero unserved energy.

## Inputs

The 168-hour benchmark (`data/research_benchmark_168h.csv`, synthetic; see [data/README.md](../data/README.md)):
latency-sensitive demand `d_LS(t)`, 28 delay-tolerant bundles with energy `E_j` and three candidate
slots each, solar and wind output, grid carbon intensity `CI(t)` and the non-firm and phased envelopes.

## Data preparation

Workload is split by **latency tolerance**: real-time inference, live serving and interactive sessions are
fixed demand; training, fine-tuning, offline inference and preprocessing may move within an
arrival-to-deadline window. Each delay-tolerant job is a one-hour rectangular power block. All series share
an hourly clock. A validation gate checks `total = fixed + flexible` and `renewable = solar + wind`.

## Features

Per hour: demand, renewable availability, carbon intensity, connection envelope, and for each bundle the
candidate slots `{t0, t0+3, t0+7}` (clipped to the horizon).

## Model

### Variables (per hour t ∈ {1,…,168})

| Symbol | Code | Meaning | Bounds |
|---|---|---|---|
| g(t) | `pg` | grid import | 0 … C(t) |
| e(t) | `pe` | electrolyser intake | 0 … 4 MW |
| f(t) | `pf` | fuel-cell output | 0 … 2 MW |
| c(t) | `pc` | renewable curtailment | 0 … REN(t) |
| h(t) | `h` | hydrogen inventory (MWh-H) | 0 … 20, h(168) = 5 |
| x(j,k) | binaries | bundle j placed in its k-th candidate slot | {0, 1} |

### Constraints

- **Bus balance:** `g(t) + f(t) + REN(t) = d_LS(t) + Σ_j E_j x(j,k: slot = t) + e(t) + c(t)`
- **Inventory:** `h(t) = h(t−1) + η_el e(t) − f(t)/η_fc`, `h(0) = 5`, `η_el = 0.72`, `η_fc = 0.55`
- **Renewable backing:** `e(t) + c(t) ≤ REN(t)` (hydrogen is produced only from on-site renewables)
- **One-hot:** `Σ_k x(j,k) = 1` for every bundle
- **Connection:** `0 ≤ g(t) ≤ C(t)` — firm (uniform C), phased (staircase) or non-firm (time-varying)
- **Terminal inventory:** `h(168) = h(0) = 5 MWh-H`, so no benefit can come from emptying the tank

### Objective (no electricity price)

```
min  Σ_t [ w_co2 · CI(t) · g(t) / 1000  +  w_curt · c(t)  +  w_cycle · (e(t) + f(t)) ]
   + Σ_j Σ_k w_delay · delay(j,k) · x(j,k)
```

| Weight | Value | Unit |
|---|---|---|
| `w_co2` | 1.0 | per t CO₂ |
| `w_curt` | 1.0 | per MWh curtailed |
| `w_cycle` | 0.02 | per MWh through the hydrogen chain |
| `w_delay` | 5.0 | per bundle-hour of deferral |
| `w_shed` (MATLAB path only) | 1e4 | per MWh unserved — dominant penalty |

The MATLAB MILP carries an explicit unserved-energy slack with the dominant penalty and accepts a solution
when total slack ≤ 1e-6 MWh. The Python and web implementations have no slack variable: a schedule is
feasible only if the balance holds exactly. Both give the same capacities.

## Optimisation

- **MILP solver:** `intlinprog` (MATLAB Optimization Toolbox), GLPK (Octave), or HiGHS through
  `scipy.optimize.milp` with `mip_rel_gap = 0`, 300 s time limit. Without a MILP solver MATLAB falls back
  to `qh2dc_fallback_dispatch.m` (local search + rule-based hydrogen dispatch).
- **Capacity search:** bisection on a uniform cap over [0, 16] MW, 24 iterations (resolution
  16/2²⁴ ≈ 1e-6 MW). Feasibility is monotone in the cap, so the search is exact to its resolution.
- **Reported operating point:** R2 and R3 metrics are taken from the schedule solved **at** the reported
  capacity (see `verify/r2_check.py`).

## QUBO / QAOA (placement sub-problem)

For one day (four bundles × three slots = 12 binaries, 4,096 states, 3⁴ = 81 one-hot states):

```
Q_jk,jk += w_stress·max(0, E_j − headroom(t)) + w_carbon·CI(t)·E_j/1000
           − w_renew·min(E_j, max(0, REN(t) − d_LS(t))) + w_delay·delay(j,k)
one-hot:   A·(1 − Σ_k x_jk)²  →  −A on the diagonal, +2A between slots of one bundle, +A constant
collision: w_collide · E_j·E_j' / 10 for two bundles in the same hour
```

`headroom(t) = C_nonfirm(t) − (d_LS(t) − REN(t))`. Weights: A = 40, w_stress = 6, w_carbon = 1,
w_renew = 1.5, w_delay = 0.30, w_collide = 2.5. The cost operator is the diagonal of QUBO energies
rescaled by `max|E|`; the mixer is `exp(−iβX)` on every qubit; depth p ∈ {1, 2}. Angles were optimised
in MATLAB with `fminsearch` (Nelder–Mead), five random restarts, seed 7, 600 evaluations each; the
published statistics use those angles, pinned in `verify_python.py` and in the web engine.

## Outputs

Connection capacity per scenario, hourly schedules, and the metrics below; QAOA feasible mass,
optimum probability and optimality gap.

## Evaluation and metrics

| Metric | Definition |
|---|---|
| Required connection capacity | smallest feasible uniform cap (R2, R3) or peak import under an imposed envelope (R0, R1, R4, R5) |
| Capacity reduction | `1 − C/C_R0` |
| Envelope violation | `Σ max(0, g(t) − C(t))` |
| Unserved energy | MATLAB slack; structurally zero in the Python/web formulation |
| Operational CO₂ | `Σ g(t)·CI(t)/1000` |
| Renewable utilisation | `1 − Σ c(t) / Σ REN(t)` |
| Workload | share of bundles moved, mean and maximum deferral |
| QAOA | feasible probability mass, probability of the exact optimum, gap of the most probable feasible state |

## Baselines

R0 (grid-only reference) and the sequential scenarios R1–R5 are the comparisons implemented in this
release. Classical scheduling baselines (earliest-admissible, greedy renewable-/carbon-aware, simulated
annealing) are **not implemented** in this version — see [limitations.md](limitations.md).

## Experimental configuration

| Scenario | Renewables | Hydrogen | Flexibility | Envelope |
|---|---|---|---|---|
| R0 | – | – | – | none (peak import) |
| R1 | ✓ | – | – | none (peak import) |
| R2 | ✓ | ✓ | – | minimum uniform cap |
| R3 | ✓ | ✓ | ✓ | minimum uniform cap |
| R4 | ✓ | ✓ | ✓ | non-firm 10.7 / 6.5 MW (hours 08–14, 7 h daily) |
| R5 | ✓ | ✓ | ✓ | phased 8.7 / 9.7 / 10.7 MW |

## Assumptions

Perfect foresight over the week; hourly resolution; rectangular one-hour bundles with unchanged energy
when moved; constant conversion efficiencies; no part-load, start-up, ramp, degradation, compression or
water modelling; behind-the-meter campus with no export; the hydrogen tank is the only buffer modelled.

## Threats to validity

- **External validity:** one synthetic week; results may differ for other weather, workload mixes and grids.
- **Construct validity:** capacity from a perfect-foresight schedule is a lower bound relative to an
  operational, forecast-driven controller.
- **Attribution:** the 2.58 / 2.00 / 1.64 MW figures are a sequential decomposition; interactions between
  resources are not separated.
- **Numerical:** solutions with equal objective may differ in hydrogen trajectory; QAOA depth-2 statistics
  depend on the classical optimiser (see [reproducibility.md](reproducibility.md)).
