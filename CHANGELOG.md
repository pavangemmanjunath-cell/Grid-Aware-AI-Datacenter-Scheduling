# Changelog

All notable changes to this project will be documented in this file.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Live demo of the dashboard on GitHub Pages (https://pavangemmanjunath-cell.github.io/Grid-Aware-AI-Datacenter-Scheduling/) and a social preview image (`assets/social-preview.png`).

## [1.0.0] - 2026-11-21

First public release accompanying the ICMLDE 2026 paper (ID 1939).

### Added
- MATLAB reference implementation (`matlab/`), not modified in this repository; it generated the published results table
  (`data/research_results_gridflex.csv`). Manuscript statements it does not reproduce are listed in PAPER_CODE_ALIGNMENT.md §4–§5.
- Independent Python/SciPy cross-check and MATLAB verification harness (`verify/`).
- Synthetic 168-hour benchmark, published results and verification summary (`data/`); catalogue of
  public validation datasets with licences verified on 2026-11-21 (`data/public_datasets.json`).
- `scripts/crosscheck.py` — reproduces 64 published values in an isolated workspace.
- `scripts/export_static_snapshot.py` — exports solved schedules for the web app's offline mode.
- Simulation engine and FastAPI service (`webapp/backend`) with OpenAPI, async what-if jobs, QUBO/QAOA
  endpoints, provenance endpoint and a disabled language-model assistant interface.
- React 19 + Vite + React Three Fiber web simulator (`webapp/frontend`): five research views plus Design studio
  and an optional 3D view.
- `START.bat` / `STOP.bat` one-click launcher for Windows (maps a temporary drive letter for long paths).
- `scripts/pennylane_crosscheck.py` — gate-level QAOA reproduction in PennyLane (optional, `requirements-quantum.txt`).
- Documentation of the quantum layer (`docs/quantum.md`), end-to-end data flow (`docs/data-flow.md`) and a dated
  survey of related papers, patents and repositories (`docs/related-work.md`).
- Research dashboard: five views (Campus, Connection, Week replay,
  Quantum check, Evidence), hand-built SVG component graph with ask-the-component answers, five KPI cards with
  citation chips, fixed honesty banner, URL state, light paper style with optional dark mode.
- Read-only research API (`/api/meta`, `/api/scenarios`, `/api/benchmark`, `/api/dispatch`, `/api/jobs`,
  `/api/qaoa`, `/api/components`, `/api/download`) with scenario `kind`, 400 on invalid scenarios, ETag caching.
- Hourly MILP dispatch per scenario (`data/dispatch/research_dispatch_<R>.csv`) and job placements
  (`data/dispatch/research_job_placement.csv`), exported by `scripts/export_dispatch.py`; totals equal the
  published table.
- Playwright acceptance tests (dashboard acceptance checklist); Expert review issue form; repository QR code (`assets/qr-github.png`).
- Test suites: data invariants, published-number consistency, full Python reproduction, engine parity,
  API contract.
- Documentation (`docs/`), ADRs, citation metadata, community health files, CI workflow, issue forms.
