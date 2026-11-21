# Benchmarks

Formal benchmark suite against external methods is under development. This folder records the
verification runs that exist, with their environment and outcome.

## Objective

Show that the published results are reproduced by each implementation of the model and document where and
why the toolbox-free MATLAB path differs.

## Baseline methods

The reference is the MILP solution (MATLAB `intlinprog` run that produced `data/research_results_gridflex.csv`).
No external scheduling baselines are included in this release.

## Dataset

The synthetic 168-hour benchmark in `data/`.

## Metrics

Connection capacity, grid energy, CO₂, renewable utilisation, average delay, share shifted, envelope
violation per scenario; QUBO enumeration and QAOA statistics. Tolerances: relative 1e-4 / absolute 1e-3
(`scripts/crosscheck.py`), relative 1e-5–1e-6 (engine parity), and those coded in `verify/check_run.py`.

## Results (2026-11-21)

| Implementation | Environment | Command | Result |
|---|---|---|---|
| Python/SciPy cross-check | Windows 11, Python 3.13.5, SciPy 1.15.3 (HiGHS) | `python scripts/crosscheck.py` | 64 / 64 pass, 24 s |
| Web engine | same | `cd webapp/backend && python -m pytest` | 25 / 25 pass |
| MATLAB, no Optimization Toolbox | MATLAB R2026a | `qh2dc_verify_run` + `verify/check_run.py` | 50 pass / 19 fail, 88 s |

Files in `results/`:

- `matlab_R2026a_fallback_2026-11-21.txt` — full output of the 2026-11-21 MATLAB run of the current code.
  Every numeric value is identical to `verify/qh2dc_run_actual.txt` shipped with the code (only the byte
  sizes of three rendered PDF figures differ, by 1–2 bytes).
- `research_results_gridflex_FALLBACK.csv` — historical table from the toolbox-free path, recorded
  **before** the terminal-inventory fix (finding S1 in [docs/code-review.md](../docs/code-review.md)).
  Its capacities equal the current ones; its energy and shifting columns do not.

Current fallback run compared with the MILP reference:

| | Reference (MILP) | Fallback, current code |
|---|---|---|
| Six connection capacities | 15.163 / 12.586 / 10.586 / 8.944 / 10.700 / 10.615 MW | identical |
| R2 grid energy | 658.48 MWh | 665.39 MWh |
| R2 CO₂ | 242.64 t | 245.91 t |
| R2 electrolyser / fuel cell | 38.28 / 15.16 MWh | 20.83 / 8.25 MWh |
| R3 bundles moved | 3 (10.7 %) | 5 (17.9 %) |

Why: the fallback uses greedy, rule-based hydrogen dispatch instead of the MILP; capacities are found by the
same bisection and agree. Details: [docs/reproducibility.md](../docs/reproducibility.md).

## Limitations

No comparison with other scheduling algorithms, no timing study across hardware, a single synthetic
week. Contributions of baseline methods are welcome (see [ROADMAP.md](../ROADMAP.md)).
