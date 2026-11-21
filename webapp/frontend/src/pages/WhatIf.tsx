import { motion } from 'motion/react'
import { useEffect, useRef, useState, type ReactNode } from 'react'
import { DEFAULT_WHATIF, getJob, startWhatIf, type Job, type WhatIfMode, type WhatIfRequest } from '../api/source'
import type { Model, ScenarioKey } from '../api/types'
import { LineChart } from '../charts/LineChart'

type NumKey = { [K in keyof WhatIfRequest]: WhatIfRequest[K] extends number ? K : never }[keyof WhatIfRequest]

const MODES: { id: WhatIfMode; label: string; ref: ScenarioKey; help: string }[] = [
  { id: 'min-uniform-flexible', label: 'Smallest firm connection, jobs may move', ref: 'R3', help: 'Bisection finds the smallest uniform cap; bundles may use any candidate slot.' },
  { id: 'min-uniform', label: 'Smallest firm connection, jobs pinned', ref: 'R2', help: 'Bisection finds the smallest uniform cap; every bundle stays in its baseline hour.' },
  { id: 'nonfirm', label: 'Non-firm envelope', ref: 'R4', help: 'Import is capped by a daily contraction window; reported value is the peak import.' },
  { id: 'phased', label: 'Phased envelope', ref: 'R5', help: 'Three 56-hour stages as reinforcement is delivered; reported value is the peak import.' },
]

const STEPS = [
  ['1 · Configure', 'You set the plant, the demand, the workload windows and the connection contract.'],
  ['2 · Hourly table', 'The synthetic 168-h benchmark is scaled to your demand, solar and wind settings.'],
  ['3 · MILP', 'For every hour the solver decides grid import, electrolyser intake, fuel-cell output, hydrogen inventory and curtailment, and picks one slot per bundle — minimising carbon, curtailment, deferral and H₂ cycling.'],
  ['4 · Capacity search', 'For a firm connection, bisection tightens the cap until the schedule would become infeasible (24 steps).'],
  ['5 · Check', 'Zero unserved energy, zero envelope violation, tank returns to its start level; then metrics.'],
]

function Component({ title, icon, children, note }: { title: string; icon: string; children: ReactNode; note?: string }) {
  return (
    <div className="card" style={{ padding: 14 }}>
      <h3 style={{ fontSize: 15 }}><span>{icon} {title}</span></h3>
      {children}
      {note && <p style={{ fontSize: 12, margin: 0 }}>{note}</p>}
    </div>
  )
}

export function WhatIf({ model }: { model: Model }) {
  const [req, setReq] = useState<WhatIfRequest>(DEFAULT_WHATIF)
  const [job, setJob] = useState<Job | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const timer = useRef<number | undefined>(undefined)
  const current = useRef<string | null>(null) // id of the job this page is following
  useEffect(() => () => { current.current = null; window.clearTimeout(timer.current) }, [])
  const live = model.mode === 'live'
  const mode = MODES.find((m) => m.id === req.mode)!
  const ref = model.table[mode.ref]
  const isEnvelope = req.mode === 'nonfirm' || req.mode === 'phased'

  const stop = () => { current.current = null; window.clearTimeout(timer.current) }
  const poll = (id: string, failures = 0) => {
    timer.current = window.setTimeout(async () => {
      if (current.current !== id) return
      try {
        const j = await getJob(id)
        if (current.current !== id) return // a newer run or a reset superseded this one
        setJob(j)
        if (j.status === 'queued' || j.status === 'running') poll(id)
      } catch (e) {
        if (current.current !== id) return
        if (failures < 3) poll(id, failures + 1) // tolerate transient network errors
        else setErr(String(e))
      }
    }, 350)
  }
  const run = async () => {
    stop()
    setErr(null)
    try {
      const j = await startWhatIf({ ...req, h2_init_mwh: Math.min(req.h2_init_mwh, req.h2_max_mwh) })
      current.current = j.id
      setJob(j)
      poll(j.id)
    } catch (e) {
      const msg = String(e)
      setErr(msg.includes('429') ? 'The server is busy with other simulations — please try again in a moment.' : msg)
    }
  }
  const slider = (k: NumKey, label: string, min: number, max: number, step: number, unit = '') => (
    <div className="field" key={k}>
      <label>{label} <b>{(req[k] as number).toFixed(step < 0.1 ? 2 : step < 1 ? 1 : 0)} {unit}</b></label>
      <input type="range" min={min} max={max} step={step} value={req[k] as number} aria-label={label}
        onChange={(e) => {
          const next = { ...req, [k]: Number(e.target.value) }
          // keep the request inside the API's validation rules
          next.nonfirm_reduced_mw = Math.min(next.nonfirm_reduced_mw, next.nonfirm_normal_mw)
          next.h2_init_mwh = Math.min(next.h2_init_mwh, next.h2_max_mwh)
          setReq(next)
        }} />
    </div>
  )
  const toggleOffset = (o: number) => {
    const has = req.candidate_offsets_h.includes(o)
    const next = has ? req.candidate_offsets_h.filter((x) => x !== o) : [...req.candidate_offsets_h, o].sort((a, b) => a - b)
    if (next.length >= 2 && next.length <= 5) setReq({ ...req, candidate_offsets_h: next })
  }
  const res = job?.result
  const busy = job?.status === 'queued' || job?.status === 'running'

  return (
    <div className="grid" style={{ gap: 16 }}>
      <div className="page-title">
        <div>
          <div className="eyebrow">Configure your AI data centre · solved on the FastAPI backend</div>
          <h2>Design studio</h2>
          <p>Set every component of the campus, choose the connection contract, and let the scheduler find the smallest grid connection
            it can live with. With the default values the backend reproduces the published table (data/research_results_gridflex.csv) for R2–R5.</p>
        </div>
        <div className="controls">
          <button className="btn" disabled={!live || busy} onClick={run}>{busy ? 'Optimising…' : 'Optimise campus'}</button>
          <button className="btn secondary" onClick={() => { stop(); setReq(DEFAULT_WHATIF); setJob(null) }}>Paper defaults</button>
        </div>
      </div>

      <div className="card">
        <h3>How the optimisation works <span className="sub">what the solver decides for you</span></h3>
        <div className="pipeline">
          {STEPS.map(([h, d], i) => (
            <motion.div className="stage" key={h} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.08 }}>
              <h4 style={{ marginTop: 0 }}>{h}</h4><p style={{ fontSize: 13, margin: 0 }}>{d}</p>
            </motion.div>
          ))}
        </div>
      </div>

      <p className="notice" style={{ margin: 0 }}><strong>Exploratory results.</strong> Anything you change here is a what-if on the synthetic benchmark —
        not a result of the peer-reviewed paper — and the API labels it so.{!live && <> <strong>Backend not connected:</strong> run <code>START.bat</code> (Windows) or
          start <code>uvicorn app.main:app</code> in <code>webapp/backend</code>, then reload.</>}</p>

      <div className="grid cols-3">
        <Component title="Grid connection contract" icon="⚡" note={mode.help}>
          <div className="seg" role="group" aria-label="Connection contract" style={{ marginBottom: 12 }}>
            {MODES.map((m) => <button key={m.id} aria-pressed={req.mode === m.id} onClick={() => setReq({ ...req, mode: m.id })}>{m.label}</button>)}
          </div>
          {req.mode === 'nonfirm' && <>
            {slider('nonfirm_normal_mw', 'Normal level', 6, 16, 0.1, 'MW')}
            {slider('nonfirm_reduced_mw', 'Reduced level', 2, req.nonfirm_normal_mw, 0.1, 'MW')}
            {slider('nonfirm_start_hour', 'Contraction starts', 0, req.nonfirm_end_hour, 1, 'h')}
            {slider('nonfirm_end_hour', 'Contraction ends (inclusive)', req.nonfirm_start_hour, 23, 1, 'h')}
          </>}
          {req.mode === 'phased' && req.phased_levels_mw.map((v, i) => (
            <div className="field" key={i}>
              <label>Stage {i + 1} (hours {i * 56}–{i * 56 + 55}) <b>{v.toFixed(1)} MW</b></label>
              <input type="range" min={4} max={16} step={0.1} value={v} aria-label={`Phased stage ${i + 1}`}
                onChange={(e) => setReq({ ...req, phased_levels_mw: req.phased_levels_mw.map((x, k) => (k === i ? Number(e.target.value) : x)) })} />
            </div>
          ))}
        </Component>

        <Component title="AI data hall & workload" icon="🖥" note="Latency-sensitive work (inference, live serving) is fixed; delay-tolerant bundles (training, fine-tuning, batch) may move to later slots.">
          {slider('demand_scale', 'AI demand scale', 0.7, 1.3, 0.05, '×')}
          <div className="field">
            <label>Candidate slots for each bundle (hours after baseline) <b>{req.candidate_offsets_h.map((o) => (o ? `+${o}` : '0')).join(', ')}</b></label>
            <div className="seg" role="group" aria-label="Candidate slots">
              {[1, 2, 3, 4, 5, 6, 7, 8, 10, 12].map((o) => (
                <button key={o} aria-pressed={req.candidate_offsets_h.includes(o)} onClick={() => toggleOffset(o)}>+{o}</button>
              ))}
            </div>
          </div>
          {isEnvelope && (
            <label style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: 14, color: 'var(--text-secondary)' }}>
              <input type="checkbox" checked={req.workload_flexibility} onChange={(e) => setReq({ ...req, workload_flexibility: e.target.checked })} />
              Allow workload flexibility (untick to pin every bundle to its baseline hour)
            </label>
          )}
        </Component>

        <Component title="On-site renewables" icon="☀" note="Scales the hourly solar and wind profiles of the benchmark week. Surplus is curtailed, never exported.">
          {slider('solar_scale', 'Solar output scale', 0, 2.5, 0.05, '×')}
          {slider('wind_scale', 'Wind output scale', 0, 2.5, 0.05, '×')}
        </Component>

        <Component title="Electrolyser" icon="⚗" note="Converts renewable surplus to hydrogen; it may only use on-site renewable power.">
          {slider('electrolyser_mw', 'Rated power', 0, 12, 0.5, 'MW')}
          {slider('eta_el', 'Efficiency (electric → H₂)', 0.5, 0.85, 0.01)}
        </Component>

        <Component title="Hydrogen tank" icon="🛢" note="The tank must end the week at its starting level, so no gain comes from emptying it.">
          {slider('h2_max_mwh', 'Tank capacity', 0, 80, 1, 'MWh-H')}
          {slider('h2_init_mwh', 'Start = end level', 0, Math.max(1, req.h2_max_mwh), 0.5, 'MWh-H')}
        </Component>

        <Component title="Fuel cell" icon="🔌" note="Converts hydrogen from the tank back to electricity in the hours that would otherwise set the peak.">
          {slider('fuel_cell_mw', 'Rated power', 0, 6, 0.25, 'MW')}
          {slider('eta_fc', 'Efficiency (H₂ → electric)', 0.35, 0.7, 0.01)}
        </Component>
      </div>

      <div className="card">
        <h3>Result <span className="sub">{job ? `job ${job.id.slice(0, 8)} · ${job.status}${job.runtime_s ? ` · ${job.runtime_s.toFixed(1)} s` : ''}` : 'press “Optimise campus”'}</span></h3>
        {busy && <div className="meter"><span style={{ width: `${Math.max(4, (job?.progress ?? 0) * 100)}%`, background: 'var(--accent)' }} /></div>}
        {job?.status === 'failed' && <p style={{ color: 'var(--status-critical)' }}>{job.error}</p>}
        {err && <p style={{ color: 'var(--status-critical)' }}>{err}</p>}
        {res && !res.feasible && <p className="notice"><strong>Infeasible.</strong> No schedule meets every hour of demand inside this contract with these assets.
          Try more hydrogen, a later contraction window, wider job windows or workload flexibility.</p>}
        {res?.feasible && res.metrics && (
          <div className="grid cols-2">
            <div className="table-wrap">
              <table className="data">
                <thead><tr><th>Metric</th><th>Your campus</th><th>Paper {mode.ref}</th></tr></thead>
                <tbody>
                  <tr><td>Required connection</td><td>{res.connection_capacity_MW!.toFixed(3)} MW</td><td>{ref.connection_capacity_MW.toFixed(3)} MW</td></tr>
                  <tr><td>Reduction vs grid-only peak</td><td>{res.reduction_vs_grid_only_pct!.toFixed(1)}%</td><td>{ref.capacity_reduction_pct.toFixed(1)}%</td></tr>
                  <tr><td>Grid energy</td><td>{res.metrics.grid_energy_MWh.toFixed(2)} MWh</td><td>{ref.grid_energy_MWh.toFixed(2)} MWh</td></tr>
                  <tr><td>Operational CO₂</td><td>{res.metrics.operational_CO2_t.toFixed(2)} t</td><td>{ref.operational_CO2_t.toFixed(2)} t</td></tr>
                  <tr><td>Renewable utilisation</td><td>{res.metrics.renewable_utilization_pct.toFixed(2)}%</td><td>{ref.renewable_utilization_pct.toFixed(2)}%</td></tr>
                  <tr><td>Electrolyser / fuel cell</td><td>{res.metrics.electrolyser_MWh.toFixed(1)} / {res.metrics.fuel_cell_MWh.toFixed(1)} MWh</td><td>—</td></tr>
                  <tr><td>Bundles shifted · mean delay</td><td>{res.metrics.jobs_shifted_pct.toFixed(1)}% · {res.metrics.average_workload_delay_h.toFixed(2)} h</td>
                    <td>{ref.jobs_shifted_pct.toFixed(1)}% · {ref.average_workload_delay_h.toFixed(2)} h</td></tr>
                  <tr><td>Envelope violation</td><td>{res.metrics.violation_energy_MWh.toFixed(3)} MWh</td><td>0</td></tr>
                </tbody>
              </table>
              <p style={{ fontSize: 12 }}>{res.disclaimer}</p>
            </div>
            {res.series && (
              <div className="grid">
                <LineChart ariaLabel="Grid import and connection cap of your campus" yLabel="MW" series={[
                  { id: 'g', label: 'Grid import', color: 'var(--series-grid)', values: res.series.grid_import_MW, unit: 'MW', area: true },
                  { id: 'c', label: 'Connection cap', color: 'var(--text-primary)', values: res.series.connection_cap_MW, step: true, dashed: true, unit: 'MW' },
                ]} />
                <LineChart ariaLabel="Hydrogen inventory of your campus" yLabel="MWh-H" series={[
                  { id: 'h', label: 'H₂ inventory', color: 'var(--series-el)', values: res.series.h2_inventory_MWh, unit: 'MWh', area: true },
                ]} />
              </div>
            )}
          </div>
        )}
      </div>

      <div className="card">
        <h3>What is distinctive about the method</h3>
        <ul className="ticks">
          <li><b>Connection capacity is the output,</b> not a fixed input or a priced term: a carbon-/curtailment-weighted MILP is wrapped in a bisection that returns the smallest feasible cap.</li>
          <li><b>Hydrogen and flexibility in one model:</b> the hydrogen chain and discrete job placement are decided together, on the same hours, so their relief can be compared directly.</li>
          <li><b>Contract-aware:</b> firm, phased and time-varying non-firm envelopes use the same formulation.</li>
          <li><b>Verifiable quantum layer:</b> only the placement block becomes a 12-variable QUBO; QAOA is checked against all 4,096 states and cross-checked in PennyLane.</li>
          <li><b>Independently reproduced:</b> an independent SciPy model and this engine are tested against the published numbers, which were produced by the MATLAB MILP run.</li>
        </ul>
        <p style={{ fontSize: 12, margin: 0 }}>A dated comparison with related papers, patents and repositories is in <code>docs/related-work.md</code>; it is a survey, not a novelty claim.</p>
      </div>
    </div>
  )
}
