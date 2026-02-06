# Runbook: Primitive B Memory Threshold Tuning (v1)

## Objective

Tune recurrence confidence thresholds while preserving determinism and explainability.

## Baseline thresholds

- Recurrence gate: `score >= 0.60`
- Weights:
  - symptom hash exact: `0.55`
  - scope hash exact: `0.25`
  - cause overlap: `0.00..0.15`
  - same site: `0.05`

## Weekly calibration ritual

1. Sample incidents labeled `new` and `recurring` from the previous week.
2. Verify machine reasons include expected anchors (symptom/scope/cause/site).
3. Record false positives and false negatives.
4. Propose threshold/weight changes only via ADR update and backend+ops approval.

## Guardrails

- Do not change thresholds directly in API/UI layers.
- Keep score function deterministic and versioned.
- If score semantics change, increment `memory_model_version` and provide migration notes.

## Rollback

1. Revert to prior ADR-approved weights.
2. Redeploy matcher service.
3. Validate with fixture set:
   - noisy-but-normal spike
   - sustained drift
   - repeat outage

## KPI suggestions

- Recurrence precision@1
- Drift false-positive rate
- % incidents with machine-readable recurrence reasons
