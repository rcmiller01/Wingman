# Unit 6 — Degraded Mode & Reliability Hardening

**Objective:** Keep narrative trustworthy during partial failures.
**Depends on:** Units 1–3

## Implementation TODO

- [ ] Implement degraded generation path for unavailable sources.
- [ ] Add staleness labels and explicit uncertainty language.
- [ ] Track SLOs: freshness, generation success, degraded frequency.
- [ ] Alert on freshness and generation-failure SLO breaches.
- [ ] Add reliability tests for source outages and stale inputs.

## Evidence required

- [ ] Degraded-mode logic docs/tests
- [ ] SLO definitions + metrics dashboards
- [ ] Alert policy configuration

## Verification checklist

- [ ] Degraded narratives stay coherent + auditable.
- [ ] Alerts fire under simulated SLO violations.
