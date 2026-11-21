# Code review of the MATLAB package (2026-08-29)

> Internal pre-submission code audit of the MATLAB package, performed for the authors on 2026-08-29. It is
> not part of the conference peer review and contains no reviewer correspondence. Finding numbers (S1–S4,
> M1–M4, L1–L4) are referenced elsewhere. Section numbers refer to the manuscript draft of that date. Text
> preserved as written, except one reference to a folder not included in this repository.


Reviewed against a real execution on MATLAB R2026a (no Optimization Toolbox), not by
reading alone. Every defect below was either observed in a run or confirmed by a
targeted experiment.

**Overall.** This is well above the median research codebase. Single-source
configuration, a validation gate on the data layer, an exhaustive reference for the
quantum block, and an independently written second implementation are all things most
published packages lack. The defects are concentrated in one place: the toolbox-free
fallback, which is the path most external reviewers will actually execute, because
most machines do not have the Optimization Toolbox.

---

## Findings

### S1 — Fallback drained the hydrogen tank below the terminal constraint *(fixed)*

`qh2dc_fallback_dispatch.m`, pass 2.

The discharge budget was `min(h(t:T))`, which enforces only `h >= 0`. The terminal
condition `H_T = H_final` was enforced nowhere: the block at the end corrected only
`resid > 0` (too much hydrogen left), never `resid < 0`.

Observed: `h2_terminal_MWh = 0` against a configured `H_final = 5`.

This is the most serious finding, because that constraint is not incidental — §3.2 of
the manuscript introduces it specifically so "the optimiser cannot manufacture an
apparent benefit by draining the tank on the last day", and the fallback did exactly
that. It also made the MATLAB-rendered Fig. 6 contradict its own caption, which
promises an inventory "returning to its initial level at the end of the horizon".

Fixed by bounding the budget by `min(min(h(t:T)), h(T) - H_final)`. Terminal
inventory is now exactly 5.0 and Fig. 6 closes at its starting value.

**Consequence, stated plainly:** with the constraint enforced the heuristic has less
hydrogen to lean on, so R3 now moves 5 bundles rather than 3 (17.9 % shifted, 0.68 h
average, against the MILP's 10.7 % and 0.46 h). That group now reports FAIL. This is
the right trade: a valid solution that differs from the MILP is worth more than an
invalid one that happens to match. All six connection capacities still reproduce
exactly.

### S2 — Delay tie-break could veto a feasibility-restoring move *(fixed)*

`qh2dc_fallback_dispatch.m`, placement search.

`score = (exc - exc_t) - 1e-3 * max(dDelay, 0)` collapses two incommensurable
quantities into one number. On R4 the search descends to 0.004489 MWh of residual
exceedance and then stops: the final move is worth 0.004489 but costs
`7 h x 1e-3 = 0.007`, so it scores negative and is rejected — **0.0045 MWh short of
feasibility**. R4 was reported infeasible and the whole run died.

The docstring already describes the intent correctly ("the bundle whose relocation
removes the most exceedance *for the least delay*"), i.e. delay is a tie-break. Fixed
by making the comparison lexicographic.

**Design note for the authors:** any scalarisation of "constraint violation" against
"solution quality" has this failure mode. Feasibility should dominate lexicographically
whenever it is a hard requirement, as it is here.

### S3 — Infeasibility surfaced as an unrelated type error *(fixed)*

`qh2dc_dispatch` returns `[]`; `qh2dc_metrics` then evaluated `S.pg` on a `double` and
raised `Dot indexing is not supported for variables of type double`. That names
neither the scenario nor the cause, and sends the reader to the wrong file.

Fixed with `qh2dc_assert_feasible.m`, called from `main_qh2dc` after each scenario. It
names the scenario and distinguishes "the MILP proved infeasibility" from "the
heuristic could not find a placement the MILP would have found".

### S4 — Figure window hard-coded independently of the data it marks *(fixed)*

`qh2dc_figures.m`, gr3.

The landscape grid was `bv = linspace(-1.5, 1.5, ng)` while the marker is plotted at
`QA.params(2)`. The two are unrelated. This run's optimiser returned `beta ~ 2.76`
rather than the shipped `-0.379` — an equivalent optimum, identical expectation to
eight significant figures — and the marker landed **outside the contoured region**,
floating in white space while MATLAB silently expanded the axis.

Fixed by centring the window on the optimised angles. Any figure that marks a computed
point inside a hand-chosen window has this bug latent in it.

### M1 — `viol_MWh` is structurally always zero on the fallback path *(not fixed — measurement design)*

`qh2dc_fallback_dispatch.m` ends with `ps = max(0, pg - cap); pg = min(pg, cap)`. It
clips import to the cap and books the remainder as unserved energy. But
`qh2dc_metrics` computes `viol_MWh = sum(max(0, S.pg - S.cap))` — on already-clipped
`pg`, which is identically zero by construction.

So "Envelope compliance PASS (6/6)" carries **no information** on the fallback path.
The quantity that actually matters there is `shed_MWh`. On the MILP path `viol_MWh` is
meaningful, because `pg` is bounded by the cap in the solver rather than clipped
afterwards.

Recommend the metric assert that shed is zero whenever violation is reported as zero,
so the two paths cannot silently disagree about what compliance means. I have not
changed it, because it affects a published metric definition.

### M2 — Residual unserved energy passes the feasibility gate

`qh2dc_dispatch` accepts a solution when `sum(S.ps) <= 1e-6`. Observed on R3:
`shed_MWh = 4.67e-07`. Numerically negligible, but the manuscript states unserved
energy is zero in every optimised case, and strictly it is 4.7e-7 MWh, not 0.

Either tighten the gate or say "below 1e-6 MWh". I have not changed the tolerance,
because tightening it could flip a published scenario to infeasible.

### M3 — QAOA reproducibility depends on unstable primitives

`qh2dc_qaoa.m` seeds with the legacy `rand('seed', ...)` and optimises with
`fminsearch`. Neither is contractually stable across MATLAB releases. Observed: `p=1`
reproduces to eight significant figures, `p=2` does not (93.11 % feasible mass here
against 67.13 % published — a *better* local optimum, not a worse one).

`verify_python.py` already sidesteps this by pinning the angles. The MATLAB path
should do the same for the published depths, or the paper should mark those two
percentages as optimiser-dependent. Flagged rather than changed: choosing which run
is authoritative is the authors' call, not mine.

### M4 — `qh2dc_ingest_trace.m` is unreachable and untested

The production-trace path is documented in the README and referenced in the paper as
the route to external validation, but nothing calls it, no fixture exercises it, and
it would fail on any trace whose columns are not already renamed to its expected
schema. It also silently truncates to `cfg.T` via `Rn.solar_MW(1:T)`, which errors
unhelpfully if the renewable file is shorter than the horizon.

A ten-row synthetic fixture and one smoke test would make the paper's external-validation
claim demonstrable rather than aspirational.

### L1 — Quadratic array growth in the sparse assembly

`qh2dc_dispatch.m` builds `rI/rJ/rV` with `[rI; t]` inside nested loops. At T=168 this
is invisible; at T=8760 it is the dominant cost. Preallocate if the horizon is ever
extended.

### L2 — `local_dispatch` recomputes the whole week per candidate move

The placement search evaluates `J.n * J.K = 84` full-horizon dispatches per iteration.
Moving one bundle perturbs a handful of hours. Fine at this size, but the search is
`O(n^2 K^2 T)` and will not extend to a month.

### L3 — Legend overlap in MATLAB-rendered gr5/gr6

Legends are placed `northwest`/`north` with `Orientation','horizontal'` and overlap the
data. Cosmetic only, and it does not affect the manuscript, which embeds the Python
renders (`verify/verify_python.py`). Worth fixing if the MATLAB figures are ever used directly.

### L4 — Dead variable

`qh2dc_fallback_dispatch.m` declares `pg = zeros(T,1)` before pass 1 and unconditionally
overwrites it after pass 2.

---

## What is genuinely good

- **`qh2dc_config.m` as single source of truth.** The claim that nothing is hard-coded
  elsewhere held up under grep.
- **The validation gate in `qh2dc_load_benchmark.m`.** Asserting that `load_base`
  equals `fixed + flex` and `ren` equals `solar + wind` catches the class of error that
  silently corrupts results.
- **`qh2dc_qubo_bruteforce.m`.** Exhaustively enumerating 2^12 states as the reference,
  and keeping the instance small *specifically so that this is possible*, is the right
  instinct and is honestly labelled "a verification device, not part of the proposed
  method".
- **Returning `[]` for infeasibility** makes `qh2dc_min_capacity`'s bisection oracle
  clean and correct. Monotonicity is stated and relied on deliberately.
- **The terminal-inventory constraint in the MILP** is real anti-gaming, correctly
  implemented there (`lb(ih(T)) = ub(ih(T)) = HF`).
- **`verify_python.py`** is a genuine second implementation, not a wrapper, and its
  header is candid about the one thing it replays rather than recomputes.

---

## Priorities

| | Item | Status |
|---|---|---|
| 1 | S1 terminal inventory | fixed |
| 2 | S2 feasibility veto | fixed |
| 3 | S3 error message | fixed |
| 4 | S4 figure window | fixed |
| 5 | M3 pin QAOA angles or mark version-dependent | **authors' decision** |
| 6 | M1 make `viol_MWh` meaningful on both paths | recommended |
| 7 | M2 state the 1e-6 shed tolerance | recommended |
| 8 | M4 smoke-test the ingestion path | recommended before the journal version |
| 9 | L1–L4 | optional |
