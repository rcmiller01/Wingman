# ADR 0002: Primitive B Baseline Memory v1 Contract

- Status: Accepted
- Date: 2026-02-06
- Owners: Backend + Ops

## Context

Primitive B requires Wingman to answer: "is this unusual?", "have we seen this before?", and "what worked last time?" with deterministic, auditable outputs.

## Decision

We standardize on the v1 memory contract and deterministic recurrence scoring:

1. **Canonical dimensions**: `site_id`, `entity_ref`, `metric_key`, UTC timestamps.
2. **Signature semantics**: symptom hash + scope hash + top cause keys + severity bucket.
3. **Scoring weights**:
   - symptom hash exact: `0.55`
   - scope hash exact: `0.25`
   - cause overlap: up to `0.15`
   - same site bonus: `0.05`
4. **Classification gates**:
   - score `< 0.6` => `new`
   - score `>= 0.6` and severity increased => `worsening`
   - score `>= 0.6` and severity decreased => `improving`
   - score `>= 0.6` and same severity => `recurring`
5. **Versioning**: emit `memory_model_version=primitive-b-v1` with all match outputs.

## Non-goals

- No ML anomaly model in v1.
- No dynamic threshold tuning in code; thresholds are review-gated and runbook-managed.

## Consequences

- API/UI can consume one canonical recurrence payload and reason codes.
- Future units can extend storage + drift logic without redefining score semantics.
