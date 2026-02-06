# Primitive C Status Narrative — Enactment Pack

This folder operationalizes the Primitive C plan into implementable unit packages.

## How to use

1. Start with `units/00-adr-and-semantics-freeze.md`.
2. Complete units in dependency order.
3. For each completed checklist item, attach evidence (PR, test output, dashboard snapshot, runbook link).
4. Keep all status derivation logic centralized in backend narrative services.

## Unit index

- `units/00-adr-and-semantics-freeze.md`
- `units/01-aggregation-foundation.md`
- `units/02-narrative-composer-service.md`
- `units/03-api-endpoint-and-versioning.md`
- `units/04-dashboard-integration.md`
- `units/05-chat-integration.md`
- `units/06-degraded-mode-and-reliability.md`
- `units/07-runbooks-style-governance.md`

## Global delivery guardrails

- One canonical narrative payload across API/UI/chat.
- Deterministic status derivation from incident/execution/approval sources.
- Confidence-aware language with explicit uncertainty.
- No channel-specific reinterpretation of top-level status.
- Fast-path availability under degraded dependencies.
