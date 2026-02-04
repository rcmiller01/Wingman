---
id: monitoring.prometheus.alert_triage.v1
title: "Prometheus Alert Triage"
tier: 1
category: monitoring
risk: safe
short_description: "Interpret a Prometheus alert and map it to next diagnostic steps."
applies_to:
  subsystems:
    - monitoring
    - prometheus
  signatures:
    - prometheus_alert_firing
  resource_types:
    - alert
    - service
---

# Purpose
Provide a repeatable checklist to interpret a Prometheus alert and identify what to check next.

# When to Use
- Prometheus alert is firing and you need to understand impact quickly.
- You need a quick link to relevant Grafana dashboards.

# Inputs
- `{{alert_name}}` (string): Name of the alert.
- `{{labels}}` (map, optional): Alert labels (e.g., `instance`, `job`, `service`).
- `{{time_window_minutes}}` (int): Lookback window for charts.

# Preconditions
- Access to Prometheus and Grafana UI.

# Plan
1. Read the alert summary and labels for scope.
2. Check the related service/instance metrics in Grafana.
3. Compare latency, error rate, and saturation signals.
4. Decide whether to page or open a ticket.

# Commands
> Copy/paste as needed. Do not run automatically.

```text
# Example PromQL placeholders (replace metric names with your own)
rate(http_requests_total{service="{{labels.service}}",status=~"5.."}[5m])

histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{service="{{labels.service}}"}[5m])) by (le))

avg(node_cpu_seconds_total{mode!="idle",instance="{{labels.instance}}"})
```

# Validation
- Identify whether the alert is transient or sustained over {{time_window_minutes}} minutes.
- Correlate alert timing with service errors, latency, or resource saturation.

# Rollback
- Not applicable (read-only triage).

# Notes
- Add a Grafana link to the ticket for the affected service.
- If the alert lacks context, improve labels and alert annotations.
