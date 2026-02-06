"""Incident detection and correlation package."""

from homelab.incidents.memory import (
    IncidentSignature,
    RecurrenceMatchResult,
    build_incident_signature,
    find_recurrence_matches,
)

__all__ = [
    "Incident",
    "IncidentSeverity",
    "correlate_incidents",
    "create_incident",
    "get_correlated_incidents",
    "resolve_incident",
    "IncidentSignature",
    "RecurrenceMatchResult",
    "build_incident_signature",
    "find_recurrence_matches",
]


def __getattr__(name: str):
    if name in {
        "Incident",
        "IncidentSeverity",
        "correlate_incidents",
        "create_incident",
        "get_correlated_incidents",
        "resolve_incident",
    }:
        from homelab.incidents import correlator

        return getattr(correlator, name)
    raise AttributeError(name)
