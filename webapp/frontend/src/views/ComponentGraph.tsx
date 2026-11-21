// Engineering schematic of one AI campus (not a map). Nine nodes, nine edges, fixed positions:
// only the values change, so the eye learns the layout once. Every value is read from
// /api/dispatch, /api/benchmark and /api/jobs for the selected scenario and hour.
import type { BenchmarkRow, DispatchRow, JobRow, ScenarioId } from '../research/api'

interface Props {
  scenario: ScenarioId
  hour: number
  bench: BenchmarkRow
  disp: DispatchRow
  jobs: JobRow[]
  selected: string | null
  onSelect: (id: string) => void
}

const W = 960, H = 560
const BOX: Record<string, [number, number, number, number]> = {
  grid: [30, 60, 190, 96], solar: [30, 232, 190, 96], wind: [30, 404, 190, 96],
  bus: [400, 40, 50, 470], job_queue: [720, 36, 210, 92], data_hall: [720, 200, 210, 104],
  fuel_cell: [510, 296, 160, 88], electrolyser: [510, 432, 160, 88], tank: [720, 420, 210, 112],
}
const COLOR: Record<string, string> = {
  grid: 'var(--c-grid)', solar: 'var(--c-solar)', wind: 'var(--c-wind)', bus: 'var(--text-secondary)',
  data_hall: 'var(--c-load)', job_queue: 'var(--c-jobs)', electrolyser: 'var(--c-h2)', tank: 'var(--c-h2)', fuel_cell: 'var(--c-h2)',
}

const fmt = (v: number) => (Math.abs(v) < 0.005 ? '0.00' : v.toFixed(2))

function Edge({ d, mw, color, label, lx, ly, unit = 'MW' }: { d: string; mw: number; color: string; label: string; lx: number; ly: number; unit?: string }) {
  const on = mw > 0.005
  const w = on ? 1.5 + (9 * Math.min(mw, 16)) / 16 : 1
  const dur = on ? Math.min(6, Math.max(0.5, 5 / mw)) : 0
  return (
    <g>
      <path d={d} fill="none" stroke={color} strokeWidth={w} strokeOpacity={on ? 0.35 : 0.5} strokeDasharray={on ? undefined : '4 4'} />
      {on && (
        <path d={d} fill="none" stroke={color} strokeWidth={Math.max(3, w * 0.7)} strokeLinecap="round"
          strokeDasharray="0.1 11.9" className="flow-dots" style={{ animationDuration: `${dur}s` }} />
      )}
      <text x={lx} y={ly} fontSize={11.5} fill="var(--text-secondary)" textAnchor="middle" fontWeight={600}>
        {label} {fmt(mw)} {unit}
      </text>
    </g>
  )
}

function Node({ id, title, lines, selected, onSelect, dim, children }: {
  id: string; title: string; lines: string[]; selected: boolean; onSelect: (id: string) => void; dim?: boolean; children?: React.ReactNode
}) {
  const [x, y, w, h] = BOX[id]
  return (
    <g className="node-box" tabIndex={0} role="button" aria-label={`${title}: ${lines.join(', ')}. Open details`}
      onClick={() => onSelect(id)} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onSelect(id) } }}
      opacity={dim ? 0.45 : 1} data-node={id}>
      <rect className="frame" x={x} y={y} width={w} height={h} rx={10} fill="var(--surface-1)"
        stroke={selected ? 'var(--accent)' : 'var(--border)'} strokeWidth={selected ? 2.5 : 1.2} />
      <rect x={x} y={y} width={6} height={h} rx={3} fill={COLOR[id]} />
      <text x={x + 16} y={y + 22} fontSize={13.5} fontWeight={700} fill="var(--text-primary)">{title}</text>
      {lines.map((l, i) => (
        <text key={i} x={x + 16} y={y + 42 + i * 17} fontSize={12.5} fill="var(--text-secondary)" style={{ fontVariantNumeric: 'tabular-nums' }}>{l}</text>
      ))}
      {children}
    </g>
  )
}

export function ComponentGraph({ scenario, hour, bench, disp, jobs, selected, onSelect }: Props) {
  const hasRen = scenario !== 'R0'
  const hasH2 = ['R2', 'R3', 'R4', 'R5'].includes(scenario)
  const solar = hasRen ? bench.solar_MW : 0
  const wind = hasRen ? bench.wind_MW : 0
  const g = disp.grid_import_MW, env = disp.envelope_MW
  const supply = g + disp.fuel_cell_MW + solar + wind
  const demand = bench.fixed_ai_load_MW + disp.flex_load_MW + disp.electrolyser_MW + disp.curtailment_MW
  const residual = supply - demand
  const running = jobs.filter((j) => j.chosen_hour === hour)
  const ratio = env ? g / env : null
  const needle = ratio === null ? 0 : Math.min(1.1, ratio)
  const meterColor = ratio !== null && ratio > 0.95 ? 'var(--c-limit)' : 'var(--c-grid)'
  const inv = disp.h2_inventory_MWh
  const [tx, ty, tw, th] = BOX.tank

  // gauge geometry (grid node)
  const gx = BOX.grid[0] + 160, gy = BOX.grid[1] + 74, gr = 22
  const ang = Math.PI * (1 - Math.min(1, needle))
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="graph" style={{ width: '100%', height: 'auto', display: 'block' }} role="group"
      aria-label={`Component graph of the campus for ${scenario} at hour ${hour}`}>
      {/* edges (drawn first) */}
      <Edge d="M220,108 L400,108" mw={g} color="var(--c-grid)" label="import" lx={310} ly={98} />
      <Edge d="M220,280 L400,280" mw={solar} color="var(--c-solar)" label="solar" lx={310} ly={270} />
      <Edge d="M220,452 L400,452" mw={wind} color="var(--c-wind)" label="wind" lx={310} ly={442} />
      <Edge d="M510,340 L450,340" mw={disp.fuel_cell_MW} color="var(--c-h2)" label="" lx={480} ly={330} />
      <Edge d="M450,240 L720,240" mw={bench.fixed_ai_load_MW} color="var(--c-load)" label="fixed AI load" lx={585} ly={230} />
      <Edge d="M825,128 L825,200" mw={disp.flex_load_MW} color="var(--c-jobs)" label="flexible" lx={868} ly={170} />
      <Edge d="M450,476 L510,476" mw={disp.electrolyser_MW} color="var(--c-h2)" label="" lx={480} ly={466} />
      <Edge d="M670,476 L720,476" mw={0.72 * disp.electrolyser_MW} color="var(--c-h2)" label="H₂" lx={695} ly={466} unit="MWh/h" />
      <Edge d="M825,420 L825,340 L670,340" mw={disp.fuel_cell_MW / 0.55} color="var(--c-h2)" label="H₂" lx={760} ly={330} unit="MWh/h" />

      {/* nodes */}
      <Node id="grid" title="Grid connection" selected={selected === 'grid'} onSelect={onSelect}
        lines={[`import ${fmt(g)} MW`, env ? `envelope ${fmt(env)} MW` : 'no envelope (peak sets C)', env ? `headroom ${fmt(env - g)} MW` : '']}>
        <path d={`M${gx - gr},${gy} A${gr},${gr} 0 0 1 ${gx + gr},${gy}`} fill="none" stroke="var(--surface-3)" strokeWidth={6} />
        {ratio !== null && <path d={`M${gx - gr},${gy} A${gr},${gr} 0 0 1 ${gx + gr * Math.cos(ang)},${gy - gr * Math.sin(ang)}`} fill="none" stroke={meterColor} strokeWidth={6} />}
        <line x1={gx} y1={gy} x2={gx + (gr - 4) * Math.cos(ang)} y2={gy - (gr - 4) * Math.sin(ang)} stroke={meterColor} strokeWidth={2.5} />
        <text x={gx} y={gy + 14} fontSize={10.5} textAnchor="middle" fill={meterColor} fontWeight={700}>{ratio === null ? 'n/a' : `${Math.round(ratio * 100)}%`}</text>
      </Node>
      <Node id="solar" title="Solar PV" dim={!hasRen} selected={selected === 'solar'} onSelect={onSelect}
        lines={hasRen ? [`output ${fmt(solar)} MW`, `curtailed (all RE) ${fmt(disp.curtailment_MW)} MW`] : ['not in R0']} />
      <Node id="wind" title="Wind" dim={!hasRen} selected={selected === 'wind'} onSelect={onSelect}
        lines={hasRen ? [`output ${fmt(wind)} MW`] : ['not in R0']} />
      <g className="node-box" tabIndex={0} role="button" aria-label={`Campus bus: balance residual ${fmt(residual)} MW. Open details`} data-node="bus"
        onClick={() => onSelect('bus')} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onSelect('bus') } }}>
        <rect className="frame" x={400} y={40} width={50} height={470} rx={8} fill="var(--surface-2)" stroke={selected === 'bus' ? 'var(--accent)' : 'var(--border)'} strokeWidth={selected === 'bus' ? 2.5 : 1.2} />
        <text x={425} y={30} fontSize={12.5} fontWeight={700} textAnchor="middle" fill="var(--text-primary)">Campus bus</text>
        <text x={425} y={528} fontSize={11.5} textAnchor="middle" fill={Math.abs(residual) < 0.005 ? 'var(--status-good)' : 'var(--status-critical)'} fontWeight={700}>
          residual {fmt(residual)} MW
        </text>
        <text x={425} y={546} fontSize={10.5} textAnchor="middle" fill="var(--text-muted)">supply {fmt(supply)} = demand {fmt(demand)}</text>
      </g>
      <Node id="job_queue" title="Flexible job queue" selected={selected === 'job_queue'} onSelect={onSelect}
        lines={[`running now ${fmt(disp.flex_load_MW)} MW`, running.length ? `bundle #${running.map((j) => j.id).join(', #')}${running.some((j) => j.delay_h) ? ' (moved)' : ''}` : 'no bundle this hour']} />
      <Node id="data_hall" title="AI data hall" selected={selected === 'data_hall'} onSelect={onSelect}
        lines={[`load ${fmt(bench.fixed_ai_load_MW + disp.flex_load_MW)} MW`, `fixed ${fmt(bench.fixed_ai_load_MW)} · flexible ${fmt(disp.flex_load_MW)}`, 'latency-sensitive + delay-tolerant']} />
      <Node id="fuel_cell" title="Fuel cell" dim={!hasH2} selected={selected === 'fuel_cell'} onSelect={onSelect}
        lines={hasH2 ? [`output ${fmt(disp.fuel_cell_MW)} MW`, `of 2 MW rated`] : ['not in this scenario']} />
      <Node id="electrolyser" title="Electrolyser" dim={!hasH2} selected={selected === 'electrolyser'} onSelect={onSelect}
        lines={hasH2 ? [`intake ${fmt(disp.electrolyser_MW)} MW`, `of 4 MW rated`] : ['not in this scenario']} />
      <Node id="tank" title="Hydrogen tank" dim={!hasH2} selected={selected === 'tank'} onSelect={onSelect}
        lines={hasH2 ? [`${fmt(inv)} MWh-H₂`, `${Math.round((inv / 20) * 100)}% of 20 MWh-H₂`] : ['not in this scenario']}>
        <rect x={tx + tw - 34} y={ty + 12} width={20} height={th - 24} rx={4} fill="var(--surface-2)" stroke="var(--border)" />
        <rect x={tx + tw - 34} y={ty + 12 + (th - 24) * (1 - Math.min(1, inv / 20))} width={20} height={(th - 24) * Math.min(1, inv / 20)} rx={4} fill="var(--c-h2)" opacity={0.8} />
      </Node>
    </svg>
  )
}
