# Unit 0 — ADR + Narrative Semantics Freeze

**Objective:** Lock narrative meaning before implementation.
**Depends on:** none

## Implementation TODO

- [ ] Author ADR for narrative semantics and prioritization.
- [ ] Define `overall_status` derivation rules (`healthy | watch | action_needed`).
- [ ] Define ranking precedence (severity, escalation, tie-breakers).
- [ ] Define confidence bands + approved wording by band.
- [ ] Define uncertainty policy for incomplete/conflicting evidence.
- [ ] Define one-sentence headline constraints.
- [ ] Publish canonical examples (healthy/watch/action_needed).
- [ ] Obtain backend + frontend + product sign-off.

## Evidence required

- [ ] ADR link
- [ ] Approved style guide excerpt
- [ ] Example payload samples

## Verification checklist

- [ ] Same incident snapshot produces same semantic classification.
- [ ] Reviewers confirm wording consistency with confidence policy.
