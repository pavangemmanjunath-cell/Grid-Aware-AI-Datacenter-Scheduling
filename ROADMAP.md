# Roadmap

## Current stable capabilities (v1.0.0)

- MATLAB reference implementation of the connection-aware MILP, bisection, QUBO and QAOA (paper results).
- Independent Python/SciPy cross-check reproducing all 64 published values.
- Importable Python engine with parity tests; FastAPI service with OpenAPI, async what-if jobs.
- React + three.js web simulator: 3D replay, quantum lab, Design studio (component configurator), data and architecture views;
  static (backend-free) mode.
- Documentation, CI, issue forms, citation metadata.

## Near-term improvements

- Validate and publish the Docker images; optional GitHub Pages deployment of the static app.
- Smoke test and synthetic fixture for `matlab/qh2dc_ingest_trace.m` (finding M4).
- Make `viol_MWh` meaningful on the MATLAB fallback path and state the 1e-6 MWh unserved tolerance
  (findings M1, M2).
- Pin the QAOA depth-2 angles in the MATLAB path as well (finding M3).
- Export of what-if results (CSV/JSON) from the web app.

## Research extensions (Proposed)

- Classical baselines under identical conditions: earliest-admissible, renewable-/carbon-aware greedy,
  simulated annealing, with runtime and solution quality.
- Factorial / marginal-contribution attribution of renewables, hydrogen and flexibility.
- Sensitivity to envelope depth, duration and deadline windows; one-factor-at-a-time sensitivity.
- Forecast-error and rolling-horizon operation.
- Sub-hourly resolution; detailed electrolyser/fuel-cell models.
- QAOA with multiple initialisations, optimisers, noise models and N×K scaling; real-hardware runs.
- Adapters for public workload, renewable and carbon-intensity data.
- A grounded language-model assistant behind the existing interface (ADR-0004).

## Community contributions welcome

- dataset adapters (download + convert scripts with licence notes);
- reproduction reports on Linux/macOS, Octave/GLPK, other MATLAB releases;
- a greedy baseline scheduler as a new engine module with tests;
- accessibility review of the web app; translations of the documentation.

## Long-term research direction

Treat AI campuses as schedulable, connection-aware assets: multi-site portfolios, coupling to grid-side
flexibility markets, and verified quantum or classical heuristics for the discrete placement layer at
realistic scale.
