import { lazy, Suspense, useEffect, useState } from 'react'
import { loadModel } from '../api/source'
import { useQaoa } from '../research/api'
import { Cite, Loading, Unavailable } from '../research/ui'
import { useApp } from '../state/store'

const Lab = lazy(() => import('../pages/Quantum').then((m) => ({ default: m.Quantum })))

function Explorer() {
  const model = useApp((s) => s.model)
  const setModel = useApp((s) => s.setModel)
  useEffect(() => { if (!model) loadModel().then(setModel).catch(() => undefined) }, [model, setModel])
  if (!model) return <Loading />
  return <Suspense fallback={<Loading />}><Lab model={model} /></Suspense>
}

export function QuantumCheckView() {
  const q = useQaoa()
  const [explore, setExplore] = useState(false)
  if (q.isError) return <Unavailable />
  if (!q.data) return <Loading />
  const d = q.data
  const allFound = d.depths.every((x) => x.most_probable_is_optimum && x.gap === 0)
  return (
    <div className="grid" style={{ gap: 16 }}>
      <div className="layout-12">
        <div className="span-4 card">
          <h3><span>The question in plain language</span><Cite anchor="Fig. 3" source={d.source} field={['n_states', 'n_feasible']} /></h3>
          <p>Each day has <b>{d.bundles} flexible bundles</b> and each may run in one of <b>{d.slots} slots</b> (baseline, +3 h, +7 h).
            That is {d.bundles} × {d.slots} = <b>{d.qubits} binary variables = {d.qubits} qubits</b>, so 2<sup>{d.qubits}</sup> ={' '}
            <b>{d.states.toLocaleString('en')}</b> basis states, of which <b>{d.feasible}</b> put every bundle in exactly one slot.</p>
          <p>The question: does the QAOA circuit put most of its probability on those {d.feasible} states, and is its most likely answer the best one?</p>
          <p className="notice info" style={{ fontSize: 13 }}>{d.note}</p>
        </div>
        <div className="span-8 card">
          <h3><span>Feasible probability mass</span>
            <span style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              {allFound && <span className="pill" style={{ background: 'color-mix(in srgb, var(--status-good) 18%, transparent)', color: 'var(--status-good)', fontWeight: 700 }}>✓ optimum found · gap 0</span>}
              <Cite anchor="Fig. 3" source={d.source} field={['qaoa.p.feas_mass', 'qaoa.p.p_opt', 'qaoa.p.gap']} />
            </span></h3>
          <svg viewBox="0 0 700 150" style={{ width: '100%', height: 'auto' }} role="img" aria-label="Feasible probability mass at depth 1 and 2">
            {d.depths.map((x, i) => {
              const y = 22 + i * 60
              const w = (x.feasible_mass_pct / 100) * 520
              return (
                <g key={x.p}>
                  <text x={0} y={y + 22} fontSize={14} fontWeight={700} fill="var(--text-primary)">p = {x.p}</text>
                  <rect x={60} y={y} width={520} height={34} rx={5} fill="var(--surface-2)" />
                  <rect x={60} y={y} width={w} height={34} rx={5} fill="var(--c-h2)" />
                  <text x={66 + w} y={y + 22} fontSize={14} fontWeight={700} fill="var(--text-primary)">{x.feasible_mass_pct.toFixed(2)} %</text>
                  <text x={60} y={y + 50} fontSize={11.5} fill="var(--text-muted)">probability of the exact optimum {x.optimum_probability_pct.toFixed(3)} % · gap {x.gap}</text>
                </g>
              )
            })}
          </svg>
          <h4 style={{ margin: '12px 0 6px' }}>Chosen slots vs baseline (day 0)</h4>
          <svg viewBox="0 0 700 92" style={{ width: '100%', height: 'auto' }} role="img" aria-label="Baseline and chosen hours of the four bundles">
            {Array.from({ length: 25 }, (_, h) => h).filter((h) => h % 3 === 0).map((h) => (
              <text key={h} x={40 + h * 26} y={88} fontSize={10.5} textAnchor="middle" fill="var(--text-muted)">{String(h).padStart(2, '0')}:00</text>
            ))}
            {d.baseline_hours.map((b, k) => {
              const a = d.assignment_hours[k], y = 12 + k * 17
              return (
                <g key={k}>
                  <rect x={40 + b * 26 - 6} y={y - 6} width={12} height={12} rx={2} fill="var(--surface-3)" stroke="var(--c-jobs)" />
                  {a !== b && <line x1={40 + b * 26 + 6} x2={40 + a * 26 - 8} y1={y} y2={y} stroke="var(--c-jobs)" strokeWidth={1.5} />}
                  <rect x={40 + a * 26 - 6} y={y - 6} width={12} height={12} rx={2} fill="var(--c-jobs)" />
                  <text x={40 + a * 26 + 10} y={y + 4} fontSize={10.5} fill="var(--text-secondary)">bundle {k + 1}: {b}:00 → {a}:00{a === b ? ' (stays)' : ''}</text>
                </g>
              )
            })}
          </svg>
          <div className="caption">Outlined = baseline slot, filled = chosen slot (from assignment_hours and baseline_hours).</div>
        </div>
      </div>
      <div className="card">
        <h3><span>Explore the circuit <span className="sub">optional · exact 12-qubit state vector computed in your browser</span></span>
          <button className="btn secondary" onClick={() => setExplore(!explore)}>{explore ? 'Hide' : 'Open explorer'}</button></h3>
        {explore && <Explorer />}
      </div>
    </div>
  )
}
