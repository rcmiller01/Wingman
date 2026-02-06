# Unit 5 — Chat Integration

**Objective:** Ensure chat status answers match API and dashboard.
**Depends on:** Unit 3

## Implementation TODO

- [ ] Route status-intent prompts through narrative service.
- [ ] Reuse canonical headline/issues/confidence blocks.
- [ ] Add explicit stale/degraded fallback responses.
- [ ] Prevent chat-specific reinterpretation of status meaning.
- [ ] Add deterministic snapshot tests for status prompts.

## Evidence required

- [ ] Prompt routing changes
- [ ] Response-template mappings
- [ ] Snapshot test outputs

## Verification checklist

- [ ] Chat answers match API/dashboard at same `as_of` timestamp.
- [ ] Fallbacks are safe, explicit, and non-speculative.
