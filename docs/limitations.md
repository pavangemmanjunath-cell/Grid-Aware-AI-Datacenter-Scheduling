# Limitations

## Scientific limitations

- Results come from **one deterministic synthetic week**. The 41.0 % reduction describes this benchmark
  and configuration, not AI data centres in general.
- The relief figures (renewables 2.58 MW, hydrogen 2.00 MW, flexibility 1.64 MW) are a **sequential**
  decomposition R0 → R1 → R2 → R3. Interaction effects are not separated; a factorial or
  marginal-contribution analysis is not part of this release.
- The schedule assumes **perfect foresight** of demand, generation and carbon intensity over the week; the
  capacities are lower bounds relative to an operational, forecast-driven controller.
- "Zero unserved energy" holds for the modelled conditions only. No reserve margin, emergency import or
  workload shedding is modelled.

## Data limitations

- Synthetic signals with documented generating processes; not calibrated to a real site (see
  [data/README.md](../data/README.md)).
- Workload is two classes and 28 one-hour rectangular bundles; real jobs vary in duration, power profile
  and checkpointing overhead.
- The production-trace path (`matlab/qh2dc_ingest_trace.m`) is untested and requires a schema mapping for
  any public trace.

## Model limitations

- Hourly resolution: sub-hourly peaks that could breach an envelope are not represented.
- Constant electrolyser (0.72) and fuel-cell (0.55) efficiencies; 0.72 is a DOE ultimate target, not
  current practice. No part-load curves, ramp limits, minimum load, start-up losses, degradation,
  compression, water use, safety or permitting constraints.
- Behind-the-meter campus: unused renewable energy is curtailed, never exported. The hydrogen tank is the only
  buffer modelled.
- The QUBO covers one day's placement; continuous dispatch stays classical.

## Quantum layer

- Ideal, noiseless 12-qubit **state-vector simulation**. No device noise, decoherence or shot sampling.
- The instance is classically enumerable (4,096 states); the QAOA results are a formulation and
  verification study. **No quantum advantage in runtime, scalability or solution quality is claimed.**
- Depth-2 statistics depend on the classical optimiser and MATLAB release; the published values came from
  the MATLAB optimisation run and are reproduced exactly with those angles pinned (see
  [reproducibility.md](reproducibility.md)).

## Generalization limitations

- One site layout, one plant size, one envelope shape per scenario. Behaviour under different weather,
  demand growth, grid carbon profiles and contract terms is untested in this release.

## Computational limitations

- The bisection solves up to 25 MILPs per scenario; fine at 168 h, but the MATLAB fallback search is
  `O(n²K²T)` and the sparse assembly grows quadratically — neither is designed for a year-long horizon.

## Analyses described in the manuscript but not included in this release

The accepted manuscript's text also describes the analyses below. **Their code and numerical results are
not part of this repository**, and nothing in the repository or the web app presents results for them:

- classical scheduling baselines (earliest-admissible, renewable-aware greedy, carbon-aware greedy,
  simulated annealing) under identical conditions;
- one-factor-at-a-time sensitivity and forecast-error (perturbed-input) robustness scenarios;
- factorial / marginal-contribution attribution of the three resources;
- envelope sensitivity to contraction duration, minimum limits and deadline windows;
- multiple-initialisation, optimiser-setting and noise-aware QAOA studies, and N×K scaling experiments.

They are listed in [ROADMAP.md](../ROADMAP.md) as candidate extensions. Contributions that implement any
of them are welcome and must report results with their own provenance.

## Security / privacy considerations

The repository contains no personal, customer or proprietary data and no credentials. The API has no
authentication and is intended for local or trusted-network use; put it behind an authenticating proxy
before exposing it publicly. The what-if endpoint is CPU-bound; `QH2DC_MAX_WORKERS` limits concurrency.

## Deployment limitations

- In-memory job store (single process). Docker artefacts are provided but not yet validated.
- The 3D scene is an illustrative visual replay; positions and sizes are not to scale.

## Areas requiring further validation

Production-scale workload traces, measured facility power, sub-hourly resolution, forecast uncertainty,
detailed electrolyser/fuel-cell models, noisy quantum hardware, and
independent reproduction by third parties.
