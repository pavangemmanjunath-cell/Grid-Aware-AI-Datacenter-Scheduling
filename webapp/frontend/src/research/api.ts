// Read-only research API (/api/...). The dashboard never computes results: every number comes from
// one of these endpoints. When the API is not running, the same responses are read from
// public/api-snapshot/ (written by `python -m app.snapshot`), so both modes show identical data.
import { useQuery } from '@tanstack/react-query'

export type ScenarioId = 'R0' | 'R1' | 'R2' | 'R3' | 'R4' | 'R5'
export const SCENARIO_IDS: ScenarioId[] = ['R0', 'R1', 'R2', 'R3', 'R4', 'R5']

export interface Meta {
  title: string
  authors: string[]
  orcid_first_author: string
  citation: string
  code_citation: string
  paper_url: string | null
  paper_doi: string | null
  software_doi: string | null
  model_version: string
  data_version: string
  benchmark_seed: number
  horizon_h: number
  solver: Record<string, string>
  generator: Record<string, number | number[] | string>
  known_differences_from_manuscript: string[]
  assumptions: Record<string, any>
  banner: string
}

export interface ScenarioRow {
  id: ScenarioId
  label: string
  kind: 'capacity_search' | 'imposed_envelope'
  tooltip: string
  capacity_label: string
  citation: string
  grid_energy_MWh: number
  connection_capacity_MW: number
  capacity_reduction_pct: number
  operational_CO2_t: number
  renewable_utilization_pct: number
  average_workload_delay_h: number
  jobs_shifted_pct: number
  violation_energy_MWh: number
}

export interface BenchmarkRow {
  hour: number; day: number; hour_of_day: number
  fixed_ai_load_MW: number; flex_baseline_MW: number; solar_MW: number; wind_MW: number; renewable_MW: number
  carbon_kgCO2_per_MWh: number; nonfirm_envelope_MW: number; phased_envelope_MW: number; nonfirm_window: boolean
}

export interface DispatchRow {
  hour: number; day: number; hour_of_day: number
  envelope_MW: number | null; grid_import_MW: number; electrolyser_MW: number; fuel_cell_MW: number
  curtailment_MW: number; h2_inventory_MWh: number; flex_load_MW: number
}

export interface JobRow { id: number; day: number; energy_MWh: number; baseline_hour: number; chosen_hour: number; delay_h: number }

export interface QaoaData {
  qubits: number; bundles: number; slots: number; states: number; feasible: number; best_energy: number
  baseline_hours: number[]; assignment_hours: number[]
  depths: { p: number; feasible_mass_pct: number; optimum_probability_pct: number; expected_cost: number; gap: number; most_probable_is_optimum: boolean }[]
  citation: string; source: string; note: string
}

export interface GraphNode { id: string; label: string; kind: 'source' | 'sink' | 'storage' | 'bus'; unit: string }
export interface GraphEdge { id: string; from: string; to: string; field: string; unit: string }
export interface ComponentGraph { nodes: GraphNode[]; edges: GraphEdge[]; balance: string; citation: string }

export interface ComponentDetail {
  id: string; label: string; kind: string; unit: string; scenario: ScenarioId; hour: number; in_scenario: boolean
  value_at_hour: number | null
  extra_at_hour: Record<string, number | null>
  series: (number | null)[]
  extra_series: Record<string, (number | null)[]>
  week_total: number; week_total_unit: string
  peak: { value: number; hour: number }
  share_pct: number | null; share_basis: 'supply' | 'load' | null
  limited_hours: number[]; limit_reason: string
  fields: string[]; endpoint: string; source_files: string[]; citation: string
  jobs?: { bundles: number; moved: number; mean_delay_h: number; running_at_hour: number[] }
}

let modePromise: Promise<'live' | 'snapshot'> | null = null
export function dataMode(): Promise<'live' | 'snapshot'> {
  if (!modePromise) {
    modePromise = (async () => {
      try {
        const ctl = new AbortController()
        const t = setTimeout(() => ctl.abort(), 1500)
        const r = await fetch('api/meta', { signal: ctl.signal })
        clearTimeout(t)
        return r.ok && (r.headers.get('content-type') ?? '').includes('json') ? 'live' : 'snapshot'
      } catch {
        return 'snapshot'
      }
    })()
  }
  return modePromise
}

/** Map an API path to its snapshot file. */
function snapshotFile(path: string): string {
  const u = new URL(path, 'http://x/')
  const s = u.searchParams.get('scenario')
  const parts = u.pathname.replace(/^\/api\//, '').split('/')
  if (parts[0] === 'dispatch' || parts[0] === 'jobs') return `api-snapshot/${parts[0]}_${s}.json`
  if (parts[0] === 'components' && parts[1]) return `api-snapshot/components/${parts[1]}_${s}.json`
  return `api-snapshot/${parts[0]}.json`
}

export async function getApi<T>(path: string): Promise<T> {
  const mode = await dataMode()
  const url = mode === 'live' ? path.replace(/^\//, '') : snapshotFile(path)
  // always revalidate (ETag -> cheap 304) so responses from two data versions are never mixed
  const r = await fetch(url, { cache: 'no-cache' })
  if (!r.ok) throw new Error(`${r.status} for ${path}`)
  return (await r.json()) as T
}

const forever = { staleTime: Infinity, gcTime: Infinity, retry: 1 } as const
export const useMeta = () => useQuery({ queryKey: ['meta'], queryFn: () => getApi<Meta>('/api/meta'), ...forever })
export const useScenarios = () => useQuery({ queryKey: ['scenarios'], queryFn: () => getApi<ScenarioRow[]>('/api/scenarios'), ...forever })
export const useBenchmark = () => useQuery({ queryKey: ['benchmark'], queryFn: () => getApi<{ rows: BenchmarkRow[] }>('/api/benchmark'), ...forever })
export const useDispatch = (s: ScenarioId) =>
  useQuery({ queryKey: ['dispatch', s], queryFn: () => getApi<{ rows: DispatchRow[]; kind: string; source: string }>(`/api/dispatch?scenario=${s}`), ...forever })
export const useJobs = (s: ScenarioId) =>
  useQuery({ queryKey: ['jobs', s], queryFn: () => getApi<{ rows: JobRow[]; source: string }>(`/api/jobs?scenario=${s}`), ...forever })
export const useQaoa = () => useQuery({ queryKey: ['qaoa'], queryFn: () => getApi<QaoaData>('/api/qaoa'), ...forever })
export const useGraph = () => useQuery({ queryKey: ['components'], queryFn: () => getApi<ComponentGraph>('/api/components'), ...forever })
/** Node detail; the payload's series is hour-independent, so it is fetched once per (node, scenario). */
export const useComponent = (id: string | null, s: ScenarioId, hour: number) =>
  useQuery({
    queryKey: ['component', id, s],
    queryFn: () => getApi<ComponentDetail>(`/api/components/${id}?scenario=${s}&hour=${hour}`),
    enabled: !!id, ...forever,
  })

export const useMode = () => useQuery({ queryKey: ['mode'], queryFn: dataMode, ...forever })
