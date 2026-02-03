---
id: proxmox.demo.skill_authoring_and_run.v1
title: "Demo: Skill Authoring and Safe Node Checks"
tier: 1
category: proxmox
risk: safe
short_description: "Demonstrates skill structure and performs read-only Proxmox node diagnostics."
applies_to:
  subsystems:
    - proxmox
  signatures:
    - proxmox_node_triage
  resource_types:
    - node
---

# Purpose
Show the required skill format while providing a harmless, read-only Proxmox node diagnostic workflow.

# When to Use
- You need an example of the Wingman skill structure.
- A Proxmox node appears unhealthy and you want quick, safe checks.

# Inputs
- `{{node}}` (string): Proxmox node name.
- `{{time_window_minutes}}` (int, default: 60): How far back to scan for recent tasks and logs.

# Preconditions
- CLI access with permission to run `pveversion`, `pvesh`, and `pvecm`.
- No changes should be made; commands are read-only.

# Plan
1. Confirm Proxmox version and node status.
2. Review recent tasks for failures in the time window.
3. Check storage availability and cluster status.
4. Identify next steps if warnings or failures appear.

# Commands
> Copy/paste as needed. Do not run automatically.

```bash
pveversion -v

pvesh get /nodes/{{node}}/status

# Recent tasks (newest first)
pvesh get /nodes/{{node}}/tasks --start 0 --limit 50

# Storage status
pvesh get /nodes/{{node}}/storage

# Cluster status (if applicable)
pvecm status
```

# Validation
- Node status reports `online` and no critical load/memory warnings.
- Task list shows no recent `ERROR` or `FAILED` entries in the window.
- Storage shows expected free/used capacity with no `inactive` status.
- Cluster (if present) shows quorum and all nodes online.

# Rollback
- Not applicable (read-only diagnostics).

# Notes
- If tasks failed, capture the UPID and use the task investigation skill.
- For persistent issues, drill down in the Proxmox UI or `journalctl -u pvedaemon -u pveproxy`.
