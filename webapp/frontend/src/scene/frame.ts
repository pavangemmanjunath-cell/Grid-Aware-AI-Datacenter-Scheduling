// Interpolated state of the campus at a fractional hour; shared by the 3D scene and the readouts.
import type { Model, ScenarioKey } from '../api/types'

export interface Frame {
  t: number; hod: number; fixed: number; flex: number; solar: number; wind: number; grid: number
  el: number; fc: number; h2: number; curtailed: number; renewUsed: number; cap: number
}

export function frameAt(model: Model, key: ScenarioKey, t: number): Frame {
  const b = model.benchmark
  const sc = model.scenarios[key].series
  const i0 = Math.floor(t) % 168, i1 = (i0 + 1) % 168, a = t - Math.floor(t)
  const L = (arr: number[] | null | undefined, fallback = 0) =>
    arr ? (arr[i0] ?? fallback) * (1 - a) + (arr[i1] ?? fallback) * a : fallback
  const hasRen = key !== 'R0'
  const capArr = model.scenarios[key].cap
  const solar = hasRen ? L(b.solar) : 0, wind = hasRen ? L(b.wind) : 0
  const el = L(sc.electrolyser), curtailed = L(sc.curtailed)
  return {
    t, hod: (t % 24 + 24) % 24, fixed: L(b.fixedLoad), flex: L(sc.flexLoad), solar, wind, grid: L(sc.grid),
    el, fc: L(sc.fuelcell), h2: L(sc.h2), curtailed,
    renewUsed: Math.max(0, solar + wind - curtailed - el),
    cap: capArr ? (capArr[i0] ?? Infinity) : Infinity,
  }
}
