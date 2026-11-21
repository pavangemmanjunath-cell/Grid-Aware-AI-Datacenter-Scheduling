// Exact QAOA state-vector simulation in the browser (12 qubits, 4,096 amplitudes).
// Same ansatz as webapp/backend/app/engine/quantum.py and verify/verify_python.py:
// phase separation exp(-i gamma * E_s / max|E|) followed by exp(-i beta X) on every qubit.

export interface QaoaStats {
  probabilities: Float64Array
  expectedCost: number
  feasibleMass: number
  optimumProbability: number
  mostProbableFeasible: number
}

export function qaoa(energies: number[], feasible: number[], best: number, angles: number[], p: number): QaoaStats {
  const N = energies.length
  const n = Math.round(Math.log2(N))
  let maxAbs = 0
  for (const e of energies) maxAbs = Math.max(maxAbs, Math.abs(e))
  const re = new Float64Array(N).fill(1 / Math.sqrt(N))
  const im = new Float64Array(N)
  for (let layer = 0; layer < p; layer++) {
    const g = angles[layer]
    const b = angles[p + layer]
    for (let s = 0; s < N; s++) {
      const phi = -g * (energies[s] / maxAbs)
      const c = Math.cos(phi), si = Math.sin(phi)
      const r = re[s], i = im[s]
      re[s] = r * c - i * si
      im[s] = r * si + i * c
    }
    const cb = Math.cos(b), sb = Math.sin(b)
    for (let q = 0; q < n; q++) {
      const bit = 1 << q
      for (let s = 0; s < N; s++) {
        if (s & bit) continue
        const t = s | bit
        const ar = re[s], ai = im[s], br = re[t], bi = im[t]
        // [a; b] <- [cos b, -i sin b; -i sin b, cos b] [a; b]
        re[s] = cb * ar + sb * bi
        im[s] = cb * ai - sb * br
        re[t] = cb * br + sb * ai
        im[t] = cb * bi - sb * ar
      }
    }
  }
  const pr = new Float64Array(N)
  let exp = 0
  for (let s = 0; s < N; s++) {
    pr[s] = re[s] * re[s] + im[s] * im[s]
    exp += pr[s] * energies[s]
  }
  let mass = 0, top = feasible[0]
  for (const f of feasible) {
    mass += pr[f]
    if (pr[f] > pr[top]) top = f
  }
  return { probabilities: pr, expectedCost: exp, feasibleMass: mass * 100, optimumProbability: pr[best] * 100, mostProbableFeasible: top }
}

export function assignmentHours(state: number, candidateHours: number[][], slots: number): number[] {
  return candidateHours.map((cands, j) => {
    for (let k = 0; k < slots; k++) if ((state >> (j * slots + k)) & 1) return cands[k]
    return NaN
  })
}
