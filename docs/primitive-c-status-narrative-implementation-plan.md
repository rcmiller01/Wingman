# Primitive C Implementation Plan: Canonical Status Narrative

## Purpose

Deliver one authoritative status narrative that users can trust as the answer to:

- “What’s wrong right now?”
- “What did Wingman already fix?”
- “What still needs my approval?”

This plan ensures narrative generation is deterministic, auditable, and consistent across API, UI, and chat.

---

## Guiding Constraints

1. **Single narrative contract**
   - One backend-produced status object used by all interfaces.
2. **Incident-derived truth**
   - Narrative content must come from canonical incidents and execution outcomes.
3. **Confidence-aware language**
   - Claims require explicit confidence and evidence links.
4. **No channel-specific reinterpretation**
   - UI/chat format the same narrative payload; they do not invent facts.
5. **Fast-path availability**
   - Narrative endpoint remains available even under degraded dependencies.

---

## Desired Outcome (Definition of Ready + Done)

### Ready to Implement

- Narrative contract fields and severity semantics approved.
- Language style guide approved (healthy/watch/action_needed + confidence wording).
- Degraded-mode behavior approved.

### Done

- Status narrative service generates authoritative outputs on schedule and on-demand.
- API, dashboard, and chat consume the same narrative payload.
- Narrative includes active issues, autonomous actions, pending approvals, and trend delta.
- Confidence and uncertainty language is consistent and test-validated.
- Runbook documents narrative debugging and fallback behavior.

---

## Canonical Narrative Contract (v1)

Minimum fields:

- `as_of`
- `overall_status` (`healthy` | `watch` | `action_needed`)
- `headline`
- `active_issues[]` (`incident_id`, `impact`, `top_cause`, `confidence`, `next_action`)
- `autonomous_actions_taken[]` (`action`, `target`, `verification_status`, `timestamp`)
- `pending_approvals[]` (`incident_id`, `requested_action`, `risk_summary`)
- `change_since_yesterday`
- `confidence_notes[]`
- `evidence_refs[]`

### Contract Rules

- `headline` must be one sentence and reference highest-priority issue when non-healthy.
- `overall_status` derived from deterministic severity/escalation rules.
- `confidence` values must map to approved wording bands.
- All listed actions/issues must link to source records.

---

## Work Breakdown (Compound Sequencing)

### Unit 0 — ADR + Narrative Semantics Freeze

**Objective:** Lock narrative meaning before implementation.

**Tasks**
- Write ADR for status semantics and prioritization rules.
- Define confidence wording bands and uncertainty policy.
- Publish narrative examples for healthy/watch/action_needed states.

**Acceptance criteria**
- ADR approved by backend/frontend/product stakeholders.
- Example narratives accepted as style baseline.

---

### Unit 1 — Narrative Aggregation Foundation

**Objective:** Build deterministic aggregation inputs.

**Tasks**
- Implement aggregation query layer over incidents/executions/approvals.
- Define ranking model for active issues.
- Add cache strategy + freshness metadata.

**Acceptance criteria**
- Aggregation outputs reproducible from fixture snapshots.
- Freshness and cache invalidation behavior documented.

---

### Unit 2 — Narrative Composer Service

**Objective:** Generate the canonical narrative object.

**Tasks**
- Build service that composes contract fields from aggregated inputs.
- Implement deterministic headline generation templates.
- Attach confidence/evidence notes for each claim.

**Acceptance criteria**
- Composer produces stable output for same inputs.
- Headline and status remain consistent across channels.

---

### Unit 3 — API Endpoint + Versioning

**Objective:** Expose narrative as first-class API.

**Tasks**
- Add `/status/narrative` endpoint and schema version field.
- Add compatibility handling for future field expansion.
- Add auth/audit hooks for narrative access.

**Acceptance criteria**
- Contract tests lock schema and status derivation behavior.
- Endpoint latency/error budgets validated.

---

### Unit 4 — Dashboard Integration

**Objective:** Make narrative the UX anchor.

**Tasks**
- Add single “System Status” narrative panel.
- Display active issues, actions taken, and pending approvals from canonical payload.
- Prevent dashboard from showing contradictory top-level summary text.

**Acceptance criteria**
- Dashboard top summary is fully narrative-driven.
- No duplicate summary logic outside the narrative contract.

---

### Unit 5 — Chat Integration

**Objective:** Keep conversational responses consistent with dashboard/API.

**Tasks**
- Route “what’s wrong now?” style prompts through narrative service.
- Reuse headline/issue/confidence blocks in responses.
- Add fallback response for stale/degraded narrative state.

**Acceptance criteria**
- Chat status answers match dashboard/API for same timestamp.
- Fallback behavior is explicit and user-safe.

---

### Unit 6 — Degraded Mode & Reliability Hardening

**Objective:** Maintain trustworthy status under partial failures.

**Tasks**
- Implement degraded narrative generation when some data sources fail.
- Add staleness labeling and explicit uncertainty language.
- Add SLO monitoring for narrative freshness and generation failures.

**Acceptance criteria**
- Degraded responses remain coherent and auditable.
- Alerts fire when narrative freshness SLO is violated.

---

### Unit 7 — Runbooks, Style Guide, and Governance

**Objective:** Make narrative quality sustainable.

**Tasks**
- Publish narrative style guide (confidence wording + uncertainty patterns).
- Add runbook for investigating incorrect status narratives.
- Define ownership + review cadence for status semantics changes.

**Acceptance criteria**
- On-call can trace each narrative claim to evidence.
- Governance checklist required for semantic rule changes.

---

## Review Strategy (80/20 Discipline)

For each unit:

1. **Pre-implementation review:** semantics, edge cases, failure messaging.
2. **Implementation review:** deterministic derivation and contract integrity.
3. **Post-implementation review:** did user comprehension improve?

### Anti-Debt Checklist

- Is status logic implemented once (service) and reused everywhere?
- Are confidence phrases standardized and non-contradictory?
- Are degraded-mode behaviors explicit and test-covered?
- Can every headline claim be traced to evidence?

---

## Testing & Validation Matrix

- **Unit tests:** status derivation, issue ranking, headline template rules
- **Contract tests:** narrative schema + field guarantees
- **Integration tests:** incidents/executions/approvals -> narrative endpoint
- **UI tests:** narrative panel rendering with fixture payloads
- **Chat tests:** deterministic status responses for fixed snapshots
- **Reliability tests:** degraded data source scenarios + staleness handling

Success signal: any channel can answer “what’s wrong right now?” by consuming the same canonical narrative payload without channel-specific business logic.

---

## Suggested Milestones

- **M1 (Week 1):** Unit 0 + Unit 1 complete
- **M2 (Week 2):** Unit 2 + Unit 3 complete
- **M3 (Week 3):** Unit 4 + Unit 5 complete
- **M4 (Week 4):** Unit 6 + Unit 7 complete

---

## Risks and Mitigations

- **Risk:** Narrative drift across UI/chat.
  - **Mitigation:** single payload + no duplicated summary logic.
- **Risk:** Overstated certainty harms trust.
  - **Mitigation:** confidence bands + mandatory uncertainty notes.
- **Risk:** Stale status presented as current.
  - **Mitigation:** freshness metadata + degraded-mode labels + SLO alerts.

---

## Exit Signal for Primitive C

Primitive C is complete when Wingman can always provide one coherent, confidence-aware status narrative (API/UI/chat) that faithfully reflects incidents, actions taken, and pending approvals.
