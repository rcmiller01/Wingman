# Unit 3 — API Endpoint + Versioning

**Objective:** Expose narrative as a first-class API contract.
**Depends on:** Unit 2

## Implementation TODO

- [ ] Add `/status/narrative` endpoint.
- [ ] Include `schema_version` in payload.
- [ ] Define backward-compatible additive field policy.
- [ ] Add auth checks and read audit trail.
- [ ] Validate latency and error budgets.

## Evidence required

- [ ] OpenAPI/schema docs
- [ ] Contract test suite
- [ ] Latency/error benchmark outputs

## Verification checklist

- [ ] Contract tests pin schema and status derivation behavior.
- [ ] Endpoint meets agreed performance targets.
