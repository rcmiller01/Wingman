"""Deterministic baseline-memory primitives for incident recurrence analysis.

This module intentionally starts simple: it provides signature normalization,
weighted recurrence scoring, and explainable reason codes that can be reused by
API/control-plane layers without duplicating logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from typing import Literal, Sequence


RecurrenceClassification = Literal["new", "recurring", "worsening", "improving"]


@dataclass(frozen=True)
class IncidentSignature:
    """Canonicalized incident fingerprint used for recurrence matching."""

    incident_id: str
    site_id: str
    symptom_hash: str
    scope_hash: str
    top_cause_keys: tuple[str, ...]
    severity_bucket: Literal["low", "medium", "high", "critical"]
    detected_at: datetime


@dataclass(frozen=True)
class RecurrenceMatchResult:
    """Deterministic recurrence scoring output with machine-readable reasons."""

    incident_id: str
    matched_incident_id: str
    match_score: float
    match_reasons: tuple[str, ...]
    classification: RecurrenceClassification
    memory_model_version: str = "primitive-b-v1"


SEVERITY_SCORE = {"low": 1, "medium": 2, "high": 3, "critical": 4}
SEVERITY_ORDER = ["low", "medium", "high", "critical"]


def build_incident_signature(
    *,
    incident_id: str,
    site_id: str,
    symptoms: Sequence[str],
    affected_resources: Sequence[str],
    top_cause_keys: Sequence[str],
    severity_bucket: Literal["low", "medium", "high", "critical"],
    detected_at: datetime,
) -> IncidentSignature:
    """Build a canonical incident signature from normalized incident fields."""
    if detected_at.tzinfo is None:
        detected_at = detected_at.replace(tzinfo=timezone.utc)

    normalized_symptoms = sorted(s.strip().lower() for s in symptoms if s and s.strip())
    normalized_scope = sorted(r.strip().lower() for r in affected_resources if r and r.strip())
    normalized_causes = tuple(sorted(c.strip().lower() for c in top_cause_keys if c and c.strip()))

    symptom_hash = sha256("|".join(normalized_symptoms).encode("utf-8")).hexdigest()
    scope_hash = sha256("|".join(normalized_scope).encode("utf-8")).hexdigest()

    return IncidentSignature(
        incident_id=incident_id,
        site_id=site_id,
        symptom_hash=symptom_hash,
        scope_hash=scope_hash,
        top_cause_keys=normalized_causes,
        severity_bucket=severity_bucket,
        detected_at=detected_at.astimezone(timezone.utc),
    )


def find_recurrence_matches(
    *,
    current: IncidentSignature,
    historical: Sequence[IncidentSignature],
    top_n: int = 3,
) -> list[RecurrenceMatchResult]:
    """Return top-N recurrence matches using deterministic weighted scoring."""
    scored: list[RecurrenceMatchResult] = []

    for candidate in historical:
        score, reasons = _score_pair(current, candidate)
        if score <= 0:
            continue

        scored.append(
            RecurrenceMatchResult(
                incident_id=current.incident_id,
                matched_incident_id=candidate.incident_id,
                match_score=score,
                match_reasons=tuple(reasons),
                classification=_classify(current.severity_bucket, candidate.severity_bucket, score),
            )
        )

    scored.sort(key=lambda item: (-item.match_score, item.matched_incident_id))
    return scored[:top_n]


def _score_pair(current: IncidentSignature, candidate: IncidentSignature) -> tuple[float, list[str]]:
    """Compute weighted score and reasons between two signatures."""
    score = 0.0
    reasons: list[str] = []

    if current.symptom_hash == candidate.symptom_hash:
        score += 0.55
        reasons.append("symptom_hash_exact")

    if current.scope_hash == candidate.scope_hash:
        score += 0.25
        reasons.append("scope_hash_exact")

    shared_causes = sorted(set(current.top_cause_keys) & set(candidate.top_cause_keys))
    if shared_causes:
        overlap_ratio = len(shared_causes) / max(1, len(set(current.top_cause_keys) | set(candidate.top_cause_keys)))
        score += min(0.15, overlap_ratio * 0.15)
        reasons.append(f"cause_overlap:{','.join(shared_causes)}")

    if current.site_id == candidate.site_id:
        score += 0.05
        reasons.append("site_match")

    return round(min(score, 1.0), 4), reasons


def _classify(
    current_severity: Literal["low", "medium", "high", "critical"],
    previous_severity: Literal["low", "medium", "high", "critical"],
    score: float,
) -> RecurrenceClassification:
    """Classify recurrence trend using score + severity comparison."""
    if score < 0.6:
        return "new"

    current_rank = SEVERITY_SCORE[current_severity]
    previous_rank = SEVERITY_SCORE[previous_severity]

    if current_rank > previous_rank:
        return "worsening"
    if current_rank < previous_rank:
        return "improving"
    return "recurring"
