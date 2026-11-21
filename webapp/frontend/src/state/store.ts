import { create } from 'zustand'
import type { Model } from '../api/types'
import { SCENARIO_IDS, type ScenarioId } from '../research/api'

export type View = 'campus' | 'connection' | 'week' | 'quantum' | 'evidence' | 'studio'
export const VIEWS: { id: View; label: string; question: string }[] = [
  { id: 'campus', label: 'Campus', question: 'What is happening on site at this hour, and what does it add up to?' },
  { id: 'connection', label: 'Connection', question: 'How many MW does each resource remove?' },
  { id: 'week', label: 'Week replay', question: 'Does the campus stay inside the envelope every hour?' },
  { id: 'quantum', label: 'Quantum check', question: 'Does QAOA find the optimal job placement?' },
  { id: 'evidence', label: 'Evidence', question: 'Where does each number come from, and what are the limits?' },
]

interface AppState {
  /** legacy model used by the 3D view, the circuit explorer and the Design studio */
  model: Model | null
  error: string | null
  view: View
  scenario: ScenarioId
  /** continuous playback position in hours, 0 <= hour < 168 */
  hour: number
  playing: boolean
  speed: number // simulated hours per second
  selectedNode: string | null
  setModel: (m: Model) => void
  setError: (e: string) => void
  setView: (v: View) => void
  setScenario: (s: ScenarioId) => void
  setHour: (h: number) => void
  setPlaying: (p: boolean) => void
  setSpeed: (s: number) => void
  selectNode: (n: string | null) => void
}

// ---- shareable URL state: ?view=campus&scenario=R4&hour=37 -------------------
function readUrl(): { view: View; scenario: ScenarioId; hour: number } {
  const q = new URLSearchParams(window.location.search)
  const v = q.get('view') as View
  const s = (q.get('scenario') ?? '').toUpperCase() as ScenarioId
  const h = q.has('hour') ? Number(q.get('hour')) : NaN
  return {
    view: [...VIEWS.map((x) => x.id), 'studio'].includes(v) ? v : 'campus',
    scenario: SCENARIO_IDS.includes(s) ? s : 'R4',
    hour: Number.isInteger(h) && h >= 0 && h < 168 ? h : 37,
  }
}

let lastUrl = ''
function writeUrl(s: { view: View; scenario: ScenarioId; hour: number }) {
  const q = new URLSearchParams(window.location.search)
  q.set('view', s.view)
  q.set('scenario', s.scenario)
  q.set('hour', String(Math.floor(s.hour)))
  const next = `${window.location.pathname}?${q.toString()}`
  if (next !== lastUrl) {
    lastUrl = next
    window.history.replaceState(null, '', next)
  }
}

const init = readUrl()

export const useApp = create<AppState>((set, get) => ({
  model: null,
  error: null,
  view: init.view,
  scenario: init.scenario,
  hour: init.hour,
  playing: false,
  speed: 4,
  selectedNode: null,
  setModel: (model) => set({ model }),
  setError: (error) => set({ error }),
  setView: (view) => { set({ view }); writeUrl(get()) },
  setScenario: (scenario) => { set({ scenario }); writeUrl(get()) },
  setHour: (hour) => {
    const h = ((hour % 168) + 168) % 168
    const changed = Math.floor(h) !== Math.floor(get().hour)
    set({ hour: h })
    if (changed) writeUrl(get())
  },
  setPlaying: (playing) => set({ playing }),
  setSpeed: (speed) => set({ speed }),
  selectNode: (selectedNode) => set({ selectedNode }),
}))

writeUrl(useApp.getState())

/** Integer hour; components subscribing to this re-render once per simulated hour, not per frame. */
export const useHourIndex = () => useApp((s) => Math.floor(s.hour))
