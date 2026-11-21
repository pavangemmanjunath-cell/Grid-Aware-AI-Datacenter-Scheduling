# Technical positioning

## Existing approaches

1. **Carbon- and price-aware workload shifting** — move delay-tolerant compute in time or space toward
   cleaner or cheaper hours (e.g. Wiesner et al. 2021; Radovanović et al. 2023; Riepin, Brown & Zavala 2025).
2. **Data-centre microgrids with hydrogen** — size or dispatch on-site power-to-hydrogen to cut cost or
   absorb surplus (e.g. Liu et al. 2025; LCOE-based microgrid analyses).
3. **Data-centre co-simulation and demand response** — simulate energy systems around a data centre or
   track an operator's power target (e.g. vessim, flexdc-sim; Dvorkin 2025).
4. **Quantum optimisation for power scheduling** — QUBO/QAOA or annealing for unit commitment, market
   clearing and redispatch, typically by decomposition (e.g. Ling et al. 2024; Pan et al. 2024; Lee et al. 2025;
   full list in [related-work.md](related-work.md)).

A dated list of public implementations is in [related-work.md](related-work.md).

## Limitations addressed

- In classes 1–3 the grid connection is usually absent, fixed, or an input; the question "what is the
  **smallest** connection this campus can live with?" is not asked directly.
- Hydrogen studies rarely let the workload move; flexibility studies rarely include a hydrogen chain. Their relief
  therefore cannot be compared on the same hours.
- Quantum scheduling studies seldom provide an instance whose full state space is enumerated, so the
  quantum result cannot be checked exactly.

## Approach implemented in this repository

- Connection capacity is the output: a MILP with **no price term** is wrapped in a bisection that returns
  the smallest feasible uniform cap; envelopes may also be phased or time-varying.
- Hydrogen dispatch and discrete workload placement are optimised **jointly**, with a cyclic terminal
  inventory so the tank cannot be emptied for an artificial gain.
- Only the placement block is mapped to a 12-variable QUBO; the instance is enumerated exhaustively and
  QAOA statistics are reported against that ground truth.

## Technical differences (measurable)

| Aspect | Typical prior formulation | Here |
|---|---|---|
| Decision output | cost / carbon at a given connection | minimum feasible connection (MW) |
| Envelope | none or constant | firm, phased, hourly non-firm |
| Hydrogen × flexibility | one or the other | both, same hours, same model |
| Quantum layer | whole problem or another block | placement only; verified by enumeration |
| Reproduction | single implementation | MATLAB + independent Python + web engine, tested for parity |

## Research hypothesis

Renewables, a hydrogen tank and workload flexibility relieve a connection envelope through different
time-scales, so they are complementary rather than interchangeable; a small hydrogen plant plus limited
shifting is enough to hold a non-firm envelope with zero unserved energy.

## Evidence currently available

On the synthetic benchmark only: the sequential decomposition (15.16 → 12.59 → 10.59 → 8.94 MW); the
non-firm case being infeasible with bundles pinned (10 h, 23.21 MWh over the envelope) and feasible with
6 of 28 bundles moved; QAOA at p = 1 and p = 2 placing its most probable feasible state on the exact
optimum. Produced by the MATLAB MILP run and reproduced by two independent implementations (Python/SciPy,
web engine).

## Evidence still required

Real workload and site data; multiple weeks and weather years; forecast uncertainty; factorial
attribution; comparison with classical scheduling heuristics; sub-hourly validation; detailed equipment
models; noisy-hardware QAOA. None of these is provided by this release.

## Limitations

See [limitations.md](limitations.md). The positioning above is a statement about formulation and
verification, not about performance or superiority.
