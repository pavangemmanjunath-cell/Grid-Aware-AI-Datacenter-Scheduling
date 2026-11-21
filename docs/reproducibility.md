# Reproducibility guide

Every command on this page was executed on 2026-11-21 on the environment below unless marked
*not yet validated*.

## Supported environment

| | Tested | Expected to work |
|---|---|---|
| OS | Windows 11 Home (10.0.26200) | Linux, macOS |
| Python | 3.13.5 (NumPy 2.1.3, SciPy 1.15.3, pandas 2.2.3, matplotlib 3.10.0, pytest 8.3.4) | ≥ 3.10 |
| MATLAB | R2026a (26.1), **without** Optimization Toolbox | R2021a or later |
| Node.js | 24.20 (Vite 8.3, TypeScript 7.0, React 19.3, three 0.187) | ≥ 20.19 |
| Hardware | laptop CPU; no GPU needed | any |

## Installation

```bash
git clone https://github.com/pavangemmanjunath-cell/Grid-Aware-AI-Datacenter-Scheduling.git
cd Grid-Aware-AI-Datacenter-Scheduling
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
```

On Windows, clone to a short path (e.g. `C:\src\`); the 260-character path limit otherwise breaks
`npm install` and some Python tools.

## Dependencies

Python packages in `requirements.txt` (cross-check, tests) and `webapp/backend/requirements.txt` (API).
MATLAB code needs no toolboxes; with the Optimization Toolbox it uses `intlinprog`, under GNU Octave
`glpk`. No quantum SDK is needed.

## Dataset preparation

None — the benchmark is shipped. Check it:

```bash
python -m pytest tests/unit -q
```

## Configuration

`matlab/qh2dc_config.m` holds every parameter. The Python implementations hard-code the same values and
are tested against the published outputs, so a change in one place must be mirrored (see ADR-0001).

## Random seeds

| Seed | Where | Effect |
|---|---|---|
| 20260430 | `cfg.rng_seed`, benchmark generator | defines the week; changing it changes every result |
| 7 | `cfg.qaoa.seed`, QAOA restarts | uses MATLAB's legacy `rand('seed', …)`; not stable across releases |

## Reproduce the core example

```bash
python examples/02_qubo_enumeration.py
```

Expected: `variables: 12  basis states: 4096  one-hot feasible: 81`, exact optimum hours
`[13, 15, 11, 14]`, QAOA feasible mass 27.16 % (p = 1) and 67.13 % (p = 2).

## Reproduce the experiments

**Python (independent implementation, ~25 s):**

```bash
python scripts/crosscheck.py
```

Expected final line: `64/64 checks passed`. The script runs `verify/verify_python.py` in a temporary
copy, so nothing in `data/` or `figures/` is overwritten. To regenerate the figures into a folder of your
choice, call `run_reference_model(workdir=Path("out"))` from `scripts/qh2dc_reference.py`.

**MATLAB (reference implementation, ~90 s):**

```matlab
cd matlab
main_qh2dc          % overwrites data/research_results_gridflex.csv and figures/gr1-gr6
```

or, without overwriting the published CSV:

```bash
cd verify
matlab -batch "addpath('../matlab'); qh2dc_verify_run('qh2dc_run_actual.txt')"
cd ..
python verify/check_run.py
```

**Web engine (~2 s):**

```bash
cd webapp/backend
python -m pip install -r requirements.txt
python -m pytest -q
```

## Expected outputs

| Scenario | Capacity (MW) | Grid (MWh) | CO₂ (t) | Renewable use | Mean delay | Shifted |
|---|---|---|---|---|---|---|
| R0 | 15.163 | 1,395.50 | 475.23 | 0.00 % | 0.00 h | 0.0 % |
| R1 | 12.586 | 673.64 | 249.42 | 94.93 % | 0.00 h | 0.0 % |
| R2 | 10.586 | 658.48 | 242.64 | 99.96 % | 0.00 h | 0.0 % |
| R3 | 8.944 | 658.48 | 242.39 | 99.96 % | 0.46 h | 10.7 % |
| R4 | 10.700 | 658.48 | 242.37 | 99.96 % | 1.50 h | 21.4 % |
| R5 | 10.615 | 658.48 | 242.59 | 99.96 % | 0.11 h | 3.6 % |

Hydrogen (R2): 38.28 MWh into the electrolyser, 15.16 MWh out of the fuel cell; 38.56 MWh would be
curtailed without the hydrogen chain (R1). QUBO: 81 feasible states, best cost 1.7335.

## Evaluation commands

| Command | Checks |
|---|---|
| `python -m pytest` | data invariants, published-number arithmetic, full Python reproduction |
| `python scripts/crosscheck.py` | 64 published values |
| `python verify/check_run.py` | a MATLAB run against the shipped reference |
| `cd webapp/backend && python -m pytest` | engine parity + API contract |

## Results of the MATLAB run on this machine (2026-11-21)

MATLAB R2026a, no Optimization Toolbox (fallback path), 88 s:

```
Connection capacity (the headline result)                PASS (12/12)
Workload flexibility                                     FAIL (13/15)
Envelope compliance                                      PASS (6/6)
Energy, carbon and hydrogen                              FAIL (7/21)
QUBO exhaustive enumeration                              PASS (7/7)
QAOA p=1                                                 PASS (4/4)
QAOA p=2                                                 FAIL (1/4)
TOTAL: 50 passed, 19 failed
```

These failures are expected and explained below. Every numeric value of this run is identical to the run
recorded in `verify/qh2dc_run_actual.txt` (the new output is kept as
`benchmarks/results/matlab_R2026a_fallback_2026-11-21.txt`).

## Known sources of non-determinism

1. **Fallback solver.** Without a MILP solver, MATLAB uses a local search with greedy hydrogen dispatch.
   All six capacities reproduce exactly; energy, carbon and hydrogen totals differ (R2: 665.39 vs 658.48
   MWh grid energy, 20.83 vs 38.28 MWh through the electrolyser), and R3 moves 5 bundles instead of 3.
2. **QAOA depth 2.** `fminsearch` and the legacy RNG are not stable across MATLAB releases. On R2026a the
   optimiser finds a different local optimum (93.11 % feasible mass, 1.304 % optimum probability) than the
   published run (67.13 %, 1.042 %). The published values came from the MATLAB optimisation run and are reproduced exactly with those angles pinned
   (Python cross-check and web engine). The qualitative result — the most probable feasible state is the
   exact optimum at both depths — holds in both runs.
3. **Degenerate MILP optima.** Different solvers may return different hydrogen trajectories with the same
   objective; the reported metrics are unaffected in the tested setups.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `FileNotFoundError` on Windows for an existing file | path longer than 260 characters — move the clone to a short path |
| MATLAB reports `solver_used=fallback` | Optimization Toolbox not installed; energy/hydrogen numbers will differ (see above) |
| Web app shows "Static snapshot" | API not running; start `uvicorn app.main:app --port 8000` in `webapp/backend` |
| `npm run build` fails on TypeScript | use the versions in `package-lock.json` (`npm ci`) |

## Reproducibility limitations

- Docker images are provided but were not built during release preparation (*not yet validated*).
- The GitHub Actions workflow is configured but has not run until the repository is pushed.
- The production-trace ingestion path (`qh2dc_ingest_trace.m`) has no test fixture.
- Analyses mentioned in the manuscript text but not included here cannot be reproduced from this
  repository (see [limitations.md](limitations.md)).
