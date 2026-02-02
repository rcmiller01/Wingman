"""Alerting pipeline with escalation support."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import yaml

from homelab.notifications.channels import AlertChannel, build_default_channels


logger = logging.getLogger(__name__)


@dataclass
class AlertContext:
    title: str
    message: str
    payload: dict[str, Any]
    severity: str
    tags: list[str]


class AlertPolicy:
    def __init__(self, name: str, match: dict[str, Any], notify: list[dict[str, Any]], escalate_after: str | None):
        self.name = name
        self.match = match
        self.notify = notify
        self.escalate_after = escalate_after

    def matches(self, context: AlertContext) -> bool:
        if "severity" in self.match and self.match["severity"] != context.severity:
            return False
        if "tags" in self.match:
            required = set(self.match["tags"])
            if not required.issubset(set(context.tags)):
                return False
        return True


class AlertPolicyEngine:
    def __init__(self, policies: list[AlertPolicy]):
        self.policies = policies

    @classmethod
    def from_yaml(cls, raw: str) -> "AlertPolicyEngine":
        data = yaml.safe_load(raw) or {}
        policies = []
        for policy in data.get("policies", []):
            policies.append(
                AlertPolicy(
                    name=policy.get("name", "unnamed"),
                    match=policy.get("match", {}),
                    notify=policy.get("notify", []),
                    escalate_after=policy.get("escalate_after"),
                )
            )
        return cls(policies)


class AlertingPipeline:
    def __init__(self, channels: dict[str, AlertChannel], engine: AlertPolicyEngine | None = None):
        self.channels = channels
        self.engine = engine

    async def dispatch(self, context: AlertContext) -> list[str]:
        targets: list[dict[str, Any]] = []
        if self.engine:
            for policy in self.engine.policies:
                if policy.matches(context):
                    targets.extend(policy.notify)
        else:
            targets.append({"channel": "email"})

        sent = []
        for target in targets:
            channel_name = target.get("channel")
            channel = self.channels.get(channel_name)
            if not channel:
                continue
            success = await channel.send(context.title, context.message, context.payload)
            if success:
                sent.append(channel_name)
        return sent


_default_channels = build_default_channels()
alerting_pipeline = AlertingPipeline(_default_channels)
