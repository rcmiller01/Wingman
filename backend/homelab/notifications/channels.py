"""Alerting channel implementations."""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from typing import Any

import httpx

from homelab.config import get_settings


logger = logging.getLogger(__name__)
settings = get_settings()


class AlertChannel:
    """Base interface for alert channels."""

    name: str = "base"

    async def send(self, title: str, message: str, payload: dict[str, Any]) -> bool:
        raise NotImplementedError


class EmailChannel(AlertChannel):
    name = "email"

    async def send(self, title: str, message: str, payload: dict[str, Any]) -> bool:
        if not (settings.smtp_host and settings.smtp_from and settings.smtp_to):
            return False

        email_message = EmailMessage()
        email_message["Subject"] = title
        email_message["From"] = settings.smtp_from
        email_message["To"] = settings.smtp_to
        email_message.set_content(message)

        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
                smtp.starttls()
                if settings.smtp_user and settings.smtp_password:
                    smtp.login(settings.smtp_user, settings.smtp_password)
                smtp.send_message(email_message)
            return True
        except Exception as exc:
            logger.error("[Alert] Email send failed: %s", exc)
            return False


class WebhookChannel(AlertChannel):
    """Generic webhook channel."""

    def __init__(self, name: str, url: str | None):
        self.name = name
        self.url = url

    async def send(self, title: str, message: str, payload: dict[str, Any]) -> bool:
        if not self.url:
            return False
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.url,
                    json={"title": title, "message": message, "payload": payload},
                )
                response.raise_for_status()
            return True
        except Exception as exc:
            logger.error("[Alert] %s webhook failed: %s", self.name, exc)
            return False


class TelegramChannel(AlertChannel):
    name = "telegram"

    async def send(self, title: str, message: str, payload: dict[str, Any]) -> bool:
        if not (settings.telegram_bot_token and settings.telegram_chat_id):
            return False
        url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    url,
                    json={
                        "chat_id": settings.telegram_chat_id,
                        "text": f"{title}\n{message}",
                    },
                )
                response.raise_for_status()
            return True
        except Exception as exc:
            logger.error("[Alert] Telegram send failed: %s", exc)
            return False


def build_default_channels() -> dict[str, AlertChannel]:
    return {
        "email": EmailChannel(),
        "discord": WebhookChannel("discord", settings.discord_webhook_url),
        "slack": WebhookChannel("slack", settings.slack_webhook_url),
        "matrix": WebhookChannel("matrix", settings.matrix_webhook_url),
        "make": WebhookChannel("make", settings.make_webhook_url),
        "plane": WebhookChannel("plane", settings.plane_webhook_url),
        "telegram": TelegramChannel(),
    }
