---
id: ceph.osd.add_preflight.v1
title: "Ceph OSD Add Preflight"
tier: 1
category: ceph
risk: elevated
short_description: "Preflight checks before adding a new OSD (disk empty, SMART OK, cluster stable)."
applies_to:
  subsystems:
    - ceph
  signatures:
    - ceph_osd_add_requested
  resource_types:
    - node
    - disk
---

# Purpose
Run safe, read-only checks before adding an OSD to confirm the cluster and disk are ready.

# When to Use
- You plan to add a new OSD to expand capacity.
- A disk was replaced and needs verification before use.

# Inputs
- `{{node}}` (string): Host where the disk is attached.
- `{{disk_device}}` (string): Device path (e.g., `/dev/sdb`).

# Preconditions
- Access to the node with permissions to run read-only disk and Ceph commands.
- **Warning:** This is an elevated workflow. Stop if checks fail.

# Plan
1. Confirm cluster health is stable (`HEALTH_OK` preferred).
2. Verify the disk is not mounted and has no active partitions in use.
3. Run SMART health checks and review errors.
4. Stop and escalate if any check fails.

# Commands
> Copy/paste as needed. Do not run automatically.

```bash
# Cluster health should be stable before changes
ceph -s
ceph health detail

# Disk visibility and mount checks
lsblk -f {{disk_device}}
lsblk -o NAME,SIZE,TYPE,MOUNTPOINT {{disk_device}}

# SMART health (read-only)
smartctl -a {{disk_device}}
```

# Validation
- Cluster reports `HEALTH_OK` or only minor warnings with a documented plan.
- Disk has no mounted filesystems and is not part of an existing OSD.
- SMART report shows `PASSED` and no critical errors.

# Rollback
- Not applicable (read-only preflight checks).

# Notes
- **Stop here if:** the disk has data, SMART errors, or the cluster is unstable.
- Actual OSD creation is intentionally omitted in Tier 1 skills.
