# Primitive B Implementation Plan: Baseline Memory & Recurrence

## Purpose

Implement a minimal but durable memory layer so Wingman can reliably answer:

- “Is this unusual?”
- “Have we seen this before?”
- “What worked last time?”

This plan follows compound engineering: each delivery unit should simplify later units by centralizing semantics, reducing duplication, and preserving auditable context.

---

## Guiding Constraints

1. **Simple-first memory**
   - Start with rolling statistics + signatures before advanced anomaly ML.
2. **Incident-linked memory only**
   - Baselines and recurrence must reference canonical `incident_id`.
3. **Deterministic scoring**
   - Recurrence/drift decisions must be explainable and reproducible.
4. **Storage efficiency by design**
   - Keep high-cardinality data bounded (retention + aggregation windows).
5. **Review-gated thresholds**
   - Baseline thresholds cannot be “magic constants” without rationale.

---

## Desired Outcome (Definition of Ready + Done)

### Ready to Implement

- Canonical metric windows and key dimensions approved (service/site/resource).
- Signature strategy approved (symptom hash + cause candidates + scope).
- Retention policy approved for baseline snapshots and recurrence index.

### Done

- Baseline service computes rolling windows for key operational metrics.
- Incidents are tagged as `new`/`recurring`/`worsening`/`improving` with evidence.
- “Seen before” links include prior incident outcomes and action effectiveness.
- APIs expose recurrence confidence and historical comparison summary.
- Runbooks explain how to tune thresholds and validate memory quality.

---

## Canonical Memory Contract (v1)

Minimum entities:

- `BaselineWindow`
  - `entity_ref`, `metric_key`, `window`, `mean`, `p50`, `p95`, `stddev`, `sample_count`, `updated_at`
- `KnownGoodSnapshot`
  - `snapshot_id`, `entity_ref`, `captured_at`, `feature_vector_ref`, `notes`
- `IncidentSignature`
  - `signature_id`, `incident_id`, `symptom_hash`, `scope_hash`, `top_cause_keys[]`, `severity_bucket`
- `RecurrenceMatch`
  - `incident_id`, `matched_incident_id`, `match_score`, `match_reasons[]`, `classification`
- `ActionOutcomeMemory`
  - `incident_id`, `action_template`, `result`, `verification_status`, `time_to_recovery`

### Contract Rules

- All memory records must carry `site_id` and UTC timestamps.
- Recurrence classification must include machine-readable reasons.
- Any drift label requires before/after baseline evidence pointers.
- Matching logic versioned via `memory_model_version`.

---

## Work Breakdown (Compound Sequencing)

### Unit 0 — ADR + Metric/Signature Freeze

**Objective:** Avoid repeated baseline redefinitions.

**Tasks**
- Write ADR for baseline dimensions, windows, and signature semantics.
- Define v1 recurrence scoring formula and rationale.
- Publish calibration fixtures (normal spike, sustained drift, repeat outage).

**Acceptance criteria**
- ADR approved with explicit non-goals.
- Scoring examples accepted by backend + ops stakeholders.

---

### Unit 1 — Storage & Retention Foundation

**Objective:** Add persistence safely before behavior changes.

**Tasks**
- Add tables for baselines, signatures, recurrence matches, action outcomes.
- Add retention/compaction jobs for stale baseline buckets.
- Add migration rollback path and compatibility read strategy.

**Acceptance criteria**
- Migration up/down validated.
- Retention policies tested on synthetic volume.

---

### Unit 2 — Baseline Engine (Rolling Windows)

**Objective:** Produce stable normal-state references.

**Tasks**
- Build rolling-aggregation service for key metrics:
  - cpu, memory, io_wait, restart_rate, latency
- Add per-entity/per-time-window aggregators.
- Expose baseline evidence query helpers.

**Acceptance criteria**
- Baselines computed deterministically from fixture streams.
- Query API returns baseline summaries in bounded latency.

---

### Unit 3 — Signature Builder + Recurrence Matcher

**Objective:** Convert incidents into comparable historical fingerprints.

**Tasks**
- Build incident signature generation from canonical incidents.
- Implement recurrence matcher with weighted scoring.
- Emit classification labels and confidence with reason codes.

**Acceptance criteria**
- “Seen before” links reproducible from same input data.
- Matcher returns top-N prior incidents + rationale.

---

### Unit 4 — Drift & Novelty Classifier

**Objective:** Distinguish new behavior from recurring behavior.

**Tasks**
- Add drift decision layer comparing live signals to baselines.
- Apply labels: `new`, `recurring`, `worsening`, `improving`.
- Attach evidence pointers for each label decision.

**Acceptance criteria**
- Classifier outputs are explainable and test-covered.
- False-positive guardrails documented and validated.

---

### Unit 5 — Incident & Control-Plane Integration

**Objective:** Make memory influence planning quality.

**Tasks**
- Persist recurrence/drift fields on incident records.
- Feed prior successful/failed outcomes into planner context.
- Require plan proposals to cite memory evidence when available.

**Acceptance criteria**
- Incident payload includes historical comparison block.
- Planner sees prior action outcomes linked to similar incidents.

---

### Unit 6 — API/UI Surface + Trust Language

**Objective:** Expose memory with clear human framing.

**Tasks**
- Add API fields for recurrence confidence and comparison summary.
- UI: show “seen before”, “last occurrence”, “what worked last time”.
- Add confidence-language conventions for historical claims.

**Acceptance criteria**
- API contract tests verify new fields.
- UI uses backend-provided evidence and confidence text.

---

### Unit 7 — Tuning Loop + Knowledge Capture

**Objective:** Keep baseline quality improving over time.

**Tasks**
- Add threshold tuning playbook + weekly calibration ritual.
- Add quality KPIs (recurrence precision, drift false positives).
- Document onboarding path for adding a new metric key.

**Acceptance criteria**
- Runbook includes tuning and rollback steps.
- KPI dashboard/query spec available for ops review.

---

## Review Strategy (80/20 Discipline)

For each unit:

1. **Design review**: assumptions, thresholds, retention, and failure modes.
2. **Code review**: determinism, readability, and traceability of decisions.
3. **Outcome review**: did this reduce ambiguity for future work?

### Anti-Debt Checklist

- Is baseline logic centralized (not reimplemented in API/UI)?
- Are drift/recurrence labels generated once and reused everywhere?
- Are thresholds documented with evidence and owner?
- Is storage growth bounded and observable?

---

## Testing & Validation Matrix

- **Unit tests:** aggregator math, signature generation, matcher scoring
- **Property tests:** monotonicity/sanity constraints for score outputs
- **Contract tests:** incident/API recurrence payload fields
- **Integration tests:** ingest -> baseline -> match -> incident enrichment -> planner
- **Data-volume tests:** retention/compaction behavior over synthetic high-cardinality streams
- **Golden fixtures:** recurring crash loop, noisy-but-normal spikes, novel dependency outage

Success signal: new incident families can be made recurrence-aware by adding one signature mapper and fixture coverage, without rewriting planner/UI logic.

---

## Suggested Milestones

- **M1 (Week 1):** Unit 0 + Unit 1 complete
- **M2 (Week 2):** Unit 2 complete
- **M3 (Week 3):** Unit 3 + Unit 4 complete
- **M4 (Week 4):** Unit 5 + Unit 6 + Unit 7 complete

---

## Risks and Mitigations

- **Risk:** Overfitting baselines to short history.
  - **Mitigation:** minimum sample gates + cold-start labeling rules.
- **Risk:** Opaque recurrence scores reduce trust.
  - **Mitigation:** reason-coded matching output with evidence refs.
- **Risk:** Storage growth from per-entity metrics.
  - **Mitigation:** tiered retention, compaction, and cardinality budgets.

---

## Exit Signal for Primitive B

Primitive B is complete when every incident can be evaluated against historical baselines with explainable recurrence/drift labels and actionable outcome memory, making planning and communication more reliable over time.
