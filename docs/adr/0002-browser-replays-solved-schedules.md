# ADR-0002: The browser replays solved schedules

- Status: Accepted (2026-11-21)

## Context
The simulator must be animated and responsive, and must never show numbers that differ from the solved
model. Re-solving a MILP in the browser would need a WebAssembly solver and could diverge from HiGHS.

## Decision
The 3D scene and charts replay hourly schedules solved by the Python engine (served by the API or shipped
in a static snapshot) and interpolate between hours for motion. The only client-side computation is the
12-qubit QAOA state vector, which is exact, deterministic and cheap (4,096 amplitudes).

## Consequences
Animation is smooth and cannot contradict the published results. Interactive "what-if" changes require
the backend; without it the front end degrades to a read-only static mode.
