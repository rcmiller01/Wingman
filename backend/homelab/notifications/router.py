"""Notification Router - Dispatches alerts to webhooks."""

from homelab.notifications.webhook import notifier
from homelab.storage.models import Incident


class NotificationRouter:
    """Dispatches notifications to configured channels."""

    async def notify_incident(self, incident: Incident):
        """Send incident alert to webhook."""
        await notifier.notify(
            "incident_detected",
            {
                "incident_id": str(incident.id),
                "severity": incident.severity.value,
                "status": incident.status.value,
                "summary": ", ".join(incident.symptoms[:1]) if incident.symptoms else "",
                "affected_resources": incident.affected_resources,
                "detected_at": incident.detected_at.isoformat(),
            },
        )


# Singleton
notification_router = NotificationRouter()
