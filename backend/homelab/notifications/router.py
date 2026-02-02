"""Notification Router - Dispatches alerts to alerting pipeline."""

import logging
from pathlib import Path

from homelab.notifications.alerting import AlertContext, AlertPolicyEngine, AlertingPipeline
from homelab.notifications.channels import build_default_channels
from homelab.storage.models import Incident


logger = logging.getLogger(__name__)
POLICY_FILE = Path(__file__).with_name("escalation_policy.yaml")


class NotificationRouter:
    """Dispatches notifications to configured channels."""

    def __init__(self):
        self.pipeline = AlertingPipeline(build_default_channels(), self._load_policy_engine())

    def _load_policy_engine(self) -> AlertPolicyEngine | None:
        if not POLICY_FILE.exists():
            return None
        try:
            policy_text = POLICY_FILE.read_text(encoding="utf-8")
            return AlertPolicyEngine.from_yaml(policy_text)
        except Exception as exc:
            logger.error("[Notifications] Failed to load policy file: %s", exc)
            return None

    async def notify_event(
        self,
        event_type: str,
        payload: dict,
        severity: str = "info",
        tags: list[str] | None = None,
    ) -> list[str]:
        context = AlertContext(
            title=f"{event_type.replace('_', ' ').title()}",
            message=payload.get("summary") or payload.get("reason") or "",
            payload={"event_type": event_type, **payload},
            severity=severity,
            tags=tags or [event_type],
        )
        return await self.pipeline.dispatch(context)

    async def notify_incident(self, incident: Incident):
        """Send incident alert to channels."""
        payload = {
            "incident_id": str(incident.id),
            "severity": incident.severity.value,
            "status": incident.status.value,
            "summary": ", ".join(incident.symptoms[:1]) if incident.symptoms else "",
            "affected_resources": incident.affected_resources,
            "detected_at": incident.detected_at.isoformat(),
        }
        await self.notify_event(
            "incident_detected",
            payload,
            severity=incident.severity.value,
            tags=["incident"],
        )


# Singleton
notification_router = NotificationRouter()
