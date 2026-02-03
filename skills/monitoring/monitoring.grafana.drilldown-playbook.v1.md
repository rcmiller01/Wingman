---
id: monitoring.grafana.drilldown_playbook.v1
title: "Grafana Drilldown Playbook"
tier: 1
category: monitoring
risk: safe
short_description: "Generic drilldown steps for latency, saturation, and error investigations."
applies_to:
  subsystems:
    - monitoring
    - grafana
  signatures:
    - service_latency_high
    - service_error_rate_high
    - service_saturation_high
  resource_types:
    - service
    - dashboard
---

# Purpose
Provide a consistent Grafana drilldown workflow for latency, saturation, and error signals.

# When to Use
- You need to quickly determine why a service is slow or erroring.
- A dashboard indicates rising latency or saturation.

# Inputs
- `{{service_name}}` (string): Service being investigated.
- `{{node}}` (string, optional): Host or node name.

# Preconditions
- Access to Grafana dashboards and data sources.

# Plan
1. Start with the service overview dashboard.
2. Correlate latency, error rate, and throughput changes.
3. Drill into node-level metrics (CPU, memory, disk, network).
4. Check recent deployments or configuration changes.

# Commands
> Copy/paste as needed. Do not run automatically.

```text
# Example drilldown checklist
- Dashboard: {{service_name}} overview
- Panel: P95/P99 latency
- Panel: Error rate (4xx/5xx)
- Panel: Saturation (CPU, memory, queue depth)
- Node scope: {{node}}
```

# Validation
- You can identify a likely contributing metric (latency spike, saturation, or errors).
- Supporting graphs align with the incident window.

# Rollback
- Not applicable (read-only investigation).

# Notes
- If a deployment caused the issue, coordinate with release owners.
- Capture dashboard links in the incident ticket.
