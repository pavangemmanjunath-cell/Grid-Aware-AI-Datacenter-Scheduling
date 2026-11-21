"""Public API contract (Pydantic models -> OpenAPI)."""
from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator


class Health(BaseModel):
    status: Literal["ok"]
    version: str
    benchmark_hours: int


class Metrics(BaseModel):
    grid_energy_MWh: float
    peak_import_MW: float
    operational_CO2_t: float
    renewable_utilization_pct: float
    curtailed_MWh: float
    electrolyser_MWh: float
    fuel_cell_MWh: float
    average_workload_delay_h: float
    max_workload_delay_h: int
    jobs_shifted_pct: float
    violation_energy_MWh: float
    h2_terminal_MWh: float


class HourlySeries(BaseModel):
    grid_import_MW: list[float]
    electrolyser_MW: list[float]
    fuel_cell_MW: list[float]
    curtailed_MW: list[float]
    h2_inventory_MWh: list[float]
    flexible_load_MW: list[float]
    connection_cap_MW: list[float | None]


class ScenarioSummary(BaseModel):
    key: str
    label: str
    description: str
    published: dict[str, float] = Field(description="Row of data/research_results_gridflex.csv, verbatim")


class ScenarioDetail(ScenarioSummary):
    connection_capacity_MW: float
    metrics: Metrics
    bundle_delays_h: list[int]
    series: HourlySeries


class WhatIfMode(str, Enum):
    min_uniform_flexible = "min-uniform-flexible"   # like R3: smallest firm connection, jobs may move
    min_uniform = "min-uniform"                     # like R2: smallest firm connection, jobs pinned
    nonfirm = "nonfirm"                             # like R4: imposed non-firm envelope
    phased = "phased"                               # like R5: imposed phased envelope


class WhatIfRequest(BaseModel):
    """Exploratory run. Defaults equal the paper's benchmark configuration."""
    mode: WhatIfMode = WhatIfMode.min_uniform_flexible
    electrolyser_mw: float = Field(4.0, ge=0, le=20)
    fuel_cell_mw: float = Field(2.0, ge=0, le=10)
    h2_max_mwh: float = Field(20.0, ge=0, le=200)
    h2_init_mwh: float = Field(5.0, ge=0, le=200)
    eta_el: float = Field(0.72, ge=0.3, le=0.95)
    eta_fc: float = Field(0.55, ge=0.2, le=0.8)
    demand_scale: float = Field(1.0, ge=0.5, le=1.5, description="scales latency-sensitive and delay-tolerant AI demand")
    solar_scale: float = Field(1.0, ge=0.0, le=3.0)
    wind_scale: float = Field(1.0, ge=0.0, le=3.0)
    workload_flexibility: bool = Field(True, description="envelope modes only: allow bundles to move to later slots")
    candidate_offsets_h: list[int] = Field([0, 3, 7], description="slots each bundle may use, hours after its baseline; must start with 0")
    phased_levels_mw: list[float] = Field([8.7, 9.7, 10.7], min_length=3, max_length=3)
    nonfirm_normal_mw: float = Field(10.7, ge=1, le=20)
    nonfirm_reduced_mw: float = Field(6.5, ge=0, le=20)
    nonfirm_start_hour: int = Field(8, ge=0, le=23)
    nonfirm_end_hour: int = Field(14, ge=0, le=23)

    @model_validator(mode="after")
    def _consistent(self):
        if self.h2_init_mwh > self.h2_max_mwh:
            raise ValueError("h2_init_mwh must not exceed h2_max_mwh")
        if self.nonfirm_end_hour < self.nonfirm_start_hour:
            raise ValueError("nonfirm_end_hour must be >= nonfirm_start_hour")
        if self.nonfirm_reduced_mw > self.nonfirm_normal_mw:
            raise ValueError("nonfirm_reduced_mw must not exceed nonfirm_normal_mw")
        o = self.candidate_offsets_h
        if not (2 <= len(o) <= 5 and o[0] == 0 and all(b > a for a, b in zip(o, o[1:], strict=False)) and o[-1] <= 12):
            raise ValueError("candidate_offsets_h must start with 0, be strictly increasing, have 2-5 entries and end <= 12")
        if any(not 0 < v <= 20 for v in self.phased_levels_mw):
            raise ValueError("phased_levels_mw must be in (0, 20] MW")
        return self


class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


class WhatIfResult(BaseModel):
    exploratory: Literal[True] = True
    disclaimer: str
    feasible: bool
    connection_capacity_MW: float | None
    reduction_vs_grid_only_pct: float | None
    metrics: Metrics | None
    bundle_delays_h: list[int] | None
    series: HourlySeries | None


class Job(BaseModel):
    id: str
    status: JobStatus
    progress: float = Field(ge=0, le=1)
    request: WhatIfRequest
    created_utc: str
    finished_utc: str | None = None
    runtime_s: float | None = None
    result: WhatIfResult | None = None
    error: str | None = None


class QuboProblem(BaseModel):
    qubits: int
    basis_states: int
    bundles: int
    slots: int
    baseline_hours: list[int]
    candidate_hours: list[list[int]]
    feasible_states: list[int]
    best_state: int
    best_energy: float
    best_assignment_hours: list[int]
    energies: list[float]
    published_angles: dict[str, list[float]]


class QaoaEvaluateRequest(BaseModel):
    p: int = Field(1, ge=1, le=4)
    angles: list[Annotated[float, Field(allow_inf_nan=False, ge=-1000, le=1000)]] = Field(
        description="[gamma_1..gamma_p, beta_1..beta_p]")
    include_probabilities: bool = False

    @model_validator(mode="after")
    def _len(self):
        if len(self.angles) != 2 * self.p:
            raise ValueError("angles must contain 2p values")
        return self


class QaoaStatistics(BaseModel):
    p: int
    angles: list[float]
    expected_cost: float
    feasible_mass_pct: float
    optimum_probability_pct: float
    most_probable_feasible_state: int
    most_probable_is_optimum: bool
    optimality_gap: float
    most_probable_assignment_hours: list[int]
    probabilities: list[float] | None = None


class QaoaOptimiseRequest(BaseModel):
    p: int = Field(1, ge=1, le=3)
    restarts: int = Field(5, ge=1, le=20)
    seed: int = Field(7, ge=0)
    max_evals: int = Field(600, ge=50, le=1000)

    @model_validator(mode="after")
    def _budget(self):
        if self.restarts * self.max_evals > 3000:
            raise ValueError("restarts x max_evals must not exceed 3000 (synchronous endpoint)")
        return self


class PublicDataset(BaseModel):
    name: str
    signal: str
    url: str
    doi: str | None
    licence: str
    commercial_use: str
    access: str
    used_in_published_results: bool
    status: str
    verified_utc: str


class AssistantStatus(BaseModel):
    enabled: bool
    provider: str
    message: str


class AssistantQuestion(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
