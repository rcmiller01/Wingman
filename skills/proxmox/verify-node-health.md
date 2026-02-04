---
id: proxmox-node-health
title: Verify Proxmox node health
tier: 1
category: proxmox
risk: safe
short_description: Baseline health checks for a Proxmox node before taking action.
version: 1.0
applies_to:
  subsystems: [proxmox]
  signatures: [proxmox.node.health]
  resource_types: [node]
inputs:
  - name: node_name
    type: string
    required: true
    description: Proxmox node name to inspect.
  - name: api_endpoint
    type: string
    required: false
    description: Optional API endpoint override.
    default: https://proxmox.example.local:8006
outputs:
  - plan
  - commands
---

## Purpose
Provide a safe, repeatable checklist for verifying Proxmox node health.

## When to Use
- Before scheduling maintenance on a node.
- When incident signals indicate degraded Proxmox services.

## Inputs
- `node_name`: used to scope API and CLI checks.
- `api_endpoint`: optional override for API calls.

## Preconditions
- Read-only access to the Proxmox API.
- SSH access if CLI checks are required.

## Plan
1. Confirm cluster quorum and node membership.
2. Inspect service status for core Proxmox daemons.
3. Review recent logs for warnings and errors.
4. Capture key metrics (CPU, memory, storage usage) for the node.

## Commands
```bash
# API health summary
pveum user list --node {{node_name}}

# Service status
systemctl status pve-cluster pvedaemon pveproxy

# Resource usage snapshot
pvesh get /nodes/{{node_name}}/status
```

## Validation
- Cluster reports quorum and the node is listed as online.
- Services are active and not in a failed state.
- Resource usage is within expected bounds.

## Rollback
No changes are made; no rollback required.

## Notes
If any command output shows errors, capture the logs and escalate to deeper diagnostics.
