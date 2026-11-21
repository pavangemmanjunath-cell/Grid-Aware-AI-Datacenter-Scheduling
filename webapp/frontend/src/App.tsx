import { lazy, Suspense, useEffect, useState } from 'react'
import { loadModel } from './api/source'
import { PAPER } from './content'
import { SCENARIO_IDS, useMeta, useMode, useScenarios } from './research/api'
import { Cite, Loading } from './research/ui'
import { useApp, VIEWS } from './state/store'
import { CampusView } from './views/Campus'
import { ConnectionView } from './views/Connection'
import { EvidenceView } from './views/Evidence'
import { QuantumCheckView } from './views/QuantumCheck'
import { WeekReplayView } from './views/WeekReplay'

const Studio = lazy(() => import('./pages/WhatIf').then((m) => ({ default: m.WhatIf })))

function useTheme() {
  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    try { return localStorage.getItem('qh2dc-theme') === 'dark' ? 'dark' : 'light' } catch { return 'light' }
  })
  useEffect(() => {
    document.documentElement.dataset.theme = theme
    try { localStorage.setItem('qh2dc-theme', theme) } catch { /* browser persistence unavailable */ }
  }, [theme])
  return [theme, () => setTheme(theme === 'dark' ? 'light' : 'dark')] as const
}

function StudioView() {
  const model = useApp((s) => s.model)
  const setModel = useApp((s) => s.setModel)
  useEffect(() => { if (!model) loadModel().then(setModel).catch(() => undefined) }, [model, setModel])
  if (!model) return <Loading />
  return <Suspense fallback={<Loading />}><Studio model={model} /></Suspense>
}

export default function App() {
  const view = useApp((s) => s.view)
  const setView = useApp((s) => s.setView)
  const scenario = useApp((s) => s.scenario)
  const setScenario = useApp((s) => s.setScenario)
  const meta = useMeta()
  const scen = useScenarios()
  const mode = useMode()
  const [theme, toggleTheme] = useTheme()
  const tips = Object.fromEntries((scen.data ?? []).map((r) => [r.id, `${r.id} ${r.label}: ${r.tooltip}`]))
  const banner = meta.data?.banner ?? 'Synthetic 168-h benchmark · decision support, not a site forecast · QAOA is an exact simulation, no quantum advantage claimed'
  const current = VIEWS.find((v) => v.id === view)

  return (
    <>
      <header className="header">
        <div className="header-row">
          <div className="title-block">
            <span className="t">How small a grid connection can an AI campus live with?</span>
            <span className="s">QH2DC research dashboard · renewables, green hydrogen and flexible AI jobs · <Cite anchor="Manjunath et al., ICMLDE 2026" /></span>
          </div>
          <div className="seg" role="group" aria-label="Scenario">
            {SCENARIO_IDS.map((k) => (
              <button key={k} aria-pressed={scenario === k} title={tips[k] ?? k} onClick={() => setScenario(k)} data-testid={`scenario-${k}`}>{k}</button>
            ))}
          </div>
          {mode.data && (
            <span className="mode-badge" title={mode.data === 'live' ? 'Reading the FastAPI service' : 'Reading the versioned API snapshot (identical responses)'}>
              <span className="dot" style={{ background: mode.data === 'live' ? 'var(--status-good)' : 'var(--status-warn)' }} />
              {mode.data === 'live' ? 'Live API' : 'API snapshot'}
            </span>
          )}
          <button className="icon-btn" onClick={toggleTheme} aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}>{theme === 'dark' ? '☀' : '☾'}</button>
        </div>
        <div className="banner" role="note" data-testid="banner"><b>{banner}</b></div>
        <nav className="tabs" aria-label="Views">
          {VIEWS.map((v) => (
            <button key={v.id} aria-current={view === v.id ? 'page' : undefined} onClick={() => setView(v.id)} title={v.question}>{v.label}</button>
          ))}
          <span className="spacer" />
          <button className="secondary-tab" aria-current={view === 'studio' ? 'page' : undefined} onClick={() => setView('studio')}
            title="Configure your own campus (exploratory, not paper results)">Design studio · exploratory</button>
        </nav>
      </header>
      <main>
        {current && <p style={{ margin: '0 0 14px', fontSize: 14 }}><b style={{ color: 'var(--text-primary)' }}>{current.label}.</b> {current.question}</p>}
        {view === 'campus' && <CampusView />}
        {view === 'connection' && <ConnectionView />}
        {view === 'week' && <WeekReplayView />}
        {view === 'quantum' && <QuantumCheckView />}
        {view === 'evidence' && <EvidenceView />}
        {view === 'studio' && <StudioView />}
      </main>
      <footer>
        <div className="footer-cite">{meta.data?.citation ?? `${PAPER.title}. ICMLDE 2026, Paper ID 1939.`}</div>
        <div style={{ marginTop: 4 }}>
          Code: <a href={PAPER.repository}>{PAPER.repository.replace('https://', '')}</a> · Apache-2.0 · first author ORCID{' '}
          <a href="https://orcid.org/0000-0002-2694-8807">0000-0002-2694-8807</a> · {banner}
        </div>
      </footer>
    </>
  )
}
