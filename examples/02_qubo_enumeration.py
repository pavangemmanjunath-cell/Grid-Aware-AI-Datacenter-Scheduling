"""Example 2 - the 12-qubit placement QUBO, solved by brute force and by QAOA.  (runtime ~1 s)

Day 0 has four delay-tolerant bundles, each with three candidate slots (baseline,
+3 h, +7 h): 12 binary variables and 4,096 basis states.  This example builds the
connection-aware QUBO with the web engine, enumerates every state, and evaluates the
exact QAOA state vector at the published (pinned) angles.

    python examples/02_qubo_enumeration.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "webapp" / "backend"))

from app.engine.benchmark import load_benchmark  # noqa: E402
from app.engine.quantum import PUBLISHED_ANGLES, assignment_hours, build_qubo, qaoa_statistics  # noqa: E402

q = build_qubo(load_benchmark(str(ROOT / "data")), day=0)
print(f"variables: {q.n}  basis states: {2 ** q.n}  one-hot feasible: {len(q.feasible)}")
print(f"baseline hours:          {q.baseline_hours}")
print(f"exact optimum (by enumeration): hours {assignment_hours(q, q.best)}, QUBO cost {q.energies[q.best]:.4f}")

for p in (1, 2):
    s = qaoa_statistics(q, PUBLISHED_ANGLES[p], p)
    print(f"QAOA p={p}: feasible mass {s['feasible_mass_pct']:.2f}%, P(optimum) {s['optimum_probability_pct']:.3f}%, "
          f"most probable feasible = optimum: {s['most_probable_is_optimum']}")
print("Ideal noiseless simulation of an enumerable instance - not evidence of quantum advantage.")
