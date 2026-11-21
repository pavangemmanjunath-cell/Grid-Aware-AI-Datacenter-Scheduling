# Paper ↔ code alignment

Maps every result in the accepted manuscript (ICMLDE 2026, paper ID 1939) to the code that produces it,
records what was verified by execution, and lists the places where the manuscript text and the code
differ. The code and `data/` are treated as the source of truth; no published number in `data/` has been
changed. (`verify/check_run.py` refers to this file for the diagnosis of its FAIL groups — see §3.)

## 1. Results → code

| Manuscript object | Produced by | Verified by |
|---|---|---|
| Table 1 benchmark configuration | `matlab/qh2dc_config.m`, `data/research_benchmark_168h.csv` | `tests/unit/test_benchmark_data.py` |
| Bus balance, inventory, connection bound (Sec. 4.1) | `matlab/qh2dc_dispatch.m` (`A1`, `A2`, `ub(ipg)`) | Python and web-engine parity |
| Objective and weights (Sec. 4.1) | `qh2dc_config.m` (`w_*`), cost vector in `qh2dc_dispatch.m` | [docs/methodology.md](docs/methodology.md) |
| Capacity bisection, 24 iterations | `matlab/qh2dc_min_capacity.m` | parity tests |
| Table 2 scenario results | `main_qh2dc.m` → `data/research_results_gridflex.csv` | `scripts/crosscheck.py` (64/64), engine parity |
| QUBO (Sec. 5.1) | `matlab/qh2dc_qubo.m`, `qh2dc_qubo_bruteforce.m` | enumeration: 4,096 states, 81 feasible |
| Table 3 QAOA | `matlab/qh2dc_qaoa.m`; angles pinned in `verify_python.py` | cross-check, engine parity, browser |
| Figs. 1–6 | `matlab/qh2dc_figures.m`, `verify/verify_python.py` | `figures/gr1–gr6` |
| R4 infeasible with bundles pinned (10 h, 23.21 MWh) | `qh2dc_dispatch.m` with `flexible = false` | `tests/integration`, engine tests |

## 2. Executed verification (2026-11-21)

| Run | Result |
|---|---|
| Python/SciPy cross-check (`scripts/crosscheck.py`) | **64 / 64** published values reproduced |
| Web engine (`webapp/backend/tests`) | 6 / 6 scenarios and 2 / 2 QAOA depths reproduced; R4-pinned infeasibility reproduced |
| MATLAB R2026a, no Optimization Toolbox (`verify/check_run.py`) | 50 pass / 19 fail — all six capacities exact; see §3 |

## 3. Diagnosis of the MATLAB fallback divergences

1. **Energy, carbon and hydrogen (7 of 21 pass).** Without a MILP solver the rule-based hydrogen dispatch is greedy;
   it captures less surplus than the optimum (e.g. 20.83 vs 38.28 MWh through the electrolyser). The MILP
   path is the reference for every energy, carbon and hydrogen number.
2. **Workload flexibility (13 of 15 pass).** With the terminal-inventory constraint enforced, the heuristic has less
   hydrogen in the tank and moves 5 bundles in R3 instead of 3. R4 and R5 match exactly.
3. **QAOA p = 2 (1 of 4 pass).** `fminsearch` with the legacy RNG finds a different local optimum on R2026a
   (93.11 % feasible mass vs 67.13 % published). Pinned angles reproduce the published values exactly.
   The qualitative claim (most probable feasible state = exact optimum) holds in both.

The code-level history of these fixes is kept in [docs/code-review.md](docs/code-review.md).

## 4. Data issues raised for the dashboard and how they were closed

| # | Issue | Resolution in this repository |
|---|---|---|
| 1 | R2 CO₂ 242.25 t (manuscript) vs 242.64 t (data) | Confirmed with the independent HiGHS MILP: 242.64 t at the reported 10.59 MW cap, 242.25 t without a cap. The dashboard serves 242.64 t and `/api/meta` records the difference. The MATLAB MILP path could not be re-run here (Optimization Toolbox unavailable). |
| 2 | Solar 4.0 MW / wind 3.0 MW (manuscript Table 1) vs benchmark maxima 8.48 / 4.66 MW | `/api/meta` serves the generator settings (8.6 MW clear-sky amplitude, wind bounded 0.3–5.0 MW) and observed maxima; the manuscript table should be corrected in a future version. |
| 3 | Hourly dispatch not saved | Exported to `data/dispatch/` (168 rows × 6 scenarios + job placements); weekly totals equal the published table (`tests/unit/test_dispatch_files.py`). |
| 4 | Solver path | Only MILP output is served; `/api/meta` names the solver of the table and of the hourly files. The toolbox-free fallback is documented in benchmarks/README.md and never served. |
| 5 | R4/R5 meaning | `/api/scenarios` carries `kind` and `capacity_label`; the UI shows “Peak import under the imposed envelope”. |

## 5. Manuscript statements that differ from the code (for the authors' attention)

These concern the manuscript text, not the code. They are listed so that readers comparing the paper with
this repository are not misled.

| # | Manuscript | Code / data | Note |
|---|---|---|---|
| 1 | R2 emissions **242.25 t** (text and Table 2) | **242.64 t** in `research_results_gridflex.csv` | 242.25 t is the R2 schedule solved with no cap; at the reported 10.59 MW it is 242.64 t. `verify/r2_check.py` labels 242.25 t "AS PUBLISHED" (manuscript) and 242.64 t "CORRECTED" (`data/`) |
| 2 | Hydrogen inventory peaks "near 16.0 MWh-H around hour 61" | 12.35 MWh-H at hour 61 for R2 at 10.59 MW | 16.0 MWh-H is again the uncapped R2 solution |
| 3 | Table 1: "Solar / wind capacity 4.0 MW peak / 3.0 MW rated" | solar reaches 8.48 MW, wind 0.86–4.66 MW in the benchmark | the benchmark has no nameplate parameter of 4.0 / 3.0 MW |
| 4 | R1 curtailment "spread across 22 hours during the quieter overnight periods" | the 22 curtailed hours are at 09:00–13:00 | count matches; timing is midday solar surplus |
| 5 | Conclusion: p = 2 "has a non-zero probability of 67.13 % to recover the true optimal daily assignment" | 67.13 % is the **feasible** mass; the optimum probability is 1.042 % | abstract and Table 3 state it correctly |
| 6 | Several analyses described as conducted (baselines, sensitivity, forecast error, factorial, noise-aware QAOA, N×K scaling) | not in this code base; no results reported in the manuscript | see [docs/limitations.md](docs/limitations.md) |
| 7 | "The numerical weights … and solver configuration … are reported" | weights and solver settings are in `qh2dc_config.m` and [docs/methodology.md](docs/methodology.md) | this repository supplies them |
