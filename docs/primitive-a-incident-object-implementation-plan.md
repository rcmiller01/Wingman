# Primitive A Implementation Plan: Incident as a First-Class Object

## Purpose

Define and implement a canonical `Incident` domain model that becomes the shared language across:

- detection/correlation
- control-plane planning and validation
- APIs and UI payloads
- audit/memory and recurrence matching

This plan uses **compound engineering**: each unit of work should reduce future effort, not increase it.

---

## Guiding Constraints

1. **Schema-first, flow-second, UI-third**
   - Canonical schema lands before pipeline changes.
2. **One source of truth**
   - Incident data contracts must be generated/derived from one backend model.
3. **Backward compatibility during migration**
   - New + old payload readers coexist until cutover is complete.
4. **Observability by default**
   - Every new incident lifecycle transition emits auditable events.
5. **Review gates are mandatory**
   - No implementation unit starts without acceptance criteria and test strategy.

---

## Desired Outcome (Definition of Ready + Done)

### Ready to Implement

- Canonical `Incident` contract approved by backend + frontend owners.
- Migration/cutover plan approved with rollback path.
- Test matrix approved (unit, contract, integration, API compatibility).

### Done

- All incident-producing paths write canonical `Incident`.
- All incident-consuming paths read canonical `Incident`.
- Incident APIs expose confidence-ranked causes + affected entities consistently.
- Audit trail captures incident state transitions and action linkage.
- Documentation/playbooks updated for future contributors.

---

## Canonical Incident Contract (v1)

Minimum fields (aligning with roadmap addendum):

- Identity/lifecycle: `incident_id`, `opened_at`, `closed_at`, `status`, `severity`
- Framing: `summary_sentence`, `symptoms[]`, `suspected_causes[]` (`cause`, `confidence`)
- Scope: `affected_entities[]` (host/vm/container/service/port/storage/gpu)
- Evidence: `evidence_refs[]` (fact ids, log signatures, metric windows)
- Actionability: `proposed_actions[]`, `approval_required`
- Resolution: `outcome`, `verification_results[]`, `rollback_used`
- Memory hooks: `seen_before`, `similar_incident_ids[]`

### Contract Rules

- `summary_sentence` is mandatory once status is not `new`.
- `suspected_causes` sorted by confidence descending.
- `confidence` range is `[0.0, 1.0]`.
- `affected_entities` must use stable typed references.
- All timestamps must be UTC ISO-8601.

---

## Work Breakdown (Compound Sequencing)

> Principle: earlier units create reusable scaffolding and reduce cognitive load for later units.

### Unit 0 — ADR + Contract Freeze (planning-heavy)

**Objective:** Prevent rework by locking semantics before coding.

**Tasks**
- Write ADR: canonical incident model scope, non-goals, migration strategy.
- Define JSON schema / Pydantic model for `Incident` + nested types.
- Define versioning policy (`incident_schema_version`).

**Why this unlocks future work**
- Every downstream team integrates against stable contracts.

**Acceptance criteria**
- ADR approved.
- Contract examples for 3 realistic incidents published.

---

### Unit 1 — Storage Foundation + Migration Safety

**Objective:** Add persistence shape and migration path without behavior changes.

**Tasks**
- Add/extend DB tables/columns for canonical incident fields.
- Add migration with reversible rollback.
- Add adapter layer for old records (`legacy -> canonical` mapping).

**Why this unlocks future work**
- Pipeline changes can land incrementally without data loss.

**Acceptance criteria**
- Migration up/down tested.
- Legacy incidents can be read through canonical adapter.

---

### Unit 2 — Domain Model + Validation Library

**Objective:** Centralize all incident validation in one module.

**Tasks**
- Introduce shared `Incident` domain model and validators.
- Add deterministic normalization helpers:
  - confidence clamping
  - cause ranking
  - entity reference normalization
- Add property-based tests for invariants where applicable.

**Why this unlocks future work**
- Detector/API/UI can reuse one validator instead of duplicating rules.

**Acceptance criteria**
- Invalid incidents fail fast with actionable errors.
- Invariant tests cover ordering, type safety, and required fields.

---

### Unit 3 — Ingestion/Correlation Refactor

**Objective:** Ensure newly detected situations emit canonical incidents.

**Tasks**
- Update incident detector/correlator outputs to canonical model.
- Add explicit `summary_sentence` construction (`problem`, `cause`, `impact`).
- Persist `evidence_refs` and top-N `suspected_causes`.

**Why this unlocks future work**
- Planner, UI, and memory all consume richer structured incidents.

**Acceptance criteria**
- New incidents include cause confidence and affected entities.
- Correlation integration tests pass for representative failure modes.

---

### Unit 4 — API Contract Cutover (dual-read, single-write)

**Objective:** Shift external contract safely.

**Tasks**
- Add/upgrade incident API schemas to canonical format.
- Keep compatibility translator for old API consumers.
- Mark legacy response fields deprecated with timeline.

**Why this unlocks future work**
- Frontend can migrate independently, with low coordination overhead.

**Acceptance criteria**
- Contract tests enforce canonical response.
- Existing clients continue to function during migration window.

---

### Unit 5 — Control-Plane Integration

**Objective:** Make plans/actions incident-aware by default.

**Tasks**
- Ensure planner/proposal/validator consume `suspected_causes`, `confidence`, and `affected_entities`.
- Require action proposals to link to `incident_id`.
- Record verification/rollback outcomes back onto incident.

**Why this unlocks future work**
- Baseline memory and narrative primitives can rely on incident-linked outcomes.

**Acceptance criteria**
- Every execution tied to an incident context.
- Post-action verification updates incident outcome fields.

---

### Unit 6 — UI + Narrative Consistency

**Objective:** Convert incident data into stable user trust signals.

**Tasks**
- Update incident list/detail UI to display canonical fields.
- Display top cause + confidence and structured impact scope.
- Reuse `summary_sentence` consistently in UI and chat responses.

**Why this unlocks future work**
- Primitive C (canonical status narrative) can aggregate incidents directly.

**Acceptance criteria**
- Incident cards and detail views use the same summary semantics.
- No UI-only inferred fields that diverge from backend truth.

---

### Unit 7 — Audit, Runbooks, and Knowledge Capture

**Objective:** Ensure changes remain easy to extend.

**Tasks**
- Add lifecycle audit events (`opened`, `reframed`, `resolved`, `reopened`).
- Update docs/runbooks with incident lifecycle diagrams and debugging guidance.
- Add “how to add a new symptom/cause mapper” contributor guide.

**Why this unlocks future work**
- Future enhancements become procedural rather than tribal knowledge.

**Acceptance criteria**
- On-call runbook includes incident trace walkthrough.
- Contributor guide validated by a fresh developer dry-run.

---

## Review Strategy (80/20 Discipline)

For each unit:

1. **Pre-implementation review (required)**
   - Scope, edge cases, risk, rollback plan.
2. **Implementation review**
   - Correctness, readability, and reuse quality.
3. **Post-implementation review**
   - What got easier? What confusion remains?
   - Capture follow-on refactors before next unit.

### Anti-Debt Checklist

- Did we remove duplication versus adding it?
- Did we simplify contracts or create optional ambiguity?
- Are adapters temporary with explicit removal date?
- Is there exactly one place to update incident semantics?

---

## Testing & Validation Matrix

- **Unit tests:** model invariants, validators, normalization helpers
- **Contract tests:** API payload shape and deprecation guarantees
- **Integration tests:** detector -> incident -> planner -> execution -> verification chain
- **Migration tests:** up/down + legacy compatibility reader
- **Golden fixtures:** representative incidents (resource saturation, dependency failure, cascading outage)

Success signal: adding a new incident type should require adding mapping logic in one place + fixture updates, without API/UI rewrites.

---

## Suggested Milestones

- **M1 (Week 1):** Unit 0 + Unit 1 complete
- **M2 (Week 2):** Unit 2 + Unit 3 complete
- **M3 (Week 3):** Unit 4 + Unit 5 complete
- **M4 (Week 4):** Unit 6 + Unit 7 complete, legacy path deprecation notice issued

---

## Risks and Mitigations

- **Risk:** Partial migration creates dual semantics.
  - **Mitigation:** dual-read/single-write strategy + explicit deprecation date.
- **Risk:** Confidence scoring inconsistency across detectors.
  - **Mitigation:** central confidence normalization utility + invariant tests.
- **Risk:** UI introduces divergent narrative text.
  - **Mitigation:** mandate backend `summary_sentence` as source of truth.

---

## Exit Signal for Primitive A

Primitive A is complete when incident framing is no longer an emergent property of multiple modules, but a single canonical object with enforced lifecycle semantics across storage, APIs, planning, execution verification, and UX.
