"""In-process job runner for long-running what-if simulations.

A what-if run with a capacity search solves the MILP up to 25 times, so the API
accepts it, returns ``202 Accepted`` with a job id, and runs it on a bounded thread
pool.  State is kept in memory: this is a single-node research service.  For a
multi-node deployment replace this module with a queue (e.g. Redis + a worker);
the router depends only on ``submit`` / ``get`` / ``list``.
"""
from __future__ import annotations

import threading
import time
import uuid
from collections import OrderedDict
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from ..schemas import Job, JobStatus, WhatIfRequest, WhatIfResult


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class QueueFull(RuntimeError):
    """Raised when too many jobs are queued or running; the API answers 429."""


ACTIVE = (JobStatus.queued, JobStatus.running)


class JobManager:
    def __init__(self, max_workers: int, max_retained: int, max_active: int | None = None):
        self._pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="qh2dc-sim")
        self._jobs: OrderedDict[str, Job] = OrderedDict()
        self._lock = threading.Lock()
        self._max = max_retained
        self._max_active = max_active or 4 * max_workers

    def submit(self, req: WhatIfRequest, fn: Callable[[WhatIfRequest, Callable[[float], None]], WhatIfResult]) -> Job:
        job = Job(id=uuid.uuid4().hex, status=JobStatus.queued, progress=0.0, request=req, created_utc=_now())
        with self._lock:
            if sum(j.status in ACTIVE for j in self._jobs.values()) >= self._max_active:
                raise QueueFull(f"{self._max_active} simulations already queued or running; try again shortly")
            self._jobs[job.id] = job
            # evict the oldest *finished* jobs only; active jobs are never dropped
            for old_id in [k for k, j in self._jobs.items() if j.status not in ACTIVE]:
                if len(self._jobs) <= self._max:
                    break
                del self._jobs[old_id]
        self._pool.submit(self._run, job.id, req, fn)
        return job

    def _update(self, job_id: str, **changes) -> None:
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id] = self._jobs[job_id].model_copy(update=changes)

    def _run(self, job_id: str, req: WhatIfRequest, fn) -> None:
        t0 = time.perf_counter()
        self._update(job_id, status=JobStatus.running)
        try:
            result = fn(req, lambda p: self._update(job_id, progress=round(min(max(p, 0.0), 1.0), 3)))
            self._update(job_id, status=JobStatus.succeeded, progress=1.0, result=result,
                         finished_utc=_now(), runtime_s=round(time.perf_counter() - t0, 3))
        except Exception as exc:  # surfaced to the client, never swallowed
            self._update(job_id, status=JobStatus.failed, error=f"{type(exc).__name__}: {exc}",
                         finished_utc=_now(), runtime_s=round(time.perf_counter() - t0, 3))

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def list(self) -> list[Job]:
        with self._lock:
            return list(reversed(self._jobs.values()))

    def shutdown(self) -> None:
        self._pool.shutdown(wait=False, cancel_futures=True)
