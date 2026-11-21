# ADR-0001: The published reference code is immutable

- Status: Accepted (2026-11-21)

## Context
`matlab/` generated the published results table and `verify/verify_python.py` is its independent
cross-check. The web application needs an importable engine, which neither script provides.

## Decision
Keep `matlab/`, `verify/` and the published artefacts (`data/research_*.csv`, `data/verification_summary.json`)
byte-for-byte identical to the versions that generated the published results table (checked with checksums
when the repository was assembled). Documentation files added to `data/` are not artefacts. New capability — the web engine, API, scripts
and tests — lives in separate modules. `scripts/qh2dc_reference.py` runs the Python cross-check in a
temporary copy so that it never overwrites tracked files.

## Consequences
The model exists three times. Parity tests (`webapp/backend/tests/test_engine_parity.py`,
`tests/integration`) fail if any implementation drifts from `data/`. Any intentional model change must
update all three and be released as a new version with regenerated results.
