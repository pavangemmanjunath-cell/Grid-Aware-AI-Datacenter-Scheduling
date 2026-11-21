import { useRef } from 'react'
import { useBenchmark, useDispatch, useJobs } from '../research/api'
import { Cite, hourLabel, Loading, Unavailable } from '../research/ui'
import { useApp, useHourIndex } from '../state/store'
import { Scrubber } from './Campus'

interface Line { label: string; color: string; values: number[]; dash?: string; area?: boolean; step?: boolean; width?: number }

const W = 1180, L = 64, R = 150, PH = 118, GAP = 34, LANE = 120
const IW = W - L - R
const x = (i: number) => L + (i / 167) * IW

function Panel({ top, title, unit, yMax, lines, marks = [] }: { top: number; title: string; unit: string; yMax: number; lines: Line[]; marks?: number[] }) {
  const y = (v: number) => top + PH - (Math.max(0, v) / yMax) * PH
  const path = (ln: Line) => ln.values.map((v, i) => {
    if (ln.step) return `${i ? 'L' : 'M'}${x(Math.max(0, i - 0.5)).toFixed(1)},${y(v).toFixed(1)}L${x(Math.min(167, i + 0.5)).toFixed(1)},${y(v).toFixed(1)}`
    return `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`
  }).join('')
  const ticks = [0, yMax / 2, yMax]
  return (
    <g>
      <text x={L} y={top - 10} fontSize={12.5} fontWeight={700} fill="var(--text-primary)">{title}</text>
      {ticks.map((t) => (
        <g key={t}>
          <line x1={L} x2={L + IW} y1={y(t)} y2={y(t)} stroke="var(--grid-line)" />
          <text x={L - 8} y={y(t) + 4} fontSize={10.5} textAnchor="end" fill="var(--text-muted)">{Number.isInteger(t) ? t : t.toFixed(1)}</text>
        </g>
      ))}
      {marks.map((m) => <line key={m} x1={L} x2={L + IW} y1={y(m)} y2={y(m)} stroke="var(--text-muted)" strokeDasharray="2 3" />)}
      <text x={18} y={top + PH / 2} fontSize={10.5} fill="var(--text-muted)" transform={`rotate(-90 18 ${top + PH / 2})`} textAnchor="middle">{unit}</text>
      {lines.filter((l) => l.area).map((l) => <path key={`a-${l.label}`} d={`${path(l)}L${x(167)},${y(0)}L${x(0)},${y(0)}Z`} fill={l.color} opacity={0.14} />)}
      {lines.map((l) => <path key={l.label} d={path(l)} fill="none" stroke={l.color} strokeWidth={l.width ?? 1.6} strokeDasharray={l.dash} />)}
      {/* direct labels at the right edge: identity never relies on colour alone */}
      {lines.map((l, k) => (
        <g key={`lab-${l.label}`}>
          <line x1={L + IW + 6} x2={L + IW + 22} y1={top + 12 + k * 16} y2={top + 12 + k * 16} stroke={l.color} strokeWidth={2.4} strokeDasharray={l.dash} />
          <text x={L + IW + 26} y={top + 16 + k * 16} fontSize={11} fill="var(--text-secondary)">{l.label}</text>
        </g>
      ))}
    </g>
  )
}

export function WeekReplayView() {
  const scenario = useApp((s) => s.scenario)
  const setHour = useApp((s) => s.setHour)
  const setPlaying = useApp((s) => s.setPlaying)
  const hour = useHourIndex()
  const bench = useBenchmark(), disp = useDispatch(scenario), jobs = useJobs(scenario)
  const ref = useRef<SVGSVGElement>(null)
  if (bench.isError || disp.isError || jobs.isError) return <Unavailable />
  if (!bench.data || !disp.data || !jobs.data) return <Loading />
  const b = bench.data.rows, d = disp.data.rows, j = jobs.data.rows
  const hasRen = scenario !== 'R0'
  const env = d.map((r) => r.envelope_MW)
  const tops = [30, 30 + PH + GAP, 30 + 2 * (PH + GAP), 30 + 3 * (PH + GAP)]
  const laneTop = tops[3] + PH + GAP + 6
  const H = laneTop + LANE
  const onMove = (e: React.PointerEvent) => {
    const r = ref.current!.getBoundingClientRect()
    const px = ((e.clientX - r.left) / r.width) * W
    const h = Math.round(((px - L) / IW) * 167)
    if (h >= 0 && h <= 167) { setPlaying(false); setHour(h) }
  }
  const moved = j.filter((r) => r.delay_h > 0)
  const windowBands = b.filter((r) => r.nonfirm_window && r.hour_of_day === 8).map((r) => r.hour)
  return (
    <div className="grid" style={{ gap: 12 }}>
      <div className="card">
        <h3><span>Week replay · {scenario} <span className="sub">hover to move the cursor across every panel and the Campus schematic</span></span>
          <span style={{ display: 'flex', gap: 6 }}><Cite anchor="Fig. 2" source="/api/benchmark" /><Cite anchor="Fig. 5" source={`/api/dispatch?scenario=${scenario}`} />
            <Cite anchor="Fig. 6" source={`/api/dispatch?scenario=${scenario}`} field="h2_inventory_MWh" /></span></h3>
        <svg ref={ref} viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', height: 'auto', touchAction: 'pan-y' }} onPointerMove={onMove} onPointerDown={onMove}
          role="img" aria-label={`168-hour replay for ${scenario}: load, renewables, grid import against the envelope, hydrogen inventory and job moves`}>
          {scenario === 'R4' && windowBands.map((h0) => (
            <rect key={h0} x={x(h0 - 0.5)} y={tops[2]} width={x(h0 + 6.5) - x(h0 - 0.5)} height={PH} fill="var(--c-limit)" opacity={0.07} />
          ))}
          <Panel top={tops[0]} title="(a) AI load" unit="MW" yMax={16} lines={[
            { label: 'fixed (latency-sensitive)', color: 'var(--c-load)', values: b.map((r) => r.fixed_ai_load_MW) },
            { label: 'flexible bundles', color: 'var(--c-jobs)', values: d.map((r) => r.flex_load_MW), step: true, area: true },
          ]} />
          <Panel top={tops[1]} title={`(b) On-site generation${hasRen ? '' : ' — not in R0'}`} unit="MW" yMax={10} lines={[
            { label: 'solar', color: 'var(--c-solar)', values: b.map((r) => (hasRen ? r.solar_MW : 0)), area: true },
            { label: 'wind', color: 'var(--c-wind)', values: b.map((r) => (hasRen ? r.wind_MW : 0)), dash: '6 3' },
          ]} />
          <Panel top={tops[2]} title="(c) Grid import against the connection envelope" unit="MW" yMax={16} lines={[
            { label: 'grid import', color: 'var(--c-grid)', values: d.map((r) => r.grid_import_MW), area: true },
            ...(env.every((v) => v != null) ? [{ label: 'envelope (limit)', color: 'var(--c-limit)', values: env as number[], step: true, dash: '6 3', width: 2 }] : []),
          ]} />
          <Panel top={tops[3]} title="(d) Hydrogen inventory" unit="MWh-H₂" yMax={20} marks={[0, 20]} lines={[
            { label: 'inventory', color: 'var(--c-h2)', values: d.map((r) => r.h2_inventory_MWh), area: true },
          ]} />
          {/* job lane */}
          <text x={L} y={laneTop - 8} fontSize={12.5} fontWeight={700} fill="var(--text-primary)">
            Job lane · {moved.length} of {j.length} bundles moved
          </text>
          {j.map((r, k) => {
            const yy = laneTop + 14 + (k % 4) * 24
            return (
              <g key={r.id}>
                <rect x={x(r.baseline_hour) - 5} y={yy - 7} width={10} height={14} rx={2}
                  fill={r.delay_h ? 'var(--surface-3)' : 'var(--c-jobs)'} stroke="var(--c-jobs)" />
                {r.delay_h > 0 && (
                  <>
                    <line x1={x(r.baseline_hour) + 5} x2={x(r.chosen_hour) - 7} y1={yy} y2={yy} stroke="var(--c-jobs)" strokeWidth={1.6} markerEnd="url(#arrow)" />
                    <rect x={x(r.chosen_hour) - 5} y={yy - 7} width={10} height={14} rx={2} fill="var(--c-jobs)" />
                    <text x={x(r.chosen_hour) + 8} y={yy + 4} fontSize={10} fill="var(--text-secondary)">+{r.delay_h} h</text>
                  </>
                )}
              </g>
            )
          })}
          <defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0L10,5L0,10z" fill="var(--c-jobs)" /></marker></defs>
          {/* shared axis + cursor */}
          {[0, 24, 48, 72, 96, 120, 144, 167].map((t) => (
            <text key={t} x={x(t)} y={H - 4} fontSize={10.5} textAnchor="middle" fill="var(--text-muted)">{t}</text>
          ))}
          <line x1={x(hour)} x2={x(hour)} y1={16} y2={H - 16} stroke="var(--text-primary)" strokeWidth={1.2} opacity={0.65} />
          <text x={Math.min(x(hour) + 6, W - R - 90)} y={22} fontSize={11.5} fontWeight={700} fill="var(--text-primary)">h {hour} · {hourLabel(hour)}</text>
        </svg>
        <div className="caption">
          Grid import at h {hour}: {d[hour].grid_import_MW.toFixed(2)} MW{d[hour].envelope_MW != null ? ` / envelope ${d[hour].envelope_MW!.toFixed(2)} MW` : ''} ·
          H₂ {d[hour].h2_inventory_MWh.toFixed(2)} MWh-H₂ · hours above the envelope:{' '}
          <b>{d.filter((r) => r.envelope_MW != null && r.grid_import_MW > r.envelope_MW + 1e-6).length}</b>
          <Cite anchor="Fig. 5" source={disp.data.source} field={['grid_import_MW', 'envelope_MW', 'h2_inventory_MWh', 'flex_load_MW']} />
        </div>
      </div>
      <Scrubber />
    </div>
  )
}
