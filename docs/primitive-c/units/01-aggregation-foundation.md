# Unit 1 — Narrative Aggregation Foundation

**Objective:** Build deterministic aggregation inputs.
**Depends on:** Unit 0

## Implementation TODO

- [ ] Implement deterministic aggregation layer for incidents/executions/approvals.
- [ ] Normalize heterogeneous records into canonical intermediate structures.
- [ ] Implement active-issue ranking with deterministic tie-breakers.
- [ ] Add freshness metadata (`as_of`, per-source freshness, staleness class).
- [ ] Add cache key strategy, TTL, and invalidation rules.
- [ ] Add fixture snapshots for reproducibility.

## Evidence required

- [ ] Aggregation schema/spec
- [ ] Snapshot fixtures
- [ ] Determinism test output

## Verification checklist

- [ ] Fixtures replay to byte-stable aggregated outputs.
- [ ] Cache/freshness behavior documented and validated.
