import { lazy, Suspense, useEffect, useRef, useState } from 'react'
import { useBenchmark, useComponent, useDispatch, useJobs, useScenarios, type ComponentDetail, type ScenarioRow } from '../research/api'
import { Cite, hourLabel, Loading, ranges, Sparkline, Unavailable } from '../research/ui'
import { useApp, useHourIndex, type View } from '../state/store'
import { ComponentGraph } from './ComponentGraph'

const Campus3D = lazy(() => import('./Campus3D'))

// ---------------------------------------------------------------- KPI cards --
export function KpiCards({ compact = false }: { compact?: boolean }) {
  const scenario = useApp((s) => s.scenario)
  const setView = useApp((s) => s.setView)
  const q = useScenarios()
  if (q.isError) return <div className="card"><Unavailable /></div>
  if (!q.data) return <Loading />
  const rows = Object.fromEntries(q.data.map((r) => [r.id, r])) as Record<string, ScenarioRow>
  const r = rows[scenario], r0 = rows.R0
  const envelope = r.kind === 'imposed_envelope'
  const cards: { key: string; label: string; value: string; delta: string; tip: string; field: string | string[]; to: View; state?: 'ok' | 'bad' }[] = [
    { key: 'c', label: r.capacity_label, value: `${r.connection_capacity_MW.toFixed(2)} MW`,
      delta: scenario === 'R0' ? 'grid-only reference' : `R0 ${r0.connection_capacity_MW.toFixed(2)} MW`,
      tip: envelope ? 'Peak import observed under the imposed envelope; not a capacity search, so not a minimum connection.'
        : scenario === 'R0' || scenario === 'R1' ? 'Peak import with no cap: without storage or flexibility this is the firm connection required.'
          : 'Smallest uniform import cap that serves all load (bisection, 24 steps).',
      field: 'connection_capacity_MW', to: 'connection' },
    { key: 'r', label: 'Connection relief', value: `${r.capacity_reduction_pct.toFixed(1)} %`, delta: '(C of R0 − C) ÷ C of R0',
      tip: 'Reduction of the figure above against the grid-only reference R0.', field: 'capacity_reduction_pct', to: 'connection' },
    { key: 'v', label: 'Unserved energy · envelope violation', value: `${r.violation_energy_MWh.toFixed(2)} MWh`,
      delta: r.violation_energy_MWh === 0 ? '✓ zero in this scenario' : 'non-zero: schedule breaches the envelope',
      tip: 'Energy imported above the envelope; every optimised schedule also has zero unserved energy.',
      field: 'violation_energy_MWh', to: 'week', state: r.violation_energy_MWh === 0 ? 'ok' : 'bad' },
    { key: 'co2', label: 'Grid CO₂ (168 h)', value: `${r.operational_CO2_t.toFixed(2)} t`,
      delta: scenario === 'R0' ? 'reference' : `−${(100 * (1 - r.operational_CO2_t / r0.operational_CO2_t)).toFixed(1)} % vs R0 ${r0.operational_CO2_t.toFixed(2)} t`,
      tip: 'Operational emissions of grid imports weighted by hourly carbon intensity.', field: 'operational_CO2_t', to: 'week' },
    { key: 'd', label: 'Compute deferred', value: `${r.jobs_shifted_pct.toFixed(1)} % · ${r.average_workload_delay_h.toFixed(2)} h`,
      delta: 'share of 28 flexible bundles moved · mean delay', tip: 'Delay-tolerant bundles moved to +3 h or +7 h slots.',
      field: ['jobs_shifted_pct', 'average_workload_delay_h'], to: 'week' },
  ]
  return (
    <div className="grid" style={{ gap: 10 }} data-testid="kpi-cards">
      {cards.map((c) => (
        <div key={c.key} role="button" tabIndex={0} className={`kpi ${c.state ?? ''}`} title={c.tip} data-testid="kpi"
          aria-label={`${c.label}: ${c.value}. Open the ${c.to} view`}
          onClick={() => setView(c.to)} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setView(c.to) } }}>
          <span className="k-label"><span>{c.label}</span><Cite anchor="Table 2" source="data/research_results_gridflex.csv" field={c.field} /></span>
          <span className="k-value">{c.state === 'ok' && <span className="check" aria-label="passes">✓ </span>}{c.value}</span>
          {!compact && <span className="k-delta">{c.delta}</span>}
        </div>
      ))}
    </div>
  )
}

// ------------------------------------------------------------ hour scrubber --
export function Scrubber() {
  const hour = useHourIndex()
  const { playing, speed } = { playing: useApp((s) => s.playing), speed: useApp((s) => s.speed) }
  const setHour = useApp((s) => s.setHour), setPlaying = useApp((s) => s.setPlaying), setSpeed = useApp((s) => s.setSpeed)
  const bench = useBenchmark()
  const raf = useRef(0)
  useEffect(() => {
    if (!playing) return
    let last = performance.now()
    const tick = (t: number) => {
      const s = useApp.getState()
      s.setHour(s.hour + ((t - last) / 1000) * s.speed)
      last = t
      raf.current = requestAnimationFrame(tick)
    }
    raf.current = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf.current)
  }, [playing])
  const win = bench.data?.rows[hour]?.nonfirm_window
  return (
    <div className="card scrubber" data-testid="scrubber">
      <button className="btn" onClick={() => setPlaying(!playing)} aria-label={playing ? 'Pause' : 'Play'}>{playing ? '❚❚ Pause' : '▶ Play'}</button>
      <input type="range" min={0} max={167} value={hour} aria-label="Hour of the 168-hour week"
        onChange={(e) => { setPlaying(false); setHour(Number(e.target.value)) }} />
      <span className="mono" style={{ minWidth: 150 }}>h {hour} · {hourLabel(hour)}</span>
      <span className={`chip-win ${win ? '' : 'off'}`} title="Non-firm contraction window, hours 08–14 (7 h; binding in R4)">
        {win ? 'non-firm window active' : 'non-firm window inactive'}
      </span>
      <div className="seg" role="group" aria-label="Playback speed">
        {[1, 4, 12].map((s) => <button key={s} aria-pressed={speed === s} onClick={() => setSpeed(s)}>{s} h/s</button>)}
      </div>
    </div>
  )
}

// ------------------------------------------------------ ask the component --
const QUESTIONS = [
  'What is your consumption (or output) now?',
  'What was your peak this week, and when?',
  'What is your total over the 168 hours?',
  'When were you limited by the connection envelope or by capacity?',
]

function answer(c: ComponentDetail, q: number, hour: number): string {
  const now = c.series[hour]
  if (!c.in_scenario) return `${c.label} is not part of scenario ${c.scenario}.`
  const u = c.unit
  switch (q) {
    case 0:
      if (c.id === 'bus') return `Balance residual (supply − demand) is ${now?.toFixed(2)} MW at hour ${hour} (${hourLabel(hour)}).`
      return `${now?.toFixed(2)} ${u} at hour ${hour} (${hourLabel(hour)}).` +
        (c.id === 'grid' && c.extra_series.envelope_MW?.[hour] != null ? ` Envelope ${c.extra_series.envelope_MW[hour]?.toFixed(2)} MW.` : '')
    case 1:
      if (c.id === 'bus') return `Largest absolute residual over the week: ${Math.abs(c.peak.value).toFixed(2)} MW — the balance closes every hour.`
      return `Peak ${c.peak.value.toFixed(2)} ${u} at hour ${c.peak.hour} (${hourLabel(c.peak.hour)}).`
    case 2:
      if (c.id === 'tank') return `Inventory is a level, not a flow; its 168-h sum is ${c.week_total.toFixed(1)} MWh-H₂·h. It starts and ends at 5 MWh-H₂.`
      if (c.id === 'bus') return `The residual sums to ${c.week_total.toFixed(3)} MWh: the balance closes every hour.`
      return `${c.week_total.toFixed(2)} ${c.week_total_unit} over 168 h` + (c.share_pct != null ? `, ${c.share_pct.toFixed(1)} % of campus ${c.share_basis}.` : '.')
    default:
      if (!c.limit_reason) return 'This component has no capacity or envelope limit in the model.'
      return c.limited_hours.length ? `${c.limit_reason} in ${c.limited_hours.length} h: hours ${ranges(c.limited_hours)}.` : `Never ${c.limit_reason} in ${c.scenario}.`
  }
}

function SideCard() {
  const node = useApp((s) => s.selectedNode)
  const select = useApp((s) => s.selectNode)
  const scenario = useApp((s) => s.scenario)
  const hour = useHourIndex()
  const [q, setQ] = useState<number | null>(0)
  const c = useComponent(node, scenario, hour)
  if (!node) {
    return (
      <div className="card">
        <h3>Ask a component</h3>
        <p style={{ fontSize: 13.5 }}>Click any box in the schematic to see what it consumes or produces at this hour, its 168-h profile and
          four answers read from the API, each with the endpoint and field it came from.</p>
      </div>
    )
  }
  if (c.isError) return <div className="card"><h3>{node}</h3><Unavailable /></div>
  if (!c.data) return <div className="card"><Loading /></div>
  const d = c.data
  const color = { grid: 'var(--c-grid)', solar: 'var(--c-solar)', wind: 'var(--c-wind)', job_queue: 'var(--c-jobs)',
    electrolyser: 'var(--c-h2)', tank: 'var(--c-h2)', fuel_cell: 'var(--c-h2)' }[d.id] ?? 'var(--text-secondary)'
  const endpoint = `/api/components/${d.id}?scenario=${scenario}&hour=${hour}`
  return (
    <div className="card side-card" data-testid="side-card">
      <h3><span>{d.label}</span><button className="icon-btn" onClick={() => select(null)} aria-label="Close">✕</button></h3>
      <div className="k-value" style={{ fontSize: '1.5rem', fontWeight: 700 }} data-testid="side-value">
        {d.series[hour]?.toFixed(2)} <span style={{ fontSize: 14, color: 'var(--text-muted)' }}>{d.unit} at hour {hour}</span>
      </div>
      <Sparkline values={d.series} hour={hour} color={color} />
      <dl className="readout" style={{ marginTop: 6 }}>
        <dt>Week total</dt><dd>{d.week_total.toFixed(2)} {d.week_total_unit}</dd>
        {d.share_pct != null && <><dt>Share of campus {d.share_basis}</dt><dd>{d.share_pct.toFixed(1)} %</dd></>}
        <dt>Peak</dt><dd>{d.peak.value.toFixed(2)} at h {d.peak.hour}</dd>
      </dl>
      <div className="caption"><Cite anchor="Fig. 1" source={d.source_files.join(', ')} field={d.fields} /> {d.in_scenario ? '' : `not in ${scenario}`}</div>
      <div className="qa" style={{ marginTop: 10 }}>
        {QUESTIONS.map((t, i) => <button key={t} aria-pressed={q === i} onClick={() => setQ(i)}>{t}</button>)}
      </div>
      {q !== null && (
        <div className="answer" data-testid="answer">
          {answer(d, q, hour)}
          <div className="ev">GET {endpoint} · field {q === 3 ? 'limited_hours' : q === 1 ? 'peak' : q === 2 ? 'week_total' : d.fields[0]}</div>
        </div>
      )}
      <p style={{ fontSize: 11.5, marginTop: 8 }}>A free-text assistant can be added later; it must answer only from these endpoints, name the field it used,
        and say “not in the model” otherwise.</p>
    </div>
  )
}

// --------------------------------------------------------------- the view --
export function CampusView() {
  const scenario = useApp((s) => s.scenario)
  const selected = useApp((s) => s.selectedNode)
  const select = useApp((s) => s.selectNode)
  const hour = useHourIndex()
  const [mode, setMode] = useState<'schematic' | '3d'>('schematic')
  const bench = useBenchmark(), disp = useDispatch(scenario), jobs = useJobs(scenario)
  const ok = bench.data && disp.data && jobs.data
  return (
    <div className="grid" style={{ gap: 16 }}>
      <div className="layout-12">
        <div className="span-8 grid" style={{ gap: 12 }}>
          <div className="card">
            <h3>
              <span>Campus at hour {hour} <span className="sub">{hourLabel(hour)} · {scenario}</span></span>
              <span className="seg" role="group" aria-label="Visual">
                <button aria-pressed={mode === 'schematic'} onClick={() => setMode('schematic')}>Schematic</button>
                <button aria-pressed={mode === '3d'} onClick={() => setMode('3d')}>3D (WebGL)</button>
              </span>
            </h3>
            {mode === 'schematic' ? (
              (bench.isError || disp.isError || jobs.isError) ? <Unavailable /> : !ok ? <Loading /> : (
                <ComponentGraph scenario={scenario} hour={hour} bench={bench.data.rows[hour]} disp={disp.data.rows[hour]}
                  jobs={jobs.data.rows} selected={selected} onSelect={(id) => select(id)} />
              )
            ) : (
              <Suspense fallback={<Loading>Loading 3D scene…</Loading>}><Campus3D /></Suspense>
            )}
            <div className="caption">
              <Cite anchor="Fig. 1" source={`/api/dispatch?scenario=${scenario} · /api/benchmark`} />
              Balance every hour: grid + fuel cell + solar + wind = AI load + electrolyser + curtailment. Edge width ∝ MW; dashed = 0 MW.
            </div>
          </div>
          <Scrubber />
        </div>
        <div className="span-4 grid" style={{ gap: 12, alignContent: 'start' }}>
          <KpiCards />
          <SideCard />
        </div>
      </div>
    </div>
  )
}
