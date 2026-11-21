# Examples

Small, deterministic scripts that show the core capability in seconds. Run them from the repository
root after `python -m pip install -r requirements.txt`.

| Script | Runtime | What it shows |
|---|---|---|
| `01_inspect_benchmark.py` | < 1 s | Signal ranges of the synthetic 168-h benchmark, the envelopes, and the grid-only reference R0 (15.16 MW, 1,395.50 MWh, 475.23 t CO₂) computed directly from the data. |
| `02_qubo_enumeration.py` | ~1 s | The 12-variable daily placement QUBO: 4,096 states, 81 one-hot feasible, exact optimum at hours `[13, 15, 11, 14]`; QAOA at the published angles gives 27.16 % (p = 1) and 67.13 % (p = 2) feasible mass. |

For the full reproduction of every published number run `python scripts/crosscheck.py` (about 25 s).
Neither example needs MATLAB, a network connection or credentials.
