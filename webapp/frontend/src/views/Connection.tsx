import { useDispatch, useJobs, useScenarios, type ScenarioId, type ScenarioRow } from '../research/api'
import { Cite, Loading, Unavailable } from '../research/ui'
import { KpiCards } from './Campus'

/** Waterfall R0 -> R3. Every bar is computed from /api/scenarios; nothing is typed in. */
function Bridge({ rows }: { rows: Record<string, ScenarioRow> }) {
  const c = (k: string) => rows[k].connection_capacity_MW
  const steps = [
    { label: 'R0 grid only', kind: 'total', from: 0, to: c('R0') },
    { label: 'Renewables', kind: 'step', from: c('R0'), to: c('R1') },
    { label: 'Green hydrogen', kind: 'step', from: c('R1'), to: c('R2') },
    { label: 'Workload flexibility', kind: 'step', from: c('R2'), to: c('R3') },
    { label: 'R3 all three', kind: 'total', from: 0, to: c('R3') },
  ]
  const W = 760, H = 330, M = { t: 28, r: 16, b: 56, l: 48 }
  const iw = W - M.l - M.r, ih = H - M.t - M.b, top = 16
  const bw = iw / steps.length
  const y = (v: number) => M.t + ih - (v / top) * ih
  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', height: 'auto' }} role="img"
      aria-label={`Capacity bridge from ${c('R0').toFixed(2)} MW to ${c('R3').toFixed(2)} MW`}>
      {[0, 4, 8, 12, 16].map((t) => (
        <g key={t}>
          <line x1={M.l} x2={W - M.r} y1={y(t)} y2={y(t)} stroke="var(--grid-line)" />
          <text x={M.l - 8} y={y(t) + 4} fontSize={11} textAnchor="end" fill="var(--text-muted)">{t}</text>
        </g>
      ))}
      <text x={14} y={M.t + ih / 2} fontSize={11} fill="var(--text-muted)" transform={`rotate(-90 14 ${M.t + ih / 2})`} textAnchor="middle">MW</text>
      {steps.map((s, i) => {
        const x = M.l + i * bw + bw * 0.18, w = bw * 0.64
        const hi = Math.max(s.from, s.to), lo = Math.min(s.from, s.to)
        const isTotal = s.kind === 'total'
        const fill = isTotal ? 'var(--c-grid)' : 'var(--c-jobs)'
        const val = isTotal ? `${s.to.toFixed(2)} MW` : `−${(s.from - s.to).toFixed(2)} MW`
        return (
          <g key={s.label}>
            <rect x={x} y={y(hi)} width={w} height={Math.max(1, y(lo) - y(hi))} rx={3} fill={fill} opacity={isTotal ? 0.85 : 0.9}
              {...(isTotal ? {} : { stroke: 'var(--c-jobs)' })} />
            {i < steps.length - 1 && (
              <line x1={x + w} x2={M.l + (i + 1) * bw + bw * 0.18} y1={y(s.to)} y2={y(s.to)} stroke="var(--text-muted)" strokeDasharray="3 3" />
            )}
            <text x={x + w / 2} y={y(hi) - 7} fontSize={12.5} fontWeight={700} textAnchor="middle" fill="var(--text-primary)">{val}</text>
            <text x={x + w / 2} y={H - 30} fontSize={12} textAnchor="middle" fill="var(--text-secondary)" fontWeight={600}>{s.label}</text>
            {!isTotal && <text x={x + w / 2} y={H - 14} fontSize={11} textAnchor="middle" fill="var(--text-muted)">
              −{((100 * (s.from - s.to)) / c('R0')).toFixed(1)} % of R0</text>}
          </g>
        )
      })}
    </svg>
  )
}

function EnvelopePanel({ id, row }: { id: ScenarioId; row: ScenarioRow }) {
  const d = useDispatch(id), j = useJobs(id)
  if (d.isError || j.isError) return <div className="card"><Unavailable /></div>
  if (!d.data || !j.data) return <div className="card"><Loading /></div>
  const rows = d.data.rows
  const W = 360, H = 120
  const x = (i: number) => (i / 167) * W
  const y = (v: number) => H - 6 - (v / 12) * (H - 12)
  const imp = rows.map((r, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(r.grid_import_MW).toFixed(1)}`).join('')
  const env = rows.map((r, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(r.envelope_MW ?? 0).toFixed(1)}`).join('')
  const moved = j.data.rows.filter((r) => r.delay_h > 0).length
  return (
    <div className="card" data-testid={`envelope-${id}`}>
      <h3><span>{id} · {row.label}</span><Cite anchor="Table 2" source="data/research_results_gridflex.csv" field="connection_capacity_MW" /></h3>
      <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', height: 'auto' }} role="img" aria-label={`${id} grid import against its envelope`}>
        <path d={imp} fill="none" stroke="var(--c-grid)" strokeWidth={1.4} />
        <path d={env} fill="none" stroke="var(--c-limit)" strokeWidth={1.6} strokeDasharray="5 3" />
      </svg>
      <div className="legend"><span><i className="line-key" style={{ borderTopColor: 'var(--c-grid)' }} />grid import</span>
        <span><i className="line-key" style={{ borderTopColor: 'var(--c-limit)', borderTopStyle: 'dashed' }} />envelope (limit)</span></div>
      <dl className="readout">
        <dt>Peak import under the imposed envelope</dt><dd>{row.connection_capacity_MW.toFixed(2)} MW</dd>
        <dt>Bundles moved</dt><dd>{moved} of {j.data.rows.length}</dd>
        <dt>Envelope violation</dt><dd>{row.violation_energy_MWh.toFixed(2)} MWh {row.violation_energy_MWh === 0 && <span className="check">✓</span>}</dd>
      </dl>
      <div className="caption"><Cite anchor="Fig. 5" source={`/api/dispatch?scenario=${id} · /api/jobs?scenario=${id}`} field={['grid_import_MW', 'envelope_MW', 'delay_h']} /></div>
    </div>
  )
}

export function ConnectionView() {
  const q = useScenarios()
  if (q.isError) return <Unavailable />
  if (!q.data) return <Loading />
  const rows = Object.fromEntries(q.data.map((r) => [r.id, r])) as Record<string, ScenarioRow>
  return (
    <div className="layout-12">
      <div className="span-8 grid" style={{ gap: 12 }}>
        <div className="card">
          <h3><span>Capacity bridge · R0 → R3 <span className="sub">smallest feasible uniform connection</span></span>
            <Cite anchor="Fig. 4" source="/api/scenarios" field="connection_capacity_MW" /></h3>
          <Bridge rows={rows} />
          <p style={{ fontSize: 13.5, marginTop: 6 }}>The three resources act at different timescales — renewables lower the average, hydrogen
            shifts energy across the day, flexibility clears the few hours that set the peak — so they are complementary, not interchangeable
            (paper, Discussion). The steps are a sequential decomposition, not a factorial attribution.</p>
        </div>
        <div className="layout-12">
          <div className="span-6"><EnvelopePanel id="R4" row={rows.R4} /></div>
          <div className="span-6"><EnvelopePanel id="R5" row={rows.R5} /></div>
        </div>
      </div>
      <div className="span-4"><KpiCards compact /></div>
    </div>
  )
}
