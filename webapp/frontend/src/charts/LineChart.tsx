import { useMemo, useRef, useState } from 'react'

export interface LineSeries {
  id: string
  label: string
  color: string // CSS colour or var(--token)
  values: (number | null)[]
  step?: boolean
  dashed?: boolean
  area?: boolean
  unit?: string
}

interface Props {
  series: LineSeries[]
  height?: number
  yLabel: string
  yMax?: number
  xStart?: number
  xEnd?: number
  playhead?: number
  bands?: { from: number; to: number; color: string }[]
  onScrub?: (hour: number) => void
  ariaLabel: string
}

const W = 760
const M = { top: 8, right: 12, bottom: 28, left: 44 }

// One y-axis only (no dual axes). Hover crosshair + tooltip; click/drag scrubs the timeline.
export function LineChart({ series, height = 220, yLabel, yMax, xStart = 0, xEnd, playhead, bands, onScrub, ariaLabel }: Props) {
  const n = series[0]?.values.length ?? 0
  const x1 = xEnd ?? n - 1
  const innerW = W - M.left - M.right
  const innerH = height - M.top - M.bottom
  const ref = useRef<SVGSVGElement>(null)
  const [hover, setHover] = useState<number | null>(null)

  const top = useMemo(() => {
    if (yMax) return yMax
    let m = 0
    for (const s of series) for (let i = xStart; i <= x1; i++) m = Math.max(m, s.values[i] ?? 0)
    const step = m > 20 ? 5 : m > 8 ? 2 : 1
    return Math.ceil((m * 1.08) / step) * step || 1
  }, [series, yMax, xStart, x1])

  const x = (i: number) => M.left + ((i - xStart) / Math.max(1, x1 - xStart)) * innerW
  const y = (v: number) => M.top + innerH - (v / top) * innerH
  const ticksY = Array.from({ length: 5 }, (_, k) => (top * k) / 4)
  const span = x1 - xStart
  const tickStep = span > 100 ? 24 : span > 40 ? 6 : 3
  const ticksX: number[] = []
  for (let i = Math.ceil(xStart / tickStep) * tickStep; i <= x1; i += tickStep) ticksX.push(i)

  const path = (s: LineSeries) => {
    let d = ''
    let pen = false
    for (let i = xStart; i <= x1; i++) {
      const v = s.values[i]
      if (v === null || v === undefined || !Number.isFinite(v)) { pen = false; continue }
      if (s.step) {
        const xa = x(i - 0.5 < xStart ? xStart : i - 0.5), xb = x(i + 0.5 > x1 ? x1 : i + 0.5)
        d += `${pen ? 'L' : 'M'}${xa.toFixed(1)},${y(v).toFixed(1)}L${xb.toFixed(1)},${y(v).toFixed(1)}`
      } else {
        d += `${pen ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`
      }
      pen = true
    }
    return d
  }

  const idxFromEvent = (e: React.PointerEvent) => {
    const r = ref.current!.getBoundingClientRect()
    const px = ((e.clientX - r.left) / r.width) * W
    const i = Math.round(xStart + ((px - M.left) / innerW) * (x1 - xStart))
    return Math.min(x1, Math.max(xStart, i))
  }

  return (
    <div className="chart">
      <div className="legend" aria-hidden>
        {series.map((s) => (
          <span key={s.id}>
            <i className="line-key" style={{ borderTopColor: s.color, borderTopStyle: s.dashed ? 'dashed' : 'solid' }} />
            {s.label}
          </span>
        ))}
      </div>
      <svg
        ref={ref}
        viewBox={`0 0 ${W} ${height}`}
        role="img"
        aria-label={ariaLabel}
        onPointerMove={(e) => {
          const i = idxFromEvent(e)
          setHover(i)
          if (e.buttons === 1 && onScrub) onScrub(i)
        }}
        onPointerDown={(e) => onScrub?.(idxFromEvent(e))}
        onPointerLeave={() => setHover(null)}
        style={{ cursor: onScrub ? 'pointer' : 'crosshair', touchAction: 'pan-y' }}
      >
        {bands?.map((b, k) => (
          <rect key={k} x={x(Math.max(xStart, b.from - 0.5))} width={Math.max(0, x(Math.min(x1, b.to + 0.5)) - x(Math.max(xStart, b.from - 0.5)))}
            y={M.top} height={innerH} fill={b.color} />
        ))}
        <g className="axis">
          {ticksY.map((t) => (
            <g key={t}>
              <line className="gridline" x1={M.left} x2={W - M.right} y1={y(t)} y2={y(t)} strokeWidth={1} />
              <text x={M.left - 6} y={y(t) + 4} textAnchor="end">{t % 1 ? t.toFixed(1) : t}</text>
            </g>
          ))}
          {ticksX.map((t) => (
            <text key={t} x={x(t)} y={height - 8} textAnchor="middle">{t}</text>
          ))}
          <text x={12} y={M.top + innerH / 2} transform={`rotate(-90 12 ${M.top + innerH / 2})`} textAnchor="middle">{yLabel}</text>
        </g>
        {series.filter((s) => s.area).map((s) => (
          <path key={`${s.id}-a`} d={`${path(s)}L${x(x1)},${y(0)}L${x(xStart)},${y(0)}Z`} fill={s.color} opacity={0.16} />
        ))}
        {series.map((s) => (
          <path key={s.id} d={path(s)} fill="none" stroke={s.color} strokeWidth={2} strokeLinejoin="round"
            strokeDasharray={s.dashed ? '6 4' : undefined} />
        ))}
        {playhead !== undefined && playhead >= xStart && playhead <= x1 && (
          <line x1={x(playhead)} x2={x(playhead)} y1={M.top} y2={M.top + innerH} stroke="var(--text-primary)" strokeWidth={1.5} opacity={0.7} />
        )}
        {hover !== null && (
          <g>
            <line x1={x(hover)} x2={x(hover)} y1={M.top} y2={M.top + innerH} stroke="var(--text-muted)" strokeDasharray="3 3" />
            {series.map((s) => {
              const v = s.values[hover]
              return v === null || v === undefined || !Number.isFinite(v) ? null : (
                <circle key={s.id} cx={x(hover)} cy={y(v)} r={4} fill={s.color} stroke="var(--surface-1)" strokeWidth={2} />
              )
            })}
          </g>
        )}
      </svg>
      {hover !== null && (
        <div className="tooltip" style={{ left: `${(x(hover) / W) * 100}%`, top: 24, transform: `translateX(${x(hover) > W * 0.65 ? '-105%' : '8px'})` }}>
          <div style={{ color: 'var(--text-muted)', marginBottom: 4 }}>Hour {hover} · day {Math.floor(hover / 24)}, {String(hover % 24).padStart(2, '0')}:00</div>
          {series.map((s) => {
            const v = s.values[hover]
            return (
              <div className="row" key={s.id}>
                <span><i className="swatch" style={{ background: s.color }} /> {s.label}</span>
                <b>{v === null || v === undefined || !Number.isFinite(v) ? '—' : `${v.toFixed(2)} ${s.unit ?? ''}`}</b>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
