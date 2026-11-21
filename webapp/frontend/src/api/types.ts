// Internal data model shared by every page. Both data sources (live FastAPI
// service and the static snapshot) are mapped into this shape by api/source.ts.

export type ScenarioKey = 'R0' | 'R1' | 'R2' | 'R3' | 'R4' | 'R5'
export const SCENARIO_KEYS: ScenarioKey[] = ['R0', 'R1', 'R2', 'R3', 'R4', 'R5']

export interface Series {
  grid: number[]
  electrolyser: number[]
  fuelcell: number[]
  curtailed: number[]
  h2: number[]
  flexLoad: number[]
}

export interface ScenarioRun {
  key: ScenarioKey
  label: string
  description: string
  series: Series
  cap: (number | null)[] | null
  bundleDelays: number[]
}

export interface PublishedRow {
  scenario: string
  grid_energy_MWh: number
  connection_capacity_MW: number
  capacity_reduction_pct: number
  operational_CO2_t: number
  renewable_utilization_pct: number
  average_workload_delay_h: number
  jobs_shifted_pct: number
  violation_energy_MWh: number
}

export interface Benchmark {
  hourOfDay: number[]
  fixedLoad: number[]
  flexBaseline: number[]
  solar: number[]
  wind: number[]
  renewable: number[]
  carbon: number[]
  capNonfirm: number[]
  capPhased: number[]
}

export interface Bundle {
  baselineHour: number
  energyMWh: number
  candidates: number[]
}

export interface QuantumProblem {
  nQubits: number
  bundles: number
  slots: number
  baselineHours: number[]
  candidateHours: number[][]
  energies: number[]
  feasible: number[]
  bestIndex: number
  bestEnergy: number
  pinnedAngles: Record<string, number[]>
  landscape?: { gamma: number[]; beta: number[]; cost: number[][] }
}

export interface PublicDataset {
  name: string
  signal: string
  url: string
  doi: string | null
  licence: string
  commercial_use: string
  access: string
  used_in_published_results: boolean
  status: string
}

export interface Model {
  mode: 'live' | 'static'
  generated: string
  benchmark: Benchmark
  bundles: Bundle[]
  scenarios: Record<ScenarioKey, ScenarioRun>
  r2Unconstrained?: number[]
  table: Record<ScenarioKey, PublishedRow>
  quantum: QuantumProblem
  datasets: PublicDataset[]
  datasetsVerified: string
  sha256: Record<string, string>
}
