# ADR 0003: Relationship Graph Taxonomy and Confidence Semantics (v1)

- **Status:** Accepted
- **Date:** 2026-02-06
- **Owners:** Wingman backend maintainers
- **Related:** `docs/mlc1-relationship-graph-implementation-plan.md`, `docs/v2-roadmap.md`

## Context

MLC-1 requires Wingman to reason across dependency chains instead of isolated resources. To avoid semantic churn, graph node and edge meaning must be centralized and evidence-backed.

## Decision

Adopt graph contract v1 with stable node identity, explicit edge provenance, and stale-first lifecycle.

### Node identity

A node is uniquely identified by (`entity_type`, `entity_ref`, `site_id`).

### v1 entity types (in-scope)

- `host`
- `vm`
- `container`
- `service`
- `port`
- `storage`
- `gpu`
- `network`

### v1 edge types (in-scope)

- `hosts`
- `runs`
- `contains`
- `depends_on`
- `listens_on`
- `mounts`
- `uses_gpu`
- `attached_to_network`

### Confidence semantics

- `0.9 - 1.0`: directly observed relationship from authoritative adapter fact.
- `0.6 - 0.89`: inferred from strong correlated facts (same polling window).
- `< 0.6`: weak relationship, retained only when explicitly configured.

Every edge must include `evidence_ref` that traces to source data (`fact:<id>`, `log:<id>`, `adapter:<source>:<cursor>`).

### Staleness lifecycle

- Edges are **marked stale** when unseen after TTL.
- Stale edges are retained for audit/debug until explicit cleanup policy removes them.
- Re-observed stale edges are rehydrated (`is_stale=false`, `stale_marked_at=null`).

### Out of scope for v1

- Application-level dependency graphs derived from traces only.
- Probabilistic edges without any concrete provenance reference.
- Automatic cross-site edge inference without explicit shared identifiers.

## Consequences

### Positive

- Planner and UI consume one canonical relationship model.
- Blast-radius logic can rely on auditable provenance.
- Adapter teams can extend graph support by mapper additions only.

### Negative

- Some legitimate relationships may remain unmodeled until taxonomy extension.
- Additional storage/index cost for stale tracking.
