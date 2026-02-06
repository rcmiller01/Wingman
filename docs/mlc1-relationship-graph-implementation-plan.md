# MLC-1 Follow-on Task Plan: Relationship Graph for Unified Awareness

## Purpose

Implement explicit dependency modeling so Wingman reasons about systems, not isolated components:

`host -> vm -> container -> service -> port/storage/gpu/network`

This plan is sequenced after Primitives A and B and designed to compound with them.

---

## Guiding Constraints

1. **Graph must be evidence-backed**
   - Every edge should be traceable to observed facts.
2. **Incremental graph fidelity**
   - Start with core entity/edge types; expand only with clear use cases.
3. **Incident attachment is first-class**
   - Incidents map to graph nodes/edges for blast-radius reasoning.
4. **Planner-safe consumption**
   - Graph context must be bounded and policy-safe for planning.
5. **Change detection over full recompute**
   - Prefer incremental graph updates for scalability.

---

## Desired Outcome (Definition of Ready + Done)

### Ready to Implement

- Core entity and edge taxonomy approved.
- Source-of-truth adapter mapping plan approved (docker/proxmox/log-derived service facts).
- Blast-radius policy expectations approved.

### Done

- Graph service stores and updates dependency topology incrementally.
- Incidents carry graph context (affected nodes + upstream/downstream impact).
- Planner receives bounded topology context for safer action proposals.
- UI can render impacted dependency paths for active incidents.
- Runbooks cover graph integrity checks and reconciliation.

---

## Canonical Graph Contract (v1)

Minimum entities:

- `GraphNode` (`node_id`, `entity_type`, `entity_ref`, `site_id`, `attrs`, `last_seen_at`)
- `GraphEdge` (`edge_id`, `from_node_id`, `to_node_id`, `edge_type`, `confidence`, `evidence_ref`, `last_seen_at`)
- `ImpactSet` (`incident_id`, `primary_nodes[]`, `blast_radius_nodes[]`, `critical_paths[]`)

### Contract Rules

- Node identity must use stable resource refs.
- Edge confidence must include evidence provenance.
- Missing/aged edges marked stale before deletion.
- Cross-site edges must be explicit and auditable.

---

## Work Breakdown (Compound Sequencing)

### Unit 0 — ADR + Taxonomy Freeze

**Objective:** Prevent graph churn from ambiguous semantics.

**Tasks**
- Write ADR for node/edge taxonomy and confidence semantics.
- Define v1 supported entity/edge types.
- Publish mapping matrix from adapters to graph facts.

**Acceptance criteria**
- ADR approved with explicit out-of-scope types.
- Taxonomy examples accepted by platform and ops owners.

---

### Unit 1 — Graph Storage & Reconciliation Foundation

**Objective:** Introduce graph persistence with safe updates.

**Tasks**
- Add graph node/edge tables and indexes.
- Implement upsert + staleness reconciliation jobs.
- Add migration tests and integrity constraints.

**Acceptance criteria**
- Graph updates are idempotent.
- Stale edge lifecycle is observable and test-covered.

---

### Unit 2 — Adapter Mapping Ingestion

**Objective:** Build dependency edges from existing fact sources.

**Tasks**
- Map docker/proxmox facts to node and edge upserts.
- Derive service-port and service-storage/gpu links where available.
- Track evidence refs for each inferred relationship.

**Acceptance criteria**
- Core topology generated from fixture datasets.
- Evidence refs available for node/edge provenance.

---

### Unit 3 — Incident-to-Graph Attachment

**Objective:** Make incidents graph-aware.

**Tasks**
- Link incident affected entities to graph nodes.
- Compute upstream/downstream impact neighborhoods.
- Store `ImpactSet` for each active incident.

**Acceptance criteria**
- Active incidents show blast-radius node sets.
- Impact computation deterministic and bounded.

---

### Unit 4 — Planner Context Integration

**Objective:** Improve action safety via topology context.

**Tasks**
- Inject impacted dependency paths into planner inputs.
- Add policy checks against high-blast-radius actions.
- Annotate proposals with dependency-aware risk summaries.

**Acceptance criteria**
- Planner output references impacted topology context.
- High-risk actions flagged with explicit blast-radius rationale.

---

### Unit 5 — API/UI Topology Surfaces

**Objective:** Make system-awareness visible and explorable.

**Tasks**
- Add graph and incident-impact API endpoints.
- UI: render impacted paths for each active incident.
- Provide focused topology views (entity-centric and incident-centric).

**Acceptance criteria**
- Incident detail page shows dependency impact path.
- API contracts stable and documented.

---

### Unit 6 — Graph Quality Monitoring

**Objective:** Keep topology trustworthy over time.

**Tasks**
- Add graph quality KPIs (coverage, stale-edge ratio, orphan node ratio).
- Add reconciliation and drift alerts.
- Add debugging runbook for missing/incorrect edges.

**Acceptance criteria**
- Quality KPIs available for ops review.
- Runbook enables repeatable repair workflow.

---

## Review Strategy (80/20 Discipline)

For each unit:

1. **Design review:** taxonomy clarity, inference validity, blast-radius impact.
2. **Implementation review:** idempotency, bounded computation, provenance quality.
3. **Outcome review:** did this reduce ambiguity in incident reasoning and planning?

### Anti-Debt Checklist

- Is graph schema the single place for relationship semantics?
- Are inferred edges traceable to evidence?
- Are high-cardinality updates bounded and observable?
- Are planner risk annotations generated from graph facts, not ad-hoc logic?

---

## Testing & Validation Matrix

- **Unit tests:** node/edge upsert logic, reconciliation rules, impact traversal
- **Contract tests:** graph API and incident-impact payloads
- **Integration tests:** fact ingestion -> graph update -> incident impact -> planner context
- **Performance tests:** incremental update behavior at realistic homelab/SMB scale
- **Golden fixtures:** nested VM/container stacks, shared storage dependencies, GPU contention paths

Success signal: adding a new entity type requires taxonomy extension + mapper + fixtures, not planner/UI rewrites.

---

## Suggested Milestones

- **M1 (Week 1):** Unit 0 + Unit 1 complete
- **M2 (Week 2):** Unit 2 complete
- **M3 (Week 3):** Unit 3 + Unit 4 complete
- **M4 (Week 4):** Unit 5 + Unit 6 complete

---

## Risks and Mitigations

- **Risk:** Incorrect inferred edges cause bad blast-radius assessments.
  - **Mitigation:** confidence scoring + evidence refs + stale-edge handling.
- **Risk:** Graph update load spikes with noisy facts.
  - **Mitigation:** incremental diffing + bounded update windows.
- **Risk:** Topology complexity overwhelms users.
  - **Mitigation:** incident-centric default view with progressive disclosure.

---

## Exit Signal for MLC-1 Relationship Graph Task

This task is complete when Wingman can explain incident impact through explicit, evidence-backed dependency paths and use that context to improve planning safety and user understanding.
