import { useEffect, useRef, useState, type ReactNode } from 'react'
import { useMeta } from './api'

/** Citation chip: "Table 2" etc. Opens the paper reference plus the exact data source. */
export function Cite({ anchor, source, field }: { anchor: string; source?: string; field?: string | string[] }) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLSpanElement>(null)
  const meta = useMeta()
  useEffect(() => {
    if (!open) return
    const close = (e: MouseEvent) => { if (!ref.current?.contains(e.target as Node)) setOpen(false) }
    const esc = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false) }
    document.addEventListener('mousedown', close)
    document.addEventListener('keydown', esc)
    return () => { document.removeEventListener('mousedown', close); document.removeEventListener('keydown', esc) }
  }, [open])
  const fields = Array.isArray(field) ? field : field ? [field] : []
  return (
    <span ref={ref} style={{ position: 'relative', display: 'inline-block' }}>
      <button type="button" className="cite" aria-expanded={open} aria-label={`Source: paper ${anchor}`}
        onClick={(e) => { e.stopPropagation(); setOpen(!open) }} onKeyDown={(e) => e.stopPropagation()}
        title={`Source: paper ${anchor}`}>{anchor}</button>
      {open && (
        <span className="popover" role="dialog" style={{ right: 0, top: '120%' }} onClick={(e) => e.stopPropagation()}>
          <b>Paper {anchor}</b><br />
          {meta.data?.citation ?? 'Manjunath et al., ICMLDE 2026, Paper ID 1939.'}
          {source && <><br /><br /><b>Data</b> <code>{source}</code></>}
          {fields.length > 0 && <><br /><b>Field{fields.length > 1 ? 's' : ''}</b> {fields.map((f) => <code key={f} style={{ marginRight: 6 }}>{f}</code>)}</>}
        </span>
      )}
    </span>
  )
}

/** Provenance rule: if an endpoint fails, show a dash and say so - never a cached or typed value. */
export function Unavailable() {
  return <span className="unavailable">— data unavailable</span>
}

export function Loading({ children }: { children?: ReactNode }) {
  return <div className="loading" style={{ minHeight: 160 }}><div className="spinner" />{children ?? 'Loading…'}</div>
}

export const f1 = (v: number) => v.toFixed(1)
export const f2 = (v: number) => v.toFixed(2)

/** "37" -> "day 1 · 13:00" */
export const hourLabel = (h: number) => `day ${Math.floor(h / 24)} · ${String(h % 24).padStart(2, '0')}:00`

/** Compress [3,4,5,9] -> "3–5, 9". */
export function ranges(hours: number[], max = 8): string {
  if (!hours.length) return 'none'
  const out: string[] = []
  let a = hours[0], b = hours[0]
  for (const h of [...hours.slice(1), NaN]) {
    if (h === b + 1) { b = h; continue }
    out.push(a === b ? `${a}` : `${a}–${b}`)
    a = b = h
  }
  return out.length > max ? `${out.slice(0, max).join(', ')} … (${out.length} spans)` : out.join(', ')
}

/** Tiny sparkline with a cursor at the selected hour. */
export function Sparkline({ values, hour, color, height = 46 }: { values: (number | null)[]; hour: number; color: string; height?: number }) {
  const W = 300
  const v = values.map((x) => x ?? 0)
  const max = Math.max(1e-9, ...v), min = Math.min(0, ...v)
  const x = (i: number) => (i / (v.length - 1)) * W
  const y = (val: number) => height - 3 - ((val - min) / (max - min || 1)) * (height - 6)
  const d = v.map((val, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(val).toFixed(1)}`).join('')
  return (
    <svg viewBox={`0 0 ${W} ${height}`} style={{ width: '100%', height }} role="img" aria-label="168-hour sparkline">
      <path d={`${d}L${W},${height}L0,${height}Z`} fill={color} opacity={0.12} />
      <path d={d} fill="none" stroke={color} strokeWidth={1.6} />
      <line x1={x(hour)} x2={x(hour)} y1={0} y2={height} stroke="var(--text-primary)" strokeWidth={1} opacity={0.6} />
    </svg>
  )
}
