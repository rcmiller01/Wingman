# Primitive C — Unit-by-Unit TODO Backlog

> Execution pack: see `docs/primitive-c/README.md` and `docs/primitive-c/units/` for per-unit implementation files.

This TODO translates the Primitive C implementation plan into execution-ready checklists for each unit.

## Usage Notes

- Treat each checkbox as a concrete deliverable.
- Keep evidence links for every completed item (PR, test, dashboard, runbook update).
- Do not start a downstream unit until upstream dependencies are complete.

---

## Unit 0 — ADR + Narrative Semantics Freeze

**Objective:** Lock narrative meaning before implementation.

**Dependencies:** none

### TODO

- [ ] Write ADR covering:
  - [ ] `overall_status` semantics (`healthy | watch | action_needed`)
  - [ ] Severity/escalation precedence and tie-break rules
  - [ ] Incident/action/approval source-of-truth boundaries
  - [ ] Determinism guarantees and non-goals
- [ ] Define approved confidence bands and wording:
  - [ ] Band thresholds (numeric ranges)
  - [ ] User-facing phrase per band
  - [ ] Required uncertainty language for incomplete evidence
- [ ] Define one-sentence headline policy:
  - [ ] Must reference top-priority issue when non-healthy
  - [ ] Must avoid speculative root-cause language without confidence guardrails
- [ ] Publish style-baseline examples for:
  - [ ] healthy
  - [ ] watch
  - [ ] action_needed
- [ ] Hold cross-functional review (backend/frontend/product)
- [ ] Record approvals and unresolved follow-ups

### Completion checks

- [ ] ADR approved and merged
- [ ] Example narratives accepted as baseline
- [ ] Semantic glossary linked from implementation tickets

---

## Unit 1 — Narrative Aggregation Foundation

**Objective:** Build deterministic aggregation inputs.

**Dependencies:** Unit 0

### TODO

- [ ] Implement aggregation query layer over canonical data:
  - [ ] Incidents (active + recent)
  - [ ] Execution outcomes (autonomous actions)
  - [ ] Pending approvals
- [ ] Normalize source records into deterministic intermediate model
- [ ] Implement active-issue ranking model:
  - [ ] Severity-first ordering
  - [ ] Escalation-aware weighting
  - [ ] Stable tie-breakers
- [ ] Add freshness metadata:
  - [ ] `as_of`
  - [ ] per-source freshness timestamps
  - [ ] freshness status enum for downstream use
- [ ] Add cache strategy:
  - [ ] cache key strategy
  - [ ] invalidation triggers
  - [ ] TTL policy
- [ ] Build snapshot fixtures for reproducibility

### Completion checks

- [ ] Same fixture input always yields same aggregated output
- [ ] Cache/freshness behavior documented
- [ ] Ranking behavior covered by deterministic tests

---

## Unit 2 — Narrative Composer Service

**Objective:** Generate the canonical narrative object.

**Dependencies:** Unit 1

### TODO

- [ ] Implement composer that outputs contract v1 fields:
  - [ ] `as_of`
  - [ ] `overall_status`
  - [ ] `headline`
  - [ ] `active_issues[]`
  - [ ] `autonomous_actions_taken[]`
  - [ ] `pending_approvals[]`
  - [ ] `change_since_yesterday`
  - [ ] `confidence_notes[]`
  - [ ] `evidence_refs[]`
- [ ] Implement deterministic headline template engine
- [ ] Enforce confidence wording mapping from Unit 0
- [ ] Attach evidence references for every claim block
- [ ] Add composition-level validation:
  - [ ] required fields present
  - [ ] no orphan claims without evidence
  - [ ] confidence phrasing allowed-list only

### Completion checks

- [ ] Stable output for identical inputs
- [ ] `overall_status` and headline consistency validated
- [ ] Every surfaced issue/action links to evidence

---

## Unit 3 — API Endpoint + Versioning

**Objective:** Expose narrative as a first-class API.

**Dependencies:** Unit 2

### TODO

- [ ] Add endpoint (e.g., `GET /status/narrative`)
- [ ] Add explicit `schema_version` field in response
- [ ] Define additive-evolution policy for future versions
- [ ] Add auth controls for status payload access
- [ ] Add audit logging for narrative reads
- [ ] Add endpoint-level performance budget checks:
  - [ ] p50/p95 latency
  - [ ] error-rate budget

### Completion checks

- [ ] Contract tests lock schema + status derivation behavior
- [ ] Versioning policy documented
- [ ] Endpoint meets latency/error expectations

---

## Unit 4 — Dashboard Integration

**Objective:** Make narrative the UX anchor.

**Dependencies:** Unit 3

### TODO

- [ ] Add a single System Status narrative panel
- [ ] Render top-level fields from canonical payload only
- [ ] Render sections for:
  - [ ] active issues
  - [ ] autonomous actions taken
  - [ ] pending approvals
  - [ ] confidence notes / uncertainty
- [ ] Remove or disable conflicting summary logic in dashboard
- [ ] Add empty/degraded/stale visual states using payload metadata
- [ ] Add UI tests with fixture payloads

### Completion checks

- [ ] Dashboard top summary fully narrative-driven
- [ ] No duplicated business logic outside narrative service
- [ ] UI behavior validated for healthy/watch/action_needed

---

## Unit 5 — Chat Integration

**Objective:** Keep conversational responses consistent with dashboard/API.

**Dependencies:** Unit 3

### TODO

- [ ] Route status-intent prompts through narrative service
- [ ] Reuse headline + issue + confidence blocks directly from payload
- [ ] Add explicit stale/degraded fallback message templates
- [ ] Prevent chat-side reinterpretation of status semantics
- [ ] Add deterministic snapshot-based chat tests

### Completion checks

- [ ] Chat answers match API/dashboard for same timestamp
- [ ] Fallback response is explicit, safe, and non-speculative
- [ ] No channel-specific business logic drift

---

## Unit 6 — Degraded Mode & Reliability Hardening

**Objective:** Maintain trustworthy status under partial failures.

**Dependencies:** Units 1–3

### TODO

- [ ] Implement degraded composition path when one or more sources fail
- [ ] Add staleness detection + labeling rules
- [ ] Enforce uncertainty language in degraded states
- [ ] Add SLOs and telemetry for:
  - [ ] narrative freshness
  - [ ] generation failures
  - [ ] degraded-mode frequency
- [ ] Add alerting for freshness SLO violations
- [ ] Add reliability test scenarios for partial failures

### Completion checks

- [ ] Degraded narratives remain coherent and auditable
- [ ] SLO alerts fire under simulated violations
- [ ] Reliability tests cover source outage and stale data cases

---

## Unit 7 — Runbooks, Style Guide, and Governance

**Objective:** Make narrative quality sustainable.

**Dependencies:** Units 0–6

### TODO

- [ ] Publish narrative style guide:
  - [ ] confidence wording bands
  - [ ] uncertainty language patterns
  - [ ] forbidden phrasing examples
- [ ] Publish debugging runbook:
  - [ ] how to trace a narrative claim to evidence
  - [ ] how to diagnose incorrect `overall_status`
  - [ ] how to handle degraded/stale incidents
- [ ] Define ownership and review cadence for semantic changes
- [ ] Add governance checklist required for semantic-rule updates

### Completion checks

- [ ] On-call can trace each claim end-to-end
- [ ] Governance process documented and discoverable
- [ ] Semantic rule changes require checklist sign-off

---

## Cross-Unit Validation Checklist

- [ ] Status logic implemented once and reused everywhere
- [ ] Confidence phrases standardized and contradiction-free
- [ ] Degraded mode explicit and test-covered
- [ ] Every headline claim traceable to evidence
- [ ] Any channel can answer “what’s wrong right now?” from the same payload

## Suggested Milestones

- [ ] **M1 (Week 1):** Units 0 + 1
- [ ] **M2 (Week 2):** Units 2 + 3
- [ ] **M3 (Week 3):** Units 4 + 5
- [ ] **M4 (Week 4):** Units 6 + 7
