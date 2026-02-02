# Alerting Pipeline

## Overview

Wingman supports a pluggable alerting pipeline that routes events to multiple destinations and supports escalation policies.

## Configuration (.env)

```env
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=
SMTP_TO=

DISCORD_WEBHOOK_URL=
SLACK_WEBHOOK_URL=
MATRIX_WEBHOOK_URL=
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

MAKE_WEBHOOK_URL=
PLANE_WEBHOOK_URL=
```

## Escalation policies

Policies live in `backend/homelab/notifications/escalation_policy.yaml` and support:

- `match` filters (`severity`, `tags`)
- `notify` channel list
- `escalate_after` (reserved for future scheduling)

Example:

```yaml
policies:
  - name: critical_vm_down
    match:
      severity: critical
      tags: [vm, production]
    notify:
      - channel: discord
      - channel: email
    escalate_after: 15m
```

## Supported channels

- Email (SMTP)
- Discord webhook
- Slack webhook
- Matrix webhook
- Telegram bot
- Make.com webhook
- Plane webhook
