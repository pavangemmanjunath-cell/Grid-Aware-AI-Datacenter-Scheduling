# ADR-0003: What-if runs are asynchronous jobs

- Status: Accepted (2026-11-21)

## Context
A capacity search solves up to 25 MILPs. Holding an HTTP request open for that time is fragile behind
proxies and gives no progress feedback.

## Decision
`POST /api/v1/simulations` validates the request (Pydantic bounds), returns `202 Accepted` with a job id,
and runs the job on a bounded thread pool (`QH2DC_MAX_WORKERS`). Clients poll
`GET /api/v1/simulations/{id}` for status, progress and result. Every result carries
`exploratory: true` and a disclaimer that it is not a paper result.

## Consequences
Simple and dependency-free for a single node. Jobs are lost on restart and not shared between processes;
replace `app/services/jobs.py` with a queue (e.g. Redis + worker) for multi-node deployment — the router
depends only on `submit`, `get` and `list`.
