from datetime import datetime, timezone

from homelab.incidents.memory import build_incident_signature, find_recurrence_matches


def test_signature_is_deterministic_for_input_order() -> None:
    first = build_incident_signature(
        incident_id="inc-1",
        site_id="site-a",
        symptoms=["OOMKill", "High CPU"],
        affected_resources=["svc/web", "host/node-1"],
        top_cause_keys=["memory_pressure", "hot_loop"],
        severity_bucket="high",
        detected_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
    )

    second = build_incident_signature(
        incident_id="inc-1",
        site_id="site-a",
        symptoms=["high cpu", "oomkill"],
        affected_resources=["host/node-1", "svc/web"],
        top_cause_keys=["hot_loop", "memory_pressure"],
        severity_bucket="high",
        detected_at=datetime(2026, 2, 1),
    )

    assert first.symptom_hash == second.symptom_hash
    assert first.scope_hash == second.scope_hash
    assert first.top_cause_keys == second.top_cause_keys
    assert first.detected_at.tzinfo is not None


def test_recurrence_scoring_and_classification() -> None:
    current = build_incident_signature(
        incident_id="inc-current",
        site_id="site-a",
        symptoms=["OOMKill", "High CPU"],
        affected_resources=["svc/web", "host/node-1"],
        top_cause_keys=["memory_pressure", "hot_loop"],
        severity_bucket="critical",
        detected_at=datetime(2026, 2, 2, tzinfo=timezone.utc),
    )
    prior = build_incident_signature(
        incident_id="inc-prior",
        site_id="site-a",
        symptoms=["High CPU", "OOMKill"],
        affected_resources=["svc/web", "host/node-1"],
        top_cause_keys=["memory_pressure", "leak"],
        severity_bucket="high",
        detected_at=datetime(2026, 1, 28, tzinfo=timezone.utc),
    )
    dissimilar = build_incident_signature(
        incident_id="inc-other",
        site_id="site-b",
        symptoms=["Timeout"],
        affected_resources=["svc/db"],
        top_cause_keys=["dependency_outage"],
        severity_bucket="medium",
        detected_at=datetime(2026, 1, 15, tzinfo=timezone.utc),
    )

    matches = find_recurrence_matches(current=current, historical=[dissimilar, prior], top_n=2)

    assert len(matches) == 1
    assert matches[0].matched_incident_id == "inc-prior"
    assert matches[0].classification == "worsening"
    assert matches[0].match_score >= 0.6
    assert "symptom_hash_exact" in matches[0].match_reasons
    assert matches[0].memory_model_version == "primitive-b-v1"
