---
id: proxmox.task.failure_investigation.v1
title: "Proxmox Task Failure Investigation"
tier: 1
category: proxmox
risk: safe
short_description: "Extract error signatures from failed Proxmox tasks for ticketing and escalation."
applies_to:
  subsystems:
    - proxmox
  signatures:
    - proxmox_task_failed
  resource_types:
    - task
    - vm
---

# Purpose
Interpret failed Proxmox tasks and capture the key error signature for incident notes or ticketing.

# When to Use
- A backup, migrate, or snapshot task failed.
- The Proxmox UI shows an error but no clear root cause.

# Inputs
- `{{node}}` (string): Proxmox node name.
- `{{upid}}` (string): Task UPID from Proxmox.
- `{{vmid}}` (string, optional): VM/CT ID if applicable.

# Preconditions
- Read access to Proxmox task logs and system journal.

# Plan
1. Retrieve the task details and log output.
2. Extract the key error line and any referenced resource.
3. Check correlated system logs around the task time.
4. Produce a short error signature for escalation.

# Commands
> Copy/paste as needed. Do not run automatically.

```bash
# Task metadata
pvesh get /nodes/{{node}}/tasks/{{upid}}/status

# Task log output
pvesh get /nodes/{{node}}/tasks/{{upid}}/log

# Journald correlation (last 2 hours as a default window)
journalctl --since "2 hours ago" -u pvedaemon -u pveproxy --no-pager | tail -n 200
```

# Validation
- You can identify a clear error line (e.g., permission denied, storage full, timeout).
- The error signature includes task type, resource (VMID, storage), and time.

# Rollback
- Not applicable (read-only diagnostics).

# Notes
- If storage or backup errors are involved, capture storage name and free space.
- For recurring failures, attach the UPID, error line, and node name to the ticket.
