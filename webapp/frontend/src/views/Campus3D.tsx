// Optional WebGL view of the same hour (React Three Fiber / three.js). The schematic is the primary visual.
import { useEffect } from 'react'
import { loadModel } from '../api/source'
import type { ScenarioKey } from '../api/types'
import { CampusScene } from '../scene/CampusScene'
import { Loading } from '../research/ui'
import { useApp } from '../state/store'

export default function Campus3D() {
  const model = useApp((s) => s.model)
  const setModel = useApp((s) => s.setModel)
  const scenario = useApp((s) => s.scenario) as ScenarioKey
  useEffect(() => { if (!model) loadModel().then(setModel).catch(() => undefined) }, [model, setModel])
  if (!model) return <Loading>Loading 3D scene…</Loading>
  return (
    <div className="scene-wrap" style={{ height: 520 }}>
      <CampusScene model={model} scenario={scenario} />
      <div className="scene-hud"><span className="hud-chip">Illustrative 3D replay of the solved schedule · not to scale</span></div>
    </div>
  )
}
