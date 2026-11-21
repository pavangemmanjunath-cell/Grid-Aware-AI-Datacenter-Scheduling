# ADR-0004: Language-model assistant behind an interface, disabled by default

- Status: Accepted (2026-11-21)

## Context
A conversational assistant over the study is planned. A model can invent numbers, and calling an
external service sends data off the machine.

## Decision
Define `AssistantProvider` (`webapp/backend/app/assistant/provider.py`) and a `grounding_context` built
only from published results and documented limitations. Ship only `DisabledProvider`;
`/api/v1/assistant/ask` returns `501` until a provider is configured with `QH2DC_LLM_PROVIDER`.
Credentials must come from the environment, never from the repository.

## Consequences
No external calls in this release. A future provider must answer from the grounding context, cite it,
label exploratory numbers, and document what it sends to the external service before it is enabled.
