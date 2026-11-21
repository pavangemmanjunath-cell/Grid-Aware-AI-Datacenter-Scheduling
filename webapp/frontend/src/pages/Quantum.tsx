import { useEffect, useMemo, useRef, useState } from 'react'
import { optimiseQaoa } from '../api/source'
import type { Model } from '../api/types'
import { assignmentHours, qaoa } from '../lib/qaoa'

/** 4,096 basis states ordered by QUBO cost, probability on a log axis. Canvas for speed. */
function Distribution({ energies, feasible, best, probs }: { energies: number[]; feasible: Set<number>; best: number; probs: Float64Array }) {
  const ref = useRef<HTMLCanvasElement>(null)
  const order = useMemo(() => energies.map((_, i) => i).sort((a, b) => energies[a] - energies[b]), [energies])
  useEffect(() => {
    const c = ref.current!, dpr = window.devicePixelRatio || 1
    const W = c.clientWidth, H = 240
    c.width = W * dpr; c.height = H * dpr
    const g = c.getContext('2d')!
    g.scale(dpr, dpr)
    const css = getComputedStyle(c)
    const col = (v: string) => css.getPropertyValue(v).trim()
    g.clearRect(0, 0, W, H)
    const L = 44, B = 24, T = 8, innerW = W - L - 8, innerH = H - B - T
    const lo = -7, hi = 0 // log10 of probability: 1e-7 .. 1
    const y = (p: number) => T + innerH - ((Math.log10(Math.max(p, 1e-7)) - lo) / (hi - lo)) * innerH
    g.strokeStyle = col('--grid-line'); g.fillStyle = col('--text-muted'); g.font = '11px system-ui'; g.textAlign = 'right'
    for (let e = lo; e <= hi; e++) {
      g.beginPath(); g.moveTo(L, y(10 ** e)); g.lineTo(W - 8, y(10 ** e)); g.stroke()
      g.fillText(`1e${e}`, L - 6, y(10 ** e) + 4)
    }
    g.textAlign = 'center'
    g.fillText('basis states ordered by QUBO cost (low → high)', L + innerW / 2, H - 6)
    order.forEach((s, rank) => {
      if (feasible.has(s)) return
      g.fillStyle = col('--neutral-mark'); g.globalAlpha = 0.45
      g.fillRect(L + (rank / order.length) * innerW, y(probs[s]), 1.5, 1.5)
    })
    g.globalAlpha = 1
    order.forEach((s, rank) => {
      if (!feasible.has(s)) return
      const x = L + (rank / order.length) * innerW
      g.fillStyle = s === best ? col('--status-good') : col('--series-fc')
      g.beginPath(); g.arc(x, y(probs[s]), s === best ? 5 : 3, 0, Math.PI * 2); g.fill()
    })
  }, [order, probs, feasible, best])
  return <canvas ref={ref} style={{ width: '100%', height: 240, display: 'block' }} role="img"
    aria-label="Measurement probability of every basis state, ordered by QUBO cost; feasible states highlighted" />
}

/** p = 1 expected-cost landscape (precomputed by the reference model), one-hue sequential ramp. */
function Landscape({ land, gamma, beta }: { land: { gamma: number[]; beta: number[]; cost: number[][] }; gamma: number; beta: number }) {
  const ref = useRef<HTMLCanvasElement>(null)
  useEffect(() => {
    const c = ref.current!, n = land.gamma.length, m = land.beta.length
    c.width = n; c.height = m
    const g = c.getContext('2d')!
    const img = g.createImageData(n, m)
    let mn = Infinity, mx = -Infinity
    land.cost.forEach((row) => row.forEach((v) => { mn = Math.min(mn, v); mx = Math.max(mx, v) }))
    const ramp = [[205, 226, 251], [134, 182, 239], [57, 135, 229], [28, 92, 171], [13, 54, 107]] // blue 100→700: low cost = dark
    for (let j = 0; j < m; j++) for (let i = 0; i < n; i++) {
      const u = 1 - (land.cost[j][i] - mn) / (mx - mn)
      const k = Math.min(3.999, u * 4), a = Math.floor(k), f = k - a
      const [r1, g1, b1] = ramp[a], [r2, g2, b2] = ramp[a + 1]
      const p = ((m - 1 - j) * n + i) * 4
      img.data[p] = r1 + (r2 - r1) * f; img.data[p + 1] = g1 + (g2 - g1) * f; img.data[p + 2] = b1 + (b2 - b1) * f; img.data[p + 3] = 255
    }
    g.putImageData(img, 0, 0)
  }, [land])
  const gx = (gamma - land.gamma[0]) / (land.gamma[land.gamma.length - 1] - land.gamma[0])
  const by = (beta - land.beta[0]) / (land.beta[land.beta.length - 1] - land.beta[0])
  const inside = gx >= 0 && gx <= 1 && by >= 0 && by <= 1
  return (
    <div style={{ position: 'relative' }}>
      <canvas ref={ref} style={{ width: '100%', aspectRatio: '1.3', imageRendering: 'auto', borderRadius: 8, display: 'block' }}
        role="img" aria-label="Expected QUBO cost over the p=1 angle plane; darker is lower cost" />
      {inside && <div style={{ position: 'absolute', left: `${gx * 100}%`, top: `${(1 - by) * 100}%`, transform: 'translate(-50%,-50%)',
        width: 14, height: 14, borderRadius: '50%', border: '2px solid #fff', boxShadow: '0 0 0 2px #000' }} />}
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
        <span>γ {land.gamma[0]} → {land.gamma[land.gamma.length - 1]}</span><span>β {land.beta[0]} → {land.beta[land.beta.length - 1]} (bottom → top)</span><span>darker = lower expected cost</span>
      </div>
    </div>
  )
}

export function Quantum({ model }: { model: Model }) {
  const q = model.quantum
  const [p, setP] = useState(1)
  const [angles, setAngles] = useState<number[]>(q.pinnedAngles['1'])
  const [opt, setOpt] = useState<any>(null)
  const [busy, setBusy] = useState(false)
  const feasible = useMemo(() => new Set(q.feasible), [q])
  const stats = useMemo(() => qaoa(q.energies, q.feasible, q.bestIndex, angles, p), [q, angles, p])
  const pinned = q.pinnedAngles[String(p)]
  const atPinned = pinned.every((v, i) => Math.abs(v - angles[i]) < 1e-9)
  const topHours = assignmentHours(stats.mostProbableFeasible, q.candidateHours, q.slots)
  const bestHours = assignmentHours(q.bestIndex, q.candidateHours, q.slots)
  const setDepth = (d: number) => { setP(d); setAngles(q.pinnedAngles[String(d)]); setOpt(null) }
  const runOpt = async () => {
    setBusy(true)
    const depth = p
    try {
      const r = await optimiseQaoa(depth, 5, Math.floor(Math.random() * 1000))
      if (r.best.angles.length === 2 * depth) { setOpt(r); setAngles(r.best.angles) }
    }
    catch (e) { setOpt({ error: String(e) }) } finally { setBusy(false) }
  }
  return (
    <div className="grid" style={{ gap: 16 }}>
      <div className="page-title">
        <div>
          <div className="eyebrow">Exact 12-qubit state-vector simulation · runs in your browser</div>
          <h2>Quantum placement lab</h2>
          <p>Day 0 has four delay-tolerant bundles with three candidate slots each: 12 binary variables, 4,096 basis states, 81 one-hot
            feasible. Move the angles and the QAOA state vector is recomputed exactly. This is a formulation and verification study on a
            classically enumerable instance — not evidence of quantum advantage.</p>
        </div>
        <div className="seg" role="group" aria-label="Circuit depth">
          {[1, 2].map((d) => <button key={d} aria-pressed={p === d} disabled={busy} onClick={() => setDepth(d)}>p = {d}</button>)}
        </div>
      </div>
      <div className="grid cols-4">
        {[
          [`${stats.feasibleMass.toFixed(2)}%`, 'feasible probability mass'],
          [`${stats.optimumProbability.toFixed(3)}%`, 'probability of exact optimum'],
          [stats.mostProbableFeasible === q.bestIndex ? '0' : 'gap > 0', 'optimality gap of most-probable feasible state'],
          [stats.expectedCost.toFixed(2), `expected QUBO cost (optimum ${q.bestEnergy.toFixed(4)})`],
        ].map(([v, l]) => <div className="card stat" key={l}><span className="value">{v}</span><span className="label">{l}</span></div>)}
      </div>
      <div className="grid cols-3">
        <div className="card">
          <h3>Angles <span className="sub">{atPinned ? 'published (pinned) values' : 'custom'}</span></h3>
          {Array.from({ length: 2 * p }, (_, i) => {
            const isG = i < p
            const range = isG ? [0, 30] : [-Math.PI, Math.PI]
            return (
              <div className="field" key={i}>
                <label>{isG ? `γ${i + 1}` : `β${i - p + 1}`} <b>{angles[i].toFixed(4)}</b></label>
                <input type="range" min={range[0]} max={range[1]} step={0.001} value={angles[i]}
                  onChange={(e) => setAngles(angles.map((a, k) => (k === i ? Number(e.target.value) : a)))} />
              </div>
            )
          })}
          <div className="controls">
            <button className="btn secondary" onClick={() => setAngles(pinned)}>Reset to published</button>
            <button className="btn" disabled={model.mode !== 'live' || busy} onClick={runOpt}
              title={model.mode !== 'live' ? 'Requires the FastAPI backend' : 'Nelder–Mead, 5 random restarts'}>
              {busy ? 'Optimising…' : 'Optimise (API)'}
            </button>
          </div>
          {opt?.best && <p style={{ fontSize: 12, marginTop: 8 }}>Exploratory optimisation: best of {opt.runs.length} restarts. Results depend on seed and optimiser; the published table comes from the MATLAB run, reproduced here with its angles pinned.</p>}
          {opt?.error && <p style={{ fontSize: 12, color: 'var(--status-critical)' }}>{opt.error}</p>}
          <hr style={{ border: 0, borderTop: '1px solid var(--border)', margin: '12px 0' }} />
          <dl className="readout">
            <dt>Baseline hours</dt><dd className="mono">{q.baselineHours.join(', ')}</dd>
            <dt>Exact optimum (enumeration)</dt><dd className="mono">{bestHours.join(', ')}</dd>
            <dt>Most probable feasible</dt><dd className="mono">{topHours.join(', ')}</dd>
          </dl>
        </div>
        <div className="card" style={{ gridColumn: 'span 2' }}>
          <h3>Output distribution <span className="sub">feasible one-hot states in colour, exact optimum in green</span></h3>
          <Distribution energies={q.energies} feasible={feasible} best={q.bestIndex} probs={stats.probabilities} />
        </div>
      </div>
      {p === 1 && q.landscape && (
        <div className="grid cols-2">
          <div className="card">
            <h3>p = 1 energy landscape <span className="sub">marker = current angles</span></h3>
            <Landscape land={q.landscape} gamma={angles[0]} beta={angles[1]} />
          </div>
          <div className="card">
            <h3>QUBO terms</h3>
            <ul className="ticks">
              <li><b>One-hot</b> penalty A = 40: each bundle in exactly one slot.</li>
              <li><b>Connection stress</b> weight 6: energy above the slot's non-firm headroom.</li>
              <li><b>Carbon</b> weight 1 and <b>renewable coincidence</b> reward 1.5.</li>
              <li><b>Deferral</b> 0.30 per hour; <b>collision</b> 2.5 · E<sub>j</sub>E<sub>j′</sub>/10 for two bundles in one hour.</li>
              <li>Cost operator rescaled by max |E|; mixer e<sup>−iβX</sup> on every qubit; angles: Nelder–Mead, 5 restarts (MATLAB reference run).</li>
            </ul>
          </div>
        </div>
      )}
    </div>
  )
}
