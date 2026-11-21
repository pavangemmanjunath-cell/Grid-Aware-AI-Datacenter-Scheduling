# Use cases

Status labels: **Implemented** (works in this release), **Conceptual** (possible with the current code
plus user-supplied data or settings, not validated), **Proposed** (requires new code).

## 1. Reproduce and audit the paper — Implemented

### Problem
A reviewer or reader wants to confirm that every published number follows from the stated model.
### User / stakeholder
Peer reviewers, students, reproducibility researchers.
### Inputs
Shipped benchmark; no configuration.
### Workflow
`python scripts/crosscheck.py`; optionally the MATLAB harness and `verify/check_run.py`.
### Outputs
PASS/FAIL table for 64 published values; MATLAB comparison table.
### Expected value
Independent confirmation in ~25 s, with documented reasons for any divergence.
### Assumptions
Python ≥ 3.10 with SciPy ≥ 1.11.
### Limitations
Reproduces the published scenarios only; see the list of analyses not included in [limitations.md](limitations.md).

## 2. Explain the mechanism visually — Implemented

### Problem
Show non-specialists why hydrogen and workload flexibility relieve different hours.
### User / stakeholder
Lecturers, students, conference audiences, internal stakeholders.
### Inputs
Static snapshot or running API.
### Workflow
Web app → 3D simulator; switch R0–R5; scrub the week; read the envelope chart.
### Outputs
Animated replay of the solved schedule with synchronised charts.
### Expected value
Intuition for the connection envelope, the tank and the bundle moves.
### Assumptions
A browser with WebGL.
### Limitations
Visual replay; geometry is illustrative.

## 3. Explore plant and envelope variants — Implemented (exploratory)

### Problem
How does the minimum connection change with a larger electrolyser, a deeper non-firm cut or more demand?
### User / stakeholder
Researchers, connection planners (for orientation only).
### Inputs
Electrolyser and fuel-cell ratings, tank size, efficiencies, demand/renewable scales, envelope window and level.
### Workflow
Design studio or `POST /api/v1/simulations`; poll the job.
### Outputs
Capacity, CO₂, renewable use, shifting, envelope compliance, hourly import.
### Expected value
Fast qualitative sensitivity on the same model.
### Assumptions
Same synthetic week, perfect foresight.
### Limitations
Results are **exploratory, not peer reviewed**, and labelled so by the API. Not a substitute for a
connection study.

## 4. Verifiable quantum-optimisation test instance — Implemented

### Problem
Benchmark a QUBO solver or QAOA variant on a small instance with known ground truth.
### User / stakeholder
Quantum-optimisation researchers.
### Inputs
`GET /api/v1/quantum/problem` (energies of all 4,096 states, feasible set, optimum) or `examples/02_qubo_enumeration.py`.
### Workflow
Run any solver; compare with the enumerated optimum and the published QAOA statistics.
### Outputs
Feasible mass, optimum probability, gap.
### Expected value
Exact evaluation without trusting another solver.
### Assumptions
12 variables; ideal simulation for the reference.
### Limitations
Classically trivial size; no hardware noise.

## 5. Replace synthetic signals with real data — Conceptual

### Problem
Re-run the study on a real site.
### User / stakeholder
Researchers with access to workload, site and grid data.
### Inputs
Workload trace, renewable series, carbon intensity (see [data/README.md](../data/README.md)).
### Workflow
Map the trace to the schema of `qh2dc_ingest_trace.m`, produce a benchmark CSV, run the scheduler.
### Outputs
Site-specific capacities.
### Expected value
External validation of the mechanism.
### Assumptions
Licences permit the use; power coefficients recalibrated.
### Limitations
The ingestion path is untested; no mapping for any specific public trace is provided.

## 6. Classical baselines, sensitivity and noisy QAOA — Proposed

New code is required for the analyses listed in [limitations.md](limitations.md#analyses-described-in-the-manuscript-but-not-included-in-this-release)
and [ROADMAP.md](../ROADMAP.md).

## 7. Grounded language-model assistant — Proposed

An assistant that answers questions about the study from the repository's published results only. The
interface (`webapp/backend/app/assistant/provider.py`) exists; no provider is bundled or enabled.
