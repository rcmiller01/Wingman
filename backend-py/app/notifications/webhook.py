"""Webhook notification service."""

import hmac
import hashlib
import json
import time
import httpx
from datetime import datetime
from typing import Any, Dict, Optional

from app.config import get_settings

settings = get_settings()

class WebhookNotifier:
    """Service for sending notifications via webhooks."""
    
    def __init__(self):
        self.webhook_url = settings.webhook_url
        self.webhook_secret = settings.webhook_secret
        
    async def notify(self, event_type: str, data: Dict[str, Any]) -> bool:
        """Send a notification to the configured webhook."""
        if not self.webhook_url:
            return False
            
        payload = {
            "version": "1.0",
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data
        }
        
        headers = {
            "Content-Type": "application/json",
            "X-Copilot-Event": event_type,
        }
        
        # Add signature if secret is configured
        if self.webhook_secret:
            timestamp = str(int(time.time()))
            payload_str = json.dumps(payload, sort_keys=True)
            signature_base = f"{timestamp}.{payload_str}"
            
            signature = hmac.new(
                self.webhook_secret.encode(),
                signature_base.encode(),
                hashlib.sha256
            ).hexdigest()
            
            headers["X-Copilot-Signature"] = f"t={timestamp},v1={signature}"
            
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.webhook_url,
                    json=payload,
                    headers=headers,
                    timeout=10.0
                )
                response.raise_for_status()
                return True
        except Exception as e:
            print(f"[Copilot] Failed to send webhook notification: {e}")
            return False

# Global instance
notifier = WebhookNotifier()
