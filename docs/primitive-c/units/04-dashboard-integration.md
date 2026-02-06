# Unit 4 — Dashboard Integration

**Objective:** Make canonical narrative payload the dashboard status source.
**Depends on:** Unit 3

## Implementation TODO

- [ ] Add single System Status narrative panel.
- [ ] Render active issues/actions/pending approvals from canonical payload.
- [ ] Remove conflicting top-level summary logic from dashboard.
- [ ] Render stale/degraded visual states from payload metadata.
- [ ] Add fixture-driven UI tests for healthy/watch/action_needed.

## Evidence required

- [ ] UI component PR
- [ ] Fixture snapshots/tests
- [ ] Before/after summary logic audit

## Verification checklist

- [ ] Dashboard summary is fully narrative-driven.
- [ ] No duplicate top-level status business logic in frontend.
