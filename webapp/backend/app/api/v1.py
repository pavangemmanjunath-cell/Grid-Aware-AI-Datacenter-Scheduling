"""Version 1 of the HTTP API. All routes are mounted under /api/v1."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from ..assistant.provider import get_provider
from ..config import Settings, get_settings
from ..engine.benchmark import load_benchmark
from ..engine.quantum import PUBLISHED_ANGLES, assignment_hours, cached_qubo, optimise_angles, qaoa_statistics
from ..engine.scenarios import SCENARIOS
from ..schemas import (
    AssistantQuestion,
    AssistantStatus,
    Health,
    Job,
    Metrics,
    PublicDataset,
    QaoaEvaluateRequest,
    QaoaOptimiseRequest,
    QaoaStatistics,
    QuboProblem,
    ScenarioDetail,
    ScenarioSummary,
    WhatIfRequest,
)
from ..services.jobs import QueueFull
from ..services.simulation import provenance, public_datasets, published_table, run_whatif, series_of, solved_scenarios

router = APIRouter(prefix="/api/v1")


def data_dir(settings: Settings = Depends(get_settings)) -> str:
    return str(settings.data_dir)


# ---------------------------------------------------------------- meta -----
@router.get("/health", response_model=Health, tags=["meta"])
def health(settings: Settings = Depends(get_settings)):
    return Health(status="ok", version=settings.version, benchmark_hours=load_benchmark(str(settings.data_dir)).T)


@router.get("/provenance", tags=["meta"], summary="Data-file hashes and the origin of every number")
def get_provenance(d: str = Depends(data_dir)):
    return provenance(d)


# ----------------------------------------------------------- benchmark -----
@router.get("/benchmark", tags=["benchmark"], summary="The 168-hour synthetic benchmark week")
def benchmark(d: str = Depends(data_dir)):
    b = load_benchmark(d)
    rnd = lambda a, n=4: [round(float(v), n) for v in a]  # noqa: E731
    return {
        "hours": b.T, "synthetic": True,
        "hour_of_day": b.hour_of_day.tolist(), "fixed_load_MW": rnd(b.fixed), "flexible_baseline_MW": rnd(b.flex),
        "solar_MW": rnd(b.solar), "wind_MW": rnd(b.wind), "renewable_MW": rnd(b.renewable),
        "carbon_kgCO2_per_MWh": rnd(b.carbon, 2), "cap_nonfirm_MW": rnd(b.cap_nonfirm, 3),
        "cap_phased_MW": rnd(b.cap_phased, 3),
        "bundles": [{"baseline_hour": int(t0), "energy_MWh": round(float(e), 4), "candidates": c}
                    for t0, e, c in zip(b.bundle_hours, b.bundle_energy, b.candidates(), strict=True)],
    }


@router.get("/datasets", response_model=list[PublicDataset], tags=["benchmark"],
            summary="Public datasets for external validation (not used for the published numbers)")
def datasets(d: str = Depends(data_dir)):
    return public_datasets(d)


# ----------------------------------------------------------- scenarios -----
@router.get("/scenarios", response_model=list[ScenarioSummary], tags=["scenarios"])
def scenarios(d: str = Depends(data_dir)):
    table = published_table(d)
    return [ScenarioSummary(key=k, label=s.label, description=s.description, published=table[k])
            for k, s in SCENARIOS.items()]


@router.get("/scenarios/{key}", response_model=ScenarioDetail, tags=["scenarios"],
            summary="Published row plus the hour-by-hour solved schedule")
def scenario(key: str, d: str = Depends(data_dir)):
    key = key.upper()
    if key not in SCENARIOS:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"unknown scenario '{key}' (R0-R5)")
    s, res = SCENARIOS[key], solved_scenarios(d)[key]
    return ScenarioDetail(key=key, label=s.label, description=s.description, published=published_table(d)[key],
                          connection_capacity_MW=res.connection_capacity_MW, metrics=Metrics(**res.metrics),
                          bundle_delays_h=[int(x) for x in res.schedule.delays], series=series_of(res.schedule))


# --------------------------------------------------------- simulations -----
@router.post("/simulations", response_model=Job, status_code=status.HTTP_202_ACCEPTED, tags=["simulations"],
             summary="Start an exploratory what-if simulation (asynchronous)")
def create_simulation(req: WhatIfRequest, request: Request, d: str = Depends(data_dir)):
    try:
        return request.app.state.jobs.submit(req, lambda r, progress: run_whatif(d, r, progress))
    except QueueFull as exc:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, str(exc)) from exc


@router.get("/simulations", response_model=list[Job], tags=["simulations"])
def list_simulations(request: Request):
    return request.app.state.jobs.list()


@router.get("/simulations/{job_id}", response_model=Job, tags=["simulations"])
def get_simulation(job_id: str, request: Request):
    job = request.app.state.jobs.get(job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unknown simulation id")
    return job


# ------------------------------------------------------------- quantum -----
@router.get("/quantum/problem", response_model=QuboProblem, tags=["quantum"],
            summary="The 12-variable daily placement QUBO, enumerated exhaustively")
def qubo_problem(d: str = Depends(data_dir)):
    q = cached_qubo(d)
    return QuboProblem(qubits=q.n, basis_states=2 ** q.n, bundles=q.bundles, slots=q.slots,
                       baseline_hours=q.baseline_hours, candidate_hours=q.candidate_hours,
                       feasible_states=q.feasible.tolist(), best_state=q.best, best_energy=float(q.energies[q.best]),
                       best_assignment_hours=assignment_hours(q, q.best),
                       energies=[round(float(e), 6) for e in q.energies],
                       published_angles={str(k): v for k, v in PUBLISHED_ANGLES.items()})


@router.post("/quantum/evaluate", response_model=QaoaStatistics, tags=["quantum"],
             summary="Exact QAOA state-vector statistics at given angles")
def qaoa_evaluate(req: QaoaEvaluateRequest, d: str = Depends(data_dir)):
    s = qaoa_statistics(cached_qubo(d), req.angles, req.p)
    probs = s.pop("probabilities")
    return QaoaStatistics(**s, probabilities=[float(f"{v:.6g}") for v in probs] if req.include_probabilities else None)


@router.post("/quantum/optimise", tags=["quantum"],
             summary="Optimise QAOA angles from random restarts (exploratory; optimiser-dependent)")
def qaoa_optimise(req: QaoaOptimiseRequest, d: str = Depends(data_dir)):
    q = cached_qubo(d)
    out = optimise_angles(q, req.p, req.restarts, req.seed, req.max_evals)
    stats = qaoa_statistics(q, out["best"]["angles"], req.p)
    stats.pop("probabilities")
    return {"exploratory": True, "runs": out["runs"], "best": stats,
            "note": "Angles and feasible mass depend on the optimiser, seed and budget; "
                    "the published Table 3 values use the pinned angles from /quantum/problem."}


# ----------------------------------------------------------- assistant -----
@router.get("/assistant", response_model=AssistantStatus, tags=["assistant"])
def assistant_status(settings: Settings = Depends(get_settings)):
    p = get_provider(settings.llm_provider)
    return AssistantStatus(enabled=p.enabled, provider=p.name,
                           message="Language-model assistant is not configured in this release." if not p.enabled
                           else "Assistant answers are grounded in the repository's published results.")


@router.post("/assistant/ask", tags=["assistant"], status_code=status.HTTP_501_NOT_IMPLEMENTED,
             responses={501: {"description": "No assistant provider configured"}})
def assistant_ask(_: AssistantQuestion, settings: Settings = Depends(get_settings)):
    p = get_provider(settings.llm_provider)
    if not p.enabled:
        raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "assistant not configured (QH2DC_LLM_PROVIDER=none)")
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "no assistant provider bundled")  # pragma: no cover
