// Paper and repository facts shown in the app. Everything here is taken from the
// accepted manuscript (ICMLDE 2026, paper ID 1939) or from data/ in this repository.
// Publication identifiers are left empty until they exist; never fill them by guesswork.

export const PAPER = {
  id: 'ICMLDE-2026-1939',
  title: 'Grid-Connection-Aware Scheduling of AI Data Centres with Green Hydrogen and Quantum-Assisted Workload Placement',
  venue: 'International Conference on Machine Learning and Data Engineering (ICMLDE 2026) — accepted; proceedings to appear in Procedia Computer Science (Elsevier)',
  authors: [
    { name: 'Pavan Manjunath', aff: 'a', orcid: '0000-0002-2694-8807' },
    { name: 'Thomas Prüfer', aff: 'b' },
    { name: 'Gunaseelan S', aff: 'a' },
    { name: 'Karthiganesh Durai', aff: 'c' },
    { name: 'Naveen Kumar Reddy Chichili', aff: 'd' },
  ],
  affiliations: {
    a: 'Research Scholar, Bangalore, India',
    b: 'Senior Research Scholar, Dresden, Germany',
    c: 'Quantum Architect, Bangalore, India',
    d: 'Engineer, Bangalore, India',
  } as Record<string, string>,
  paperDoi: null as string | null, // not yet available
  softwareDoi: null as string | null, // created by Zenodo on the first GitHub release
  repository: 'https://github.com/pavangemmanjunath-cell/Grid-Aware-AI-Datacenter-Scheduling',
}

export const PROBLEM = {
  statement:
    'An AI campus can be built in about two years, while the grid reinforcement needed to energise it at full power often takes longer. ' +
    'The binding constraint is increasingly the connection agreement, not the electricity tariff. ' +
    'This work treats the required grid connection capacity itself as the quantity to minimise, under firm, phased and non-firm (time-varying) connection envelopes, ' +
    'using on-site renewables, a deliberately small green-hydrogen chain and the time flexibility of delay-tolerant AI work.',
  question: 'How small a grid connection can an AI campus run on — with zero unserved energy and every job inside its deadline window?',
  motivation: [
    'Connection queues at congested nodes delay energisation of new compute campuses by years.',
    'A firm connection sized to the peak assumes the campus is one rigid block of load.',
    'Operators increasingly offer non-firm agreements: earlier connection in exchange for periodic curtailment.',
    'Whether a campus can live inside such an envelope — and which resource relieves which hours — has, to our knowledge, rarely been quantified jointly (see docs/related-work.md).',
  ],
}

export const CONTRIBUTIONS = [
  ['Data-engineering layer', 'defines one hourly table of latency-sensitive demand, delay-tolerant bundles, solar, wind, carbon intensity and the connection envelope; the published results use the synthetic generator.'],
  ['Connection-minimising MILP', 'co-dispatches grid import, electrolyser, hydrogen inventory and fuel cell; connection capacity is recovered by bisection rather than priced.'],
  ['12-qubit QUBO / QAOA', 'the daily bundle-placement block written as a QUBO and solved by an exact state-vector QAOA, checked against all 4,096 states.'],
  ['Relief decomposition', 'connection capacity removed by renewables, hydrogen and workload flexibility in sequence.'],
]

export const LIMITATIONS = [
  'One deterministic synthetic week (168 h); not operator data and not statistically representative.',
  'Hourly resolution, rectangular workload blocks, constant electrolyser / fuel-cell efficiencies, perfect foresight.',
  'Behind-the-meter campus: unused renewable energy is curtailed, never exported; the hydrogen tank is the only buffer modelled.',
  'Ideal noiseless 12-qubit simulation; the instance is classically enumerable; no quantum advantage is claimed.',
  'Relief figures are a sequential decomposition (R0→R1→R2→R3), not a factorial attribution.',
  'The QAOA depth-2 percentages depend on the classical optimiser; the published values came from the MATLAB optimisation run and are reproduced with those angles pinned.',
]

export const NOT_IN_RELEASE = [
  'Classical scheduling baselines (earliest-admissible, renewable-/carbon-aware greedy, simulated annealing)',
  'One-factor-at-a-time sensitivity and forecast-error robustness scenarios',
  'Factorial / marginal-contribution attribution of the three resources',
  'Envelope sensitivity (contraction duration, minimum limits, deadline windows)',
  'Noise-aware QAOA and N×K scaling experiments',
]
