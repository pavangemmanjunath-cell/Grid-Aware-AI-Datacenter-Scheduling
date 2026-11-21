// Data access layer. Prefers the live FastAPI service (/api/v1); falls back to
// the static snapshot exported by scripts/export_static_snapshot.py so the app
// also runs as a static site (e.g. GitHub Pages) with no backend.

import {
  SCENARIO_KEYS,
  type Model,
  type PublishedRow,
  type QuantumProblem,
  type ScenarioKey,
  type ScenarioRun,
} from './types'

const API = 'api/v1'

const LABELS: Record<ScenarioKey, [string, string]> = {
  R0: ['Grid-only reference', 'No renewables, hydrogen or flexibility; peak import defines the baseline.'],
  R1: ['Renewable supply', 'Adds on-site solar and wind behind the meter.'],
  R2: ['Green-H₂ assisted', 'Adds electrolyser, hydrogen tank and fuel cell; smallest feasible uniform cap.'],
  R3: ['H₂ + workload flexibility', 'Delay-tolerant bundles may move to +3 h or +7 h; smallest feasible uniform cap.'],
  R4: ['Non-firm envelope', '10.7 MW, contracting to 6.5 MW for hours 08–14 (7 h) daily; peak import under the imposed envelope.'],
  R5: ['Phased envelope', '8.7 / 9.7 / 10.7 MW across three 56-hour stages; peak import under the imposed envelope.'],
}

async function getJSON<T>(url: string, init?: RequestInit): Promise<T> {
  const r = await fetch(url, init)
  if (!r.ok) throw new Error(`${r.status} ${r.statusText} for ${url}`)
  return (await r.json()) as T
}

export async function apiAvailable(): Promise<boolean> {
  try {
    const ctl = new AbortController()
    const t = setTimeout(() => ctl.abort(), 1500)
    const r = await fetch(`${API}/health`, { signal: ctl.signal })
    clearTimeout(t)
    return r.ok && (r.headers.get('content-type') ?? '').includes('json')
  } catch {
    return false
  }
}

// The static snapshot always loads: it carries the QAOA landscape and the
// unconstrained-R2 counterfactual that the API does not serve.
async function loadStatic(): Promise<Model> {
  const s = await getJSON<any>('data/qh2dc.json')
  const table = {} as Record<ScenarioKey, PublishedRow>
  for (const row of s.table as PublishedRow[]) table[row.scenario.split(' ')[0] as ScenarioKey] = row
  const scenarios = {} as Record<ScenarioKey, ScenarioRun>
  for (const k of SCENARIO_KEYS) {
    const sc = s.scenarios[k]
    scenarios[k] = {
      key: k, label: LABELS[k][0], description: LABELS[k][1],
      series: sc.series, cap: sc.cap, bundleDelays: sc.bundleDelays,
    }
  }
  const q = s.qaoa
  const quantum: QuantumProblem = {
    nQubits: q.nQubits, bundles: q.bundles, slots: q.slots, baselineHours: q.baselineHours,
    candidateHours: q.candidateHours, energies: q.energies, feasible: q.feasible, bestIndex: q.bestIndex,
    bestEnergy: q.bestEnergy, pinnedAngles: q.pinnedAngles, landscape: q.landscape,
  }
  return {
    mode: 'static', generated: s.meta.generatedUtc, benchmark: s.benchmark, bundles: s.bundles, scenarios,
    r2Unconstrained: s.scenarios.R2_unconstrained.series.grid, table, quantum,
    datasets: s.datasets.datasets, datasetsVerified: s.datasets.verified_utc, sha256: s.meta.sourceSha256,
  }
}

async function overlayLive(m: Model): Promise<Model> {
  const [details, problem, datasets, prov] = await Promise.all([
    Promise.all(SCENARIO_KEYS.map((k) => getJSON<any>(`${API}/scenarios/${k}`))),
    getJSON<any>(`${API}/quantum/problem`),
    getJSON<any[]>(`${API}/datasets`),
    getJSON<any>(`${API}/provenance`),
  ])
  const scenarios = { ...m.scenarios }
  details.forEach((d, i) => {
    const k = SCENARIO_KEYS[i]
    scenarios[k] = {
      key: k, label: d.label, description: d.description, bundleDelays: d.bundle_delays_h,
      cap: d.series.connection_cap_MW.every((v: number | null) => v === null) ? null : d.series.connection_cap_MW,
      series: {
        grid: d.series.grid_import_MW, electrolyser: d.series.electrolyser_MW, fuelcell: d.series.fuel_cell_MW,
        curtailed: d.series.curtailed_MW, h2: d.series.h2_inventory_MWh, flexLoad: d.series.flexible_load_MW,
      },
    }
  })
  return {
    ...m, mode: 'live', scenarios, datasets, sha256: prov.data_files,
    quantum: { ...m.quantum, energies: problem.energies, feasible: problem.feasible_states,
      bestIndex: problem.best_state, bestEnergy: problem.best_energy, pinnedAngles: problem.published_angles },
  }
}

export async function loadModel(): Promise<Model> {
  const base = await loadStatic()
  if (!(await apiAvailable())) return base
  try {
    return await overlayLive(base)
  } catch (e) {
    console.warn('Live API reachable but failed; using static snapshot', e)
    return base
  }
}

// ---- live-only operations ---------------------------------------------------

export type WhatIfMode = 'min-uniform-flexible' | 'min-uniform' | 'nonfirm' | 'phased'

export interface WhatIfRequest {
  mode: WhatIfMode
  electrolyser_mw: number
  fuel_cell_mw: number
  h2_max_mwh: number
  h2_init_mwh: number
  eta_el: number
  eta_fc: number
  demand_scale: number
  solar_scale: number
  wind_scale: number
  workload_flexibility: boolean
  candidate_offsets_h: number[]
  phased_levels_mw: number[]
  nonfirm_normal_mw: number
  nonfirm_reduced_mw: number
  nonfirm_start_hour: number
  nonfirm_end_hour: number
}

/** The paper's benchmark configuration; with these values the API reproduces R2-R5 exactly. */
export const DEFAULT_WHATIF: WhatIfRequest = {
  mode: 'min-uniform-flexible', electrolyser_mw: 4, fuel_cell_mw: 2, h2_max_mwh: 20, h2_init_mwh: 5,
  eta_el: 0.72, eta_fc: 0.55, demand_scale: 1, solar_scale: 1, wind_scale: 1, workload_flexibility: true,
  candidate_offsets_h: [0, 3, 7], phased_levels_mw: [8.7, 9.7, 10.7], nonfirm_normal_mw: 10.7,
  nonfirm_reduced_mw: 6.5, nonfirm_start_hour: 8, nonfirm_end_hour: 14,
}

export interface Job {
  id: string
  status: 'queued' | 'running' | 'succeeded' | 'failed'
  progress: number
  runtime_s: number | null
  error: string | null
  result: null | {
    disclaimer: string
    feasible: boolean
    connection_capacity_MW: number | null
    reduction_vs_grid_only_pct: number | null
    metrics: Record<string, number> | null
    bundle_delays_h: number[] | null
    series: null | { grid_import_MW: number[]; h2_inventory_MWh: number[]; connection_cap_MW: (number | null)[]; electrolyser_MW: number[]; fuel_cell_MW: number[]; flexible_load_MW: number[] }
  }
}

export const startWhatIf = (req: WhatIfRequest) =>
  getJSON<Job>(`${API}/simulations`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(req) })

export const getJob = (id: string) => getJSON<Job>(`${API}/simulations/${id}`)

export const optimiseQaoa = (p: number, restarts: number, seed: number) =>
  getJSON<any>(`${API}/quantum/optimise`, {
    method: 'POST', headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ p, restarts, seed, max_evals: 600 }),
  })
