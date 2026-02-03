---
id: proxmox.health.node_triage.v1
title: "Proxmox Node Health Triage"
tier: 1
category: proxmox
risk: safe
short_description: "Triage Proxmox node health across CPU, memory, storage, cluster, and tasks."
applies_to:
  subsystems:
    - proxmox
  signatures:
    - proxmox_node_unhealthy
    - proxmox_task_failed
  resource_types:
    - node
---

# Purpose
Quickly assess a Proxmox node’s health and identify likely areas of concern without making changes.

# When to Use
- Node is slow, unresponsive, or showing alerts.
- Backups or tasks have started failing on a specific node.

# Inputs
- `{{node}}` (string): Proxmox node name.
- `{{time_window_minutes}}` (int): How far back to check recent tasks and logs.

# Preconditions
- CLI access to Proxmox with read permissions for `pvesh`, `pvecm`, and logs.

# Plan
1. Review node CPU/memory/load and uptime.
2. Check storage status and capacity.
3. Validate cluster/quorum status if in a cluster.
4. Review recent tasks for failures and capture UPIDs.
5. If needed, inspect recent journal logs for service errors.

# Commands
> Copy/paste as needed. Do not run automatically.

```bash
# Node health
pvesh get /nodes/{{node}}/status

# Storage status
pvesh get /nodes/{{node}}/storage

# Cluster status (if applicable)
pvecm status

# Recent tasks
pvesh get /nodes/{{node}}/tasks --start 0 --limit 50

# Recent service logs (last {{time_window_minutes}} minutes)
journalctl -u pvedaemon -u pveproxy --since "{{time_window_minutes}} min ago" --no-pager
```

# Validation
- CPU and memory usage are within expected thresholds and no critical load warning appears.
- Storage entries are `active` and have sufficient free space.
- Cluster shows quorum and all nodes online (if clustered).
- No recent tasks show `ERROR` or `FAILED` without an identified cause.

# Rollback
- Not applicable (read-only diagnostics).

# Notes
- If you find a failed task, use the task failure investigation skill with the UPID.
- If storage is low, plan cleanup or migration before taking action.
