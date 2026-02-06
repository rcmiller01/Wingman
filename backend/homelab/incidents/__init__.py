"""Incident detection and correlation package."""

from homelab.incidents.correlator import (
    Incident,
    IncidentSeverity,
    correlate_incidents,
    create_incident,
    get_correlated_incidents,
    resolve_incident,
)

__all__ = [
    "Incident",
    "IncidentSeverity",
    "correlate_incidents",
    "create_incident",
    "get_correlated_incidents",
    "resolve_incident",
]
