import { useQuery } from '@tanstack/react-query'
import { CONTRIBUTIONS, LIMITATIONS, NOT_IN_RELEASE, PAPER, PROBLEM } from '../content'
import { useMeta } from '../research/api'
import { Cite, Loading, Unavailable } from '../research/ui'

const METHOD = [
  ['1 · Data layer', 'Latency-sensitive vs delay-tolerant AI work, solar, wind, carbon intensity and the connection envelope joined on one hourly clock.', 'Sec. 3'],
  ['2 · Benchmark', 'Deterministic synthetic 168-h week (seed 20260430); 28 bundles with candidate slots 0 / +3 / +7 h.', 'Sec. 3.2, Table 1'],
  ['3 · MILP + bisection', 'Hourly MILP over grid import, electrolyser, H₂ inventory, fuel cell and placement; bisection finds the smallest feasible uniform cap.', 'Sec. 4'],
  ['4 · QUBO / QAOA check', 'The daily placement block as a 12-variable QUBO; exact QAOA at p = 1, 2, verified against all 4,096 states.', 'Sec. 5'],
]

const RELATED = [
  ['M. Liu et al., 2025, Sustain. Energy Technol. Assess. 83', 'Data centre with power-to-hydrogen, cost objective', '10.1016/j.seta.2025.104661'],
  ['I. Riepin, T. Brown, V. M. Zavala, 2025, Adv. Appl. Energy 17', 'Spatio-temporal load shifting', '10.1016/j.adapen.2024.100202'],
  ['A. Ajagekar, F. You, 2024, Adv. Appl. Energy 14', 'Quantum circuits for data-centre energy control', '10.1016/j.adapen.2024.100179'],
  ['T. Morstyn, Y. Zhou, I. Whitfield, 2026, IEEE Energy Sustain. Mag. 2(1)', 'AI data-centre grid defection', '10.1109/esm.2025.3628276'],
  ['V. Dvorkin, 2025, IEEE Trans. Power Syst. 40(2)', 'Data-centre flexibility coordination', '10.1109/tpwrs.2024.3442954'],
  ['A. Wilkie et al., 2024, Phys. Rev. A 110', 'QAOA depth behaviour', '10.1103/physreva.110.022441'],
]

const DOWNLOADS: [string, string][] = [
  ['research_benchmark_168h.csv', 'Benchmark (168 h, synthetic)'],
  ['research_flexible_jobs.csv', 'Flexible job bundles'],
  ['research_results_gridflex.csv', 'Scenario results (Table 2)'],
  ['verification_summary.json', 'QUBO / QAOA verification'],
  ['research_job_placement.csv', 'Chosen slot per bundle and scenario'],
  ['research_dispatch_R4.csv', 'Hourly dispatch R4 (all six available)'],
]

interface DatasetDoc { verified_utc: string; datasets: { name: string; signal: string; url: string; licence: string; commercial_use: string }[] }

function fmtAssumption(v: unknown): string {
  if (Array.isArray(v)) return v.join(' / ')
  if (v && typeof v === 'object') return Object.entries(v as Record<string, unknown>).map(([k, x]) => `${k} ${fmtAssumption(x)}`).join(' · ')
  return String(v)
}

export function EvidenceView() {
  const meta = useMeta()
  const ds = useQuery({ queryKey: ['datasets'], queryFn: async () => (await fetch('data/public_datasets.json')).json() as Promise<DatasetDoc>, staleTime: Infinity })
  if (meta.isError) return <Unavailable />
  if (!meta.data) return <Loading />
  const m = meta.data
  return (
    <div className="grid" style={{ gap: 16 }}>
      <div className="layout-12">
        <div className="span-8 card">
          <h3>What the study asks</h3>
          <p>{PROBLEM.statement}</p>
          <p><b style={{ color: 'var(--text-primary)' }}>Research question.</b> {PROBLEM.question}</p>
          <ol className="contrib">{CONTRIBUTIONS.map(([h, d]) => <li key={h}><b>{h}</b> — {d}</li>)}</ol>
        </div>
        <div className="span-4 card" data-testid="citation">
          <h3>Cite this work</h3>
          <p style={{ fontSize: 13.5, color: 'var(--text-primary)' }}>{m.citation}</p>
          <p style={{ fontSize: 13 }}>{m.code_citation}</p>
          <p style={{ fontSize: 12.5 }}>Paper DOI: <b>{m.paper_doi ?? 'not yet available'}</b> · Software DOI: <b>{m.software_doi ?? 'issued by Zenodo at the first GitHub release'}</b></p>
          <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
            <img src="qr-github.svg" alt={`QR code linking to ${PAPER.repository}`} width={104} height={104} style={{ background: '#fff', padding: 4, borderRadius: 6 }} />
            <div style={{ fontSize: 12.5 }}>
              <a href={PAPER.repository} target="_blank" rel="noreferrer">{PAPER.repository.replace('https://', '')}</a><br />
              First author ORCID <a href={m.orcid_first_author} target="_blank" rel="noreferrer">0000-0002-2694-8807</a>
            </div>
          </div>
        </div>
      </div>

      <div className="card">
        <h3>Method in four steps</h3>
        <div className="pipeline" style={{ gridTemplateColumns: 'repeat(4, minmax(0, 1fr))' }}>
          {METHOD.map(([h, d, sec]) => (
            <div className="stage" key={h}><h4 style={{ marginTop: 0 }}>{h}</h4><p style={{ fontSize: 13, marginBottom: 6 }}>{d}</p><Cite anchor={sec} /></div>
          ))}
        </div>
      </div>

      <div className="layout-12">
        <div className="span-6 card table-wrap" data-testid="assumptions">
          <h3><span>Assumptions</span><Cite anchor="Table 1" source={`/api/meta · ${String(m.assumptions.source)}`} /></h3>
          <table className="data">
            <tbody>
              {Object.entries(m.assumptions).filter(([k]) => k !== 'source').map(([k, v]) => (
                <tr key={k}><td>{k.replace(/_/g, ' ')}</td><td style={{ whiteSpace: 'normal', textAlign: 'left' }}>{fmtAssumption(v)}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="span-6 grid" style={{ gap: 16 }}>
          <div className="card">
            <h3>Downloads <span className="sub">model {m.model_version} · data {m.data_version}</span></h3>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {DOWNLOADS.map(([f, label]) => <a key={f} className="dl" href={`data/${f}`} download>⬇ {label}</a>)}
            </div>
            <p style={{ fontSize: 12.5, marginTop: 8 }}>Solver: {m.solver.published_table}. Hourly files: {m.solver.hourly_dispatch}.</p>
          </div>
          <div className="card">
            <h3>Known differences from the manuscript</h3>
            <ul className="ticks">{m.known_differences_from_manuscript.map((k) => <li key={k}>{k}</li>)}</ul>
            <p style={{ fontSize: 12.5 }}>The dashboard always shows the published data files; see PAPER_CODE_ALIGNMENT.md.</p>
          </div>
        </div>
      </div>

      <div className="layout-12">
        <div className="span-6 card table-wrap">
          <h3>Related work <span className="sub">cited by author and year</span></h3>
          <table className="data"><tbody>
            {RELATED.map(([w, why, doi]) => (
              <tr key={doi}><td style={{ whiteSpace: 'normal' }}>{w}<div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{why}</div></td>
                <td><a href={`https://doi.org/${doi}`} target="_blank" rel="noreferrer">doi</a></td></tr>
            ))}
          </tbody></table>
          <p style={{ fontSize: 12.5 }}>A dated survey of 6 papers, 5 patents and 21 repositories is in docs/related-work.md.</p>
        </div>
        <div className="span-6 card">
          <h3>Limits of the evidence</h3>
          <ul className="ticks">{LIMITATIONS.map((l) => <li key={l}>{l}</li>)}</ul>
          <p className="notice" style={{ fontSize: 13 }}><strong>Not part of this release:</strong> {NOT_IN_RELEASE.join('; ')}.</p>
          <p className="notice info" style={{ fontSize: 13 }}><strong>Expert review requested.</strong> All data are simulated. Results support claims about the
            mechanism, not about any specific site; independent review by grid, hydrogen and data-centre specialists is invited (see CONTRIBUTING.md).</p>
        </div>
      </div>

      <div className="card table-wrap">
        <h3>Candidate public datasets <span className="sub">none is connected · terms verified {ds.data?.verified_utc ?? '—'}</span></h3>
        {ds.isError ? <Unavailable /> : !ds.data ? <Loading /> : (
          <table className="data">
            <thead><tr><th>Dataset</th><th>Could replace</th><th>Licence</th><th>Commercial use</th></tr></thead>
            <tbody>{ds.data.datasets.map((x) => (
              <tr key={x.name}><td style={{ whiteSpace: 'normal' }}><a href={x.url} target="_blank" rel="noreferrer">{x.name}</a></td>
                <td style={{ whiteSpace: 'normal' }}>{x.signal}</td><td style={{ whiteSpace: 'normal' }}>{x.licence}</td><td style={{ whiteSpace: 'normal' }}>{x.commercial_use}</td></tr>
            ))}</tbody>
          </table>
        )}
      </div>
    </div>
  )
}
