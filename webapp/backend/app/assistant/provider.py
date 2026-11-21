"""Extension point for a language-model assistant (disabled by default).

Nothing in this release calls an external model.  The design keeps a future
integration safe and auditable:

* ``AssistantProvider`` is the only interface the API depends on.  A provider is
  chosen by ``QH2DC_LLM_PROVIDER``; credentials come from the environment and are
  never kept in the repository.
* ``grounding_context`` assembles the facts a provider may use: the published
  scenario table, the dataset statement and the documented limitations.  A provider
  must answer from this context and cite it, so the assistant cannot introduce
  numbers that are not in the repository.
* Exploratory what-if results must be labelled as such in any answer.

To add a provider, implement ``AssistantProvider.answer`` in a new module, register
it in ``get_provider`` and document the data it sends to the external service.
"""
from __future__ import annotations

from typing import Protocol

from ..services.simulation import published_table


class AssistantProvider(Protocol):
    name: str
    enabled: bool

    def answer(self, question: str, context: str) -> str: ...


class DisabledProvider:
    name = "none"
    enabled = False

    def answer(self, question: str, context: str) -> str:  # pragma: no cover - never called
        raise RuntimeError("assistant is disabled")


def get_provider(name: str) -> AssistantProvider:
    if name in ("", "none"):
        return DisabledProvider()
    raise ValueError(f"unknown assistant provider '{name}'; no provider is bundled in this release")


def grounding_context(data_dir: str) -> str:
    rows = published_table(data_dir)
    lines = ["Published scenario results (data/research_results_gridflex.csv):"]
    for key, r in rows.items():
        lines.append(f"- {key}: capacity {r['connection_capacity_MW']:.2f} MW, grid {r['grid_energy_MWh']:.2f} MWh, "
                     f"CO2 {r['operational_CO2_t']:.2f} t, shifted {r['jobs_shifted_pct']:.1f}%")
    lines += [
        "The benchmark is a deterministic synthetic 168-hour week, not operator data.",
        "The QAOA is an ideal 12-qubit state-vector simulation; no quantum advantage is claimed.",
        "Hourly resolution, rectangular workload blocks, constant H2 efficiencies, perfect foresight.",
    ]
    return "\n".join(lines)
