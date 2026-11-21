// Animated 3D replay of one solved schedule (React Three Fiber / three.js / WebGL).
//
// Every visual quantity is driven by the solved hourly schedule of the selected
// scenario, linearly interpolated between hours for smooth motion:
//   data-hall racks  <- fixed + flexible demand        solar panels  <- solar MW
//   turbine rotors   <- wind MW                        electrolyser  <- electrolyser MW
//   hydrogen tank    <- H2 inventory (MWh-H)           fuel cell     <- fuel-cell MW
//   connection gate  <- grid import / connection cap   particle flows <- each power flow
// Nothing is re-optimised in the browser.

import { Html, OrbitControls, RoundedBox } from '@react-three/drei'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { useEffect, useMemo, useRef } from 'react'
import * as THREE from 'three'
import type { Model, ScenarioKey } from '../api/types'
import { frameAt, type Frame } from './frame'
import { useApp } from '../state/store'

const PALETTE = {
  grid: '#3987e5', renew: '#199e70', el: '#9085e9', fc: '#d55181', solar: '#e0a100', wind: '#2fa85b',
  flex: '#eb6834', rack: '#8fb8f0', critical: '#e66767', ok: '#2fa85b', warn: '#c98500',
}

function useLiveFrame(model: Model, key: ScenarioKey) {
  const f = useRef<Frame>(frameAt(model, key, useApp.getState().hour))
  useFrame(() => { f.current = frameAt(model, key, useApp.getState().hour) })
  return f
}

/** Label whose text is written from the render loop, so it never lags the playback clock. */
function LiveLabel({ model, scenario, position, text }: { model: Model; scenario: ScenarioKey; position: [number, number, number]; text: (f: Frame, h: number) => string }) {
  const ref = useRef<HTMLDivElement>(null)
  useFrame(() => {
    const h = Math.floor(useApp.getState().hour)
    const s = text(frameAt(model, scenario, h), h)
    if (ref.current && ref.current.textContent !== s) ref.current.textContent = s
  })
  return <Html position={position} center><div ref={ref} className="scene-label" /></Html>
}

// --------------------------------------------------------------- sky/light --
function SkyAndSun({ model, scenario }: { model: Model; scenario: ScenarioKey }) {
  const f = useLiveFrame(model, scenario)
  const sun = useRef<THREE.DirectionalLight>(null)
  const hemi = useRef<THREE.HemisphereLight>(null)
  const { scene } = useThree()
  const day = useMemo(() => new THREE.Color('#9cc3ea'), [])
  const night = useMemo(() => new THREE.Color('#0a1222'), [])
  const tmp = useMemo(() => new THREE.Color(), [])
  useEffect(() => { scene.background = tmp; scene.fog = new THREE.Fog(tmp, 70, 150) }, [scene, tmp])
  useFrame(() => {
    const h = f.current.hod
    const elev = Math.sin(((h - 6) / 12) * Math.PI) // >0 between 06:00 and 18:00
    const k = THREE.MathUtils.clamp(elev * 1.4 + 0.15, 0, 1)
    tmp.copy(night).lerp(day, k * 0.85)
    if (sun.current) {
      const ang = ((h - 6) / 12) * Math.PI
      sun.current.position.set(Math.cos(ang) * 40, Math.max(4, Math.sin(ang) * 40), 18)
      sun.current.intensity = 0.25 + 2.2 * Math.max(0, elev)
    }
    if (hemi.current) hemi.current.intensity = 0.55 + 0.75 * k
  })
  return (
    <>
      <hemisphereLight ref={hemi} args={['#dbe9ff', '#3a4636', 0.8]} />
      <ambientLight intensity={0.25} />
      <directionalLight ref={sun} castShadow position={[20, 30, 18]} shadow-mapSize={[1024, 1024]}>
        <orthographicCamera attach="shadow-camera" args={[-40, 40, 40, -40, 1, 120]} />
      </directionalLight>
    </>
  )
}

// --------------------------------------------------------------- data hall --
function DataHall({ model, scenario }: { model: Model; scenario: ScenarioKey }) {
  const f = useLiveFrame(model, scenario)
  const ROWS = 6, COLS = 10, N = ROWS * COLS
  const mesh = useRef<THREE.InstancedMesh>(null)
  const c = useMemo(() => new THREE.Color(), [])
  const off = useMemo(() => new THREE.Color('#1a2234'), [])
  const lit = useMemo(() => new THREE.Color(PALETTE.rack), [])
  const flexC = useMemo(() => new THREE.Color(PALETTE.flex), [])
  useEffect(() => {
    const m = new THREE.Matrix4()
    for (let r = 0; r < ROWS; r++) for (let k = 0; k < COLS; k++) {
      m.setPosition(-5.4 + k * 1.2, 1.25, -3.6 + r * 1.45)
      mesh.current!.setMatrixAt(r * COLS + k, m)
    }
    mesh.current!.instanceMatrix.needsUpdate = true
  }, [N])
  useFrame(({ clock }) => {
    const { fixed, flex } = f.current
    const nFixed = Math.round((fixed / 16) * N), nFlex = Math.round((flex / 16) * N)
    const pulse = 0.75 + 0.25 * Math.sin(clock.elapsedTime * 6)
    for (let i = 0; i < N; i++) {
      if (i < nFixed) c.copy(lit)
      else if (i < nFixed + nFlex) c.copy(flexC).multiplyScalar(pulse)
      else c.copy(off)
      mesh.current!.setColorAt(i, c)
    }
    mesh.current!.instanceColor!.needsUpdate = true
  })
  return (
    <group position={[0, 0, 0]}>
      <RoundedBox args={[14.5, 0.4, 10]} radius={0.15} position={[0, 0.2, 0]} receiveShadow>
        <meshStandardMaterial color="#2a3346" />
      </RoundedBox>
      <instancedMesh ref={mesh} args={[undefined, undefined, N]} castShadow>
        <boxGeometry args={[0.9, 2.1, 0.9]} />
        <meshStandardMaterial toneMapped={false} roughness={0.4} metalness={0.3} />
      </instancedMesh>
      <mesh position={[0, 2.0, 0]}>
        <boxGeometry args={[14.6, 3.6, 10.1]} />
        <meshPhysicalMaterial color="#9ec5f4" transparent opacity={0.08} roughness={0.1} depthWrite={false} />
      </mesh>
      <HallLabel model={model} scenario={scenario} />
    </group>
  )
}

function HallLabel({ model, scenario }: { model: Model; scenario: ScenarioKey }) {
  return <LiveLabel model={model} scenario={scenario} position={[0, 4.4, 0]}
    text={(f) => `AI data hall · ${(f.fixed + f.flex).toFixed(1)} MW${f.flex > 0 ? ` (bundle ${f.flex.toFixed(1)} MW)` : ''}`} />
}

// ------------------------------------------------------------------ solar --
function SolarField({ model, scenario }: { model: Model; scenario: ScenarioKey }) {
  const f = useLiveFrame(model, scenario)
  const R = 5, C = 8, N = R * C
  const mesh = useRef<THREE.InstancedMesh>(null)
  const mat = useRef<THREE.MeshStandardMaterial>(null)
  useEffect(() => {
    const m = new THREE.Matrix4(), q = new THREE.Quaternion().setFromEuler(new THREE.Euler(-0.55, 0, 0))
    for (let r = 0; r < R; r++) for (let k = 0; k < C; k++) {
      m.compose(new THREE.Vector3(-22 + k * 1.7, 0.7, 4 + r * 1.9), q, new THREE.Vector3(1, 1, 1))
      mesh.current!.setMatrixAt(r * C + k, m)
    }
    mesh.current!.instanceMatrix.needsUpdate = true
  }, [N])
  useFrame(() => { if (mat.current) mat.current.emissiveIntensity = 0.05 + 1.6 * (f.current.solar / 8.5) })
  const active = scenario !== 'R0'
  return (
    <group>
      <instancedMesh ref={mesh} args={[undefined, undefined, N]} castShadow receiveShadow>
        <boxGeometry args={[1.5, 0.08, 1.6]} />
        <meshStandardMaterial ref={mat} color={active ? '#1d3b66' : '#2a2f3a'} emissive={PALETTE.solar} emissiveIntensity={0.1} metalness={0.6} roughness={0.3} />
      </instancedMesh>
      <LiveLabel model={model} scenario={scenario} position={[-16, 3, 8]}
        text={(_, h) => (active ? `Solar ${model.benchmark.solar[h].toFixed(2)} MW` : 'Solar — not in R0')} />
    </group>
  )
}

// ------------------------------------------------------------------- wind --
function Turbine({ position, model, scenario, phase }: { position: [number, number, number]; model: Model; scenario: ScenarioKey; phase: number }) {
  const f = useLiveFrame(model, scenario)
  const rotor = useRef<THREE.Group>(null)
  useFrame((_, dt) => { if (rotor.current) rotor.current.rotation.z -= dt * (0.15 + f.current.wind * 0.9) })
  return (
    <group position={position}>
      <mesh position={[0, 5, 0]} castShadow>
        <cylinderGeometry args={[0.18, 0.32, 10, 12]} />
        <meshStandardMaterial color="#d9dde5" />
      </mesh>
      <mesh position={[0, 10.1, 0.3]} castShadow>
        <boxGeometry args={[0.6, 0.6, 1.4]} />
        <meshStandardMaterial color="#e8ebf0" />
      </mesh>
      <group ref={rotor} position={[0, 10.1, 1.05]} rotation={[0, 0, phase]}>
        {[0, 1, 2].map((k) => (
          <group key={k} rotation={[0, 0, (k * 2 * Math.PI) / 3]}>
            <mesh position={[0, 2.2, 0]} castShadow>
              <boxGeometry args={[0.22, 4.4, 0.06]} />
              <meshStandardMaterial color="#f2f4f7" />
            </mesh>
          </group>
        ))}
        <mesh rotation={[Math.PI / 2, 0, 0]}>
          <cylinderGeometry args={[0.25, 0.25, 0.4, 12]} />
          <meshStandardMaterial color={PALETTE.wind} />
        </mesh>
      </group>
    </group>
  )
}

function WindFarm({ model, scenario }: { model: Model; scenario: ScenarioKey }) {
  const active = scenario !== 'R0'
  return (
    <group>
      <Turbine position={[-24, 0, -10]} model={model} scenario={active ? scenario : 'R0'} phase={0} />
      <Turbine position={[-18, 0, -14]} model={model} scenario={active ? scenario : 'R0'} phase={1} />
      <Turbine position={[-12, 0, -11]} model={model} scenario={active ? scenario : 'R0'} phase={2} />
      <LiveLabel model={model} scenario={scenario} position={[-18, 13.5, -12]}
        text={(_, h) => (active ? `Wind ${model.benchmark.wind[h].toFixed(2)} MW` : 'Wind — not in R0')} />
    </group>
  )
}

// --------------------------------------------------------------- hydrogen --
function HydrogenYard({ model, scenario }: { model: Model; scenario: ScenarioKey }) {
  const f = useLiveFrame(model, scenario)
  const elMat = useRef<THREE.MeshStandardMaterial>(null)
  const fcMat = useRef<THREE.MeshStandardMaterial>(null)
  const fill = useRef<THREE.Mesh>(null)
  const TANK_H = 6
  useFrame(() => {
    const { el, fc, h2 } = f.current
    if (elMat.current) elMat.current.emissiveIntensity = 0.05 + 2.0 * (el / 4)
    if (fcMat.current) fcMat.current.emissiveIntensity = 0.05 + 2.0 * (fc / 2)
    if (fill.current) {
      const k = Math.max(0.001, h2 / 20)
      fill.current.scale.y = k
      fill.current.position.y = 0.4 + (TANK_H * k) / 2
    }
  })
  const active = ['R2', 'R3', 'R4', 'R5'].includes(scenario)
  return (
    <group position={[16, 0, 0]}>
      <RoundedBox args={[3.2, 2.4, 2.6]} radius={0.15} position={[-1, 1.2, -4.5]} castShadow>
        <meshStandardMaterial ref={elMat} color="#3b3566" emissive={PALETTE.el} emissiveIntensity={0.1} />
      </RoundedBox>
      <mesh position={[3.2, 0.4 + TANK_H / 2, -1]}>
        <cylinderGeometry args={[1.7, 1.7, TANK_H, 32, 1, true]} />
        <meshPhysicalMaterial color="#c8d6ea" transparent opacity={0.18} roughness={0.15} side={THREE.DoubleSide} depthWrite={false} />
      </mesh>
      <mesh ref={fill} position={[3.2, 0.4, -1]}>
        <cylinderGeometry args={[1.55, 1.55, TANK_H, 32]} />
        <meshStandardMaterial color={PALETTE.el} emissive={PALETTE.el} emissiveIntensity={0.6} toneMapped={false} />
      </mesh>
      <mesh position={[3.2, 0.2, -1]}>
        <cylinderGeometry args={[1.9, 1.9, 0.4, 32]} />
        <meshStandardMaterial color="#2a3346" />
      </mesh>
      <RoundedBox args={[2.6, 2.0, 2.2]} radius={0.15} position={[-1, 1.0, 3.2]} castShadow>
        <meshStandardMaterial ref={fcMat} color="#4a2238" emissive={PALETTE.fc} emissiveIntensity={0.1} />
      </RoundedBox>
      <LiveLabel model={model} scenario={scenario} position={[-1, 3.3, -4.5]} text={(f) => (active ? `Electrolyser ${f.el.toFixed(2)} MW` : 'Electrolyser — not in scenario')} />
      <LiveLabel model={model} scenario={scenario} position={[3.2, 7.4, -1]} text={(f) => (active ? `H₂ ${f.h2.toFixed(1)} / 20 MWh` : 'H₂ tank — not in scenario')} />
      <LiveLabel model={model} scenario={scenario} position={[-1, 2.8, 3.2]} text={(f) => (active ? `Fuel cell ${f.fc.toFixed(2)} MW` : 'Fuel cell — not in scenario')} />
    </group>
  )
}

// ------------------------------------------------------- grid connection --
function GridConnection({ model, scenario }: { model: Model; scenario: ScenarioKey }) {
  const f = useLiveFrame(model, scenario)
  const ring = useRef<THREE.MeshStandardMaterial>(null)
  const c = useMemo(() => new THREE.Color(), [])
  useFrame(({ clock }) => {
    const { grid, cap } = f.current
    const ratio = Number.isFinite(cap) ? grid / cap : grid / 16
    const col = ratio > 0.995 ? PALETTE.critical : ratio > 0.9 ? PALETTE.warn : PALETTE.ok
    c.set(col)
    if (ring.current) {
      ring.current.color.copy(c); ring.current.emissive.copy(c)
      ring.current.emissiveIntensity = 0.8 + (ratio > 0.995 ? 0.6 * Math.sin(clock.elapsedTime * 8) : 0)
    }
  })
  const Pylon = ({ p }: { p: [number, number, number] }) => (
    <group position={p}>
      {[[-0.6, -0.6], [0.6, -0.6], [-0.6, 0.6], [0.6, 0.6]].map(([x, z], k) => (
        <mesh key={k} position={[x * 0.6, 4, z * 0.6]} rotation={[z * 0.06, 0, -x * 0.06]}>
          <cylinderGeometry args={[0.07, 0.1, 8, 6]} />
          <meshStandardMaterial color="#9aa3b5" metalness={0.7} />
        </mesh>
      ))}
      <mesh position={[0, 7.6, 0]}><boxGeometry args={[3.4, 0.12, 0.12]} /><meshStandardMaterial color="#9aa3b5" /></mesh>
    </group>
  )
  return (
    <group>
      <Pylon p={[6, 0, -22]} />
      <Pylon p={[6, 0, -14]} />
      <RoundedBox args={[4, 2.2, 3]} radius={0.12} position={[6, 1.1, -9]} castShadow>
        <meshStandardMaterial color="#59606f" metalness={0.5} />
      </RoundedBox>
      <mesh position={[6, 2.6, -9]} rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[1.6, 0.16, 16, 48]} />
        <meshStandardMaterial ref={ring} toneMapped={false} />
      </mesh>
      <LiveLabel model={model} scenario={scenario} position={[6, 4.6, -9]}
        text={(f) => `Grid import ${f.grid.toFixed(2)} MW${Number.isFinite(f.cap) ? ` / cap ${f.cap.toFixed(2)} MW` : ' (no cap)'}`} />
    </group>
  )
}

// ----------------------------------------------------------- energy flows --
interface FlowDef { id: string; color: string; points: [number, number, number][]; max: number; pick: (f: Frame) => number }

const FLOWS: FlowDef[] = [
  { id: 'grid', color: PALETTE.grid, max: 16, pick: (f) => f.grid, points: [[6, 7.4, -22], [6, 7.4, -14], [6, 2.6, -9], [3, 2, -5.5], [0, 1.5, -3]] },
  { id: 'solar', color: PALETTE.solar, max: 9, pick: (f) => Math.min(f.solar, f.renewUsed), points: [[-15, 0.8, 7], [-10, 1.2, 5], [-6, 1.5, 2]] },
  { id: 'wind', color: PALETTE.wind, max: 5, pick: (f) => Math.max(0, f.renewUsed - Math.min(f.solar, f.renewUsed)), points: [[-18, 1, -11], [-12, 1.4, -6], [-6, 1.5, -2]] },
  { id: 'el', color: PALETTE.el, max: 4, pick: (f) => f.el, points: [[-12, 0.9, 4], [0, 0.9, 6.5], [10, 1, 0], [15, 1.2, -4.5]] },
  { id: 'tank', color: PALETTE.el, max: 4, pick: (f) => f.el, points: [[16.5, 1.4, -4.2], [18.2, 2, -2.5], [19.2, 3, -1]] },
  { id: 'fc', color: PALETTE.fc, max: 2, pick: (f) => f.fc, points: [[19.2, 1, -1], [17.5, 1, 2.2], [15, 1, 3.2]] },
  { id: 'fc2hall', color: PALETTE.fc, max: 2, pick: (f) => f.fc, points: [[14, 1, 3.2], [10, 1.2, 2.5], [6.5, 1.5, 1.5]] },
]

function Flow({ def, model, scenario }: { def: FlowDef; model: Model; scenario: ScenarioKey }) {
  const f = useLiveFrame(model, scenario)
  const N = 26
  const curve = useMemo(() => new THREE.CatmullRomCurve3(def.points.map((p) => new THREE.Vector3(...p))), [def])
  const tube = useMemo(() => new THREE.TubeGeometry(curve, 48, 0.05, 6, false), [curve])
  const mesh = useRef<THREE.InstancedMesh>(null)
  const m = useMemo(() => new THREE.Matrix4(), [])
  const v = useMemo(() => new THREE.Vector3(), [])
  const s = useMemo(() => new THREE.Vector3(), [])
  const q = useMemo(() => new THREE.Quaternion(), [])
  useFrame(({ clock }) => {
    const val = Math.max(0, def.pick(f.current))
    const share = Math.min(1, val / def.max)
    const visible = Math.round(share * N)
    const speed = 0.12 + 0.25 * share
    for (let i = 0; i < N; i++) {
      const u = (i / N + clock.elapsedTime * speed) % 1
      curve.getPointAt(u, v)
      const sc = i < visible ? 0.16 + 0.1 * share : 0
      s.set(sc, sc, sc)
      m.compose(v, q, s)
      mesh.current!.setMatrixAt(i, m)
    }
    mesh.current!.instanceMatrix.needsUpdate = true
  })
  return (
    <group>
      <mesh geometry={tube}>
        <meshBasicMaterial color={def.color} transparent opacity={0.22} />
      </mesh>
      <instancedMesh ref={mesh} args={[undefined, undefined, N]}>
        <sphereGeometry args={[1, 10, 10]} />
        <meshBasicMaterial color={def.color} toneMapped={false} />
      </instancedMesh>
    </group>
  )
}

// ------------------------------------------------------------------ scene --
export function CampusScene({ model, scenario }: { model: Model; scenario: ScenarioKey }) {
  return (
    <Canvas shadows dpr={[1, 2]} camera={{ position: [30, 22, 34], fov: 42 }} gl={{ antialias: true }}>
      <SkyAndSun model={model} scenario={scenario} />
      <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
        <circleGeometry args={[60, 64]} />
        <meshStandardMaterial color="#33453a" roughness={1} />
      </mesh>
      <gridHelper args={[120, 60, '#47604f', '#3b5043']} position={[0, 0.01, 0]} />
      <DataHall model={model} scenario={scenario} />
      <SolarField model={model} scenario={scenario} />
      <WindFarm model={model} scenario={scenario} />
      <HydrogenYard model={model} scenario={scenario} />
      <GridConnection model={model} scenario={scenario} />
      {FLOWS.map((d) => <Flow key={d.id} def={d} model={model} scenario={scenario} />)}
      <OrbitControls makeDefault enableDamping maxPolarAngle={Math.PI / 2.15} minDistance={15} maxDistance={90} target={[-2, 2, -2]} />
    </Canvas>
  )
}
