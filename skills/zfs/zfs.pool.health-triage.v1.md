---
id: zfs.pool.health_triage.v1
title: "ZFS Pool Health Triage"
tier: 1
category: zfs
risk: safe
short_description: "Interpret zpool status and events to spot degraded or failing devices."
applies_to:
  subsystems:
    - zfs
  signatures:
    - zfs_pool_degraded
    - zfs_pool_faulted
  resource_types:
    - pool
---

# Purpose
Assess ZFS pool health and identify disk or cabling issues using read-only checks.

# When to Use
- ZFS reports `DEGRADED` or `FAULTED`.
- You see read/write/checksum errors.

# Inputs
- `{{pool_name}}` (string, optional): Pool name; omit to check all pools.

# Preconditions
- Access to the host with ZFS tooling.

# Plan
1. Review `zpool status` for device errors.
2. Check recent ZFS events for error history.
3. Review IO stats to identify slow devices.

# Commands
> Copy/paste as needed. Do not run automatically.

```bash
# Pool status and errors
zpool status -v {{pool_name}}

# Recent events
zpool events -v

# IO stats (1s sample; Ctrl+C to stop)
zpool iostat -v 1
```

# Validation
- Healthy pools show `state: ONLINE` and `errors: No known data errors`.
- Degraded pools list affected devices with read/write/checksum errors.

# Rollback
- Not applicable (read-only diagnostics).

# Notes
- If a device shows persistent errors, plan a replacement.
- Check cabling and HBAs for link errors.
