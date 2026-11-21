"""The six resource scenarios of the paper (R0-R5) and parameterised what-if runs."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

import numpy as np

from .benchmark import Benchmark
from .dispatch import PlantConfig, Schedule, min_uniform_capacity, solve_dispatch


@dataclass(frozen=True)
class ScenarioSpec:
    key: str
    label: str
    description: str
    renewables: bool
    hydrogen: bool
    flexible: bool
    envelope: Literal["none", "min-uniform", "nonfirm", "phased"]


SCENARIOS: dict[str, ScenarioSpec] = {s.key: s for s in (
    ScenarioSpec("R0", "Grid-only reference", "No renewables, hydrogen or flexibility; peak import defines the baseline.",
                 False, False, False, "none"),
    ScenarioSpec("R1", "Renewable supply", "Adds on-site solar and wind behind the meter.",
                 True, False, False, "none"),
    ScenarioSpec("R2", "Green-H2 assisted", "Adds electrolyser, hydrogen tank and fuel cell; smallest feasible uniform cap.",
                 True, True, False, "min-uniform"),
    ScenarioSpec("R3", "H2 + workload flexibility", "Delay-tolerant bundles may move to +3 h or +7 h; smallest feasible uniform cap.",
                 True, True, True, "min-uniform"),
    ScenarioSpec("R4", "Non-firm envelope", "10.7 MW, contracting to 6.5 MW for hours 08-14 (7 h) daily; peak import under the envelope.",
                 True, True, True, "nonfirm"),
    ScenarioSpec("R5", "Phased envelope", "8.7 / 9.7 / 10.7 MW across three 56-hour stages; peak import under the imposed envelope.",
                 True, True, True, "phased"),
)}


@dataclass
class ScenarioResult:
    key: str
    connection_capacity_MW: float
    schedule: Schedule | None
    feasible: bool
    metrics: dict


def run_scenario(b: Benchmark, key: str, cfg: PlantConfig = PlantConfig(),
                 progress: Callable[[float], None] | None = None,
                 nonfirm_cap: np.ndarray | None = None) -> ScenarioResult:
    spec = SCENARIOS[key]
    T = b.T
    if spec.envelope == "none" and not spec.renewables:
        load = b.fixed + b.flex
        m = {"grid_energy_MWh": float(load.sum()), "peak_import_MW": float(load.max()),
             "operational_CO2_t": float((load * b.carbon).sum() / 1000), "renewable_utilization_pct": 0.0,
             "curtailed_MWh": 0.0, "electrolyser_MWh": 0.0, "fuel_cell_MWh": 0.0,
             "average_workload_delay_h": 0.0, "max_workload_delay_h": 0, "jobs_shifted_pct": 0.0,
             "violation_energy_MWh": 0.0, "h2_terminal_MWh": 0.0}
        z = np.zeros(T)
        sched = Schedule(pg=load, pe=z, pf=z, pc=z, h=z, delays=np.zeros(len(b.bundle_hours), int),
                         flex_load=b.flex.copy(), cap=np.full(T, np.inf), metrics=m)
        return ScenarioResult(key, float(load.max()), sched, True, m)

    if spec.envelope == "none":
        s = solve_dispatch(b, np.full(T, np.inf), cfg, use_h2=spec.hydrogen, flexible=spec.flexible)
        cap = float(s.pg.max()) if s else float("nan")
    elif spec.envelope == "min-uniform":
        c = min_uniform_capacity(b, cfg, use_h2=spec.hydrogen, flexible=spec.flexible, progress=progress)
        # Evaluate the operating point AT the capacity it reports (see verify/r2_check.py).
        s = solve_dispatch(b, np.full(T, c), cfg, use_h2=spec.hydrogen, flexible=spec.flexible) if c else None
        cap = float(c) if c else float("nan")
    else:
        env = (nonfirm_cap if nonfirm_cap is not None else b.cap_nonfirm) if spec.envelope == "nonfirm" else b.cap_phased
        s = solve_dispatch(b, env, cfg, use_h2=spec.hydrogen, flexible=spec.flexible)
        cap = float(s.pg.max()) if s else float("nan")
    if progress:
        progress(1.0)
    return ScenarioResult(key, cap, s, s is not None, s.metrics if s else {})


def nonfirm_envelope(b: Benchmark, normal: float, reduced: float, start: int, end: int) -> np.ndarray:
    """Non-firm envelope: ``normal`` MW, contracting to ``reduced`` MW for hours start..end inclusive."""
    window = (b.hour_of_day >= start) & (b.hour_of_day <= end)
    return np.where(window, reduced, normal).astype(float)
