"""FastAPI application factory.

Run locally:   uvicorn app.main:app --reload --port 8000   (from webapp/backend)
OpenAPI docs:  http://localhost:8000/docs
"""
from __future__ import annotations

import hashlib
import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from .api.research import data_version
from .api.research import router as research_router
from .api.v1 import router
from .config import get_settings
from .engine.benchmark import load_benchmark
from .engine.quantum import cached_qubo
from .services.jobs import JobManager
from .services.simulation import solved_scenarios

log = logging.getLogger("qh2dc")
# Results are static per model and data version (ETag). The dashboard itself fetches with cache: "no-cache",
# so it always revalidates (cheap 304) and never mixes responses from two data versions.
CACHE = "public, max-age=86400"

TAGS = [
    {"name": "meta", "description": "Health, version and data provenance."},
    {"name": "benchmark", "description": "The synthetic 168-hour benchmark and public validation datasets."},
    {"name": "scenarios", "description": "The six published scenarios (R0-R5) with solved hourly schedules."},
    {"name": "simulations", "description": "Exploratory what-if runs. Results are not paper results."},
    {"name": "quantum", "description": "12-qubit placement QUBO and exact QAOA state-vector simulation."},
    {"name": "assistant", "description": "Language-model assistant extension point (disabled in this release)."},
    {"name": "research (read-only)", "description": "Versioned, cacheable data behind every dashboard view (/api/...)."},
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    load_benchmark(str(settings.data_dir))  # fail fast if the data file is missing or invalid
    solved_scenarios(str(settings.data_dir))  # warm the caches once instead of on concurrent first requests
    cached_qubo(str(settings.data_dir))
    app.state.jobs = JobManager(settings.max_workers, settings.max_jobs_retained)
    yield
    app.state.jobs.shutdown()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        description="Grid-connection-aware scheduling of AI data centres with green hydrogen and "
                    "quantum-assisted workload placement. Research software; the benchmark is synthetic.",
        license_info={"name": "Apache-2.0", "url": "https://www.apache.org/licenses/LICENSE-2.0"},
        openapi_tags=TAGS,
        lifespan=lifespan,
    )
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["GET", "POST"],
                       allow_headers=["*"])

    @app.middleware("http")
    async def static_cache(request: Request, call_next):
        # The read-only research endpoints serve versioned files: cache for a day, validate by ETag.
        path = request.url.path
        cacheable = request.method == "GET" and path.startswith("/api/") and not path.startswith("/api/v1/")
        if cacheable:
            etag = '"{}-{}-{}"'.format(settings.version, data_version(str(settings.data_dir)),
                                   hashlib.sha256(str(request.url.path + "?" + request.url.query).encode()).hexdigest()[:12])
            if request.headers.get("if-none-match") == etag:
                return Response(status_code=304, headers={"ETag": etag, "Cache-Control": CACHE})
        response = await call_next(request)
        if cacheable and response.status_code == 200:
            response.headers["ETag"] = etag
            response.headers["Cache-Control"] = CACHE
        return response

    @app.middleware("http")
    async def request_id(request: Request, call_next):
        rid = request.headers.get("x-request-id", uuid.uuid4().hex[:12])
        t0 = time.perf_counter()
        response = await call_next(request)
        response.headers["x-request-id"] = rid
        response.headers["server-timing"] = f"app;dur={(time.perf_counter() - t0) * 1000:.1f}"
        log.info("%s %s %s %s", rid, request.method, request.url.path, response.status_code)
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError):
        # Echo only location and message: raw inputs may be non-JSON values such as NaN.
        detail = [{"loc": list(e.get("loc", ())), "msg": e.get("msg", ""), "type": e.get("type", "")} for e in exc.errors()]
        return JSONResponse(status_code=422, content={"detail": detail})

    app.include_router(research_router)
    app.include_router(router)
    return app


app = create_app()
