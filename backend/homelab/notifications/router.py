"""Notification Router - Dispatches alerts to webhooks."""

import httpx
from datetime import datetime
from homelab.config import get_settings
from homelab.storage.models import Incident, IncidentSeverity

settings = get_settings()

class NotificationRouter:
    """Dispatches notifications to configured channels."""
    
    def __init__(self):
        self.webhook_url = settings.webhook_url  # e.g. Discord/Slack webhook
        
    async def notify_incident(self, incident: Incident):
        """Send incident alert to webhook."""
        if not self.webhook_url:
            print("[NotificationRouter] No webhook URL configured, skipping notification.")
            return

        payload = {
            "content": f"🚨 **New Incident Detected** - {incident.severity.value.upper()}",
            "embeds": [
                {
                    "title": f"Incident {incident.id[:8]}",
                    "description": "\n".join(incident.symptoms),
                    "color": 15548997 if incident.severity == IncidentSeverity.critical else 15158332, # Red/Orange
                    "fields": [
                        {"name": "Severity", "value": incident.severity.value, "inline": True},
                        {"name": "Status", "value": incident.status.value, "inline": True},
                        {"name": "Resources", "value": ", ".join(incident.affected_resources), "inline": False},
                        {"name": "Detected At", "value": incident.detected_at.isoformat(), "inline": False}
                    ],
                    "footer": {"text": "Homelab Copilot"}
                }
            ]
        }
        
        try:
            async with httpx.AsyncClient() as client:
                await client.post(self.webhook_url, json=payload)
                print(f"[NotificationRouter] Sent alert for incident {incident.id}")
        except Exception as e:
            print(f"[NotificationRouter] Failed to send webhook: {e}")

# Singleton
notification_router = NotificationRouter()
