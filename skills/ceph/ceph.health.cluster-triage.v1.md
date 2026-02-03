---
id: ceph.health.cluster_triage.v1
title: "Ceph Cluster Health Triage"
tier: 1
category: ceph
risk: safe
short_description: "Interpret Ceph health summaries and identify next checks for WARN states."
applies_to:
  subsystems:
    - ceph
  signatures:
    - ceph_health_warn
    - ceph_health_error
  resource_types:
    - cluster
---

# Purpose
Interpret `ceph -s` and health warnings to decide next steps without making changes.

# When to Use
- Ceph reports `HEALTH_WARN` or `HEALTH_ERR`.
- Client IO is slow and you need a high-level cluster assessment.

# Inputs
- `{{cluster_name}}` (string, optional): Friendly name of the cluster.

# Preconditions
- CLI access to a host with Ceph admin tools.

# Plan
1. Capture the health summary and detail.
2. Review OSD tree and placement group (PG) status.
3. Identify stuck or degraded PGs and any down OSDs.
4. Escalate to specific component checks based on warnings.

# Commands
> Copy/paste as needed. Do not run automatically.

```bash
ceph -s
ceph health detail
ceph osd tree
ceph pg stat
```

# Validation
- **OK:** `HEALTH_OK`, no down OSDs, PGs in `active+clean`.
- **WARN:** Known warnings (e.g., degraded PGs, nearfull) with documented follow-ups.
- **ERR:** Any `HEALTH_ERR` or many PGs not `active+clean` requires escalation.

# Rollback
- Not applicable (read-only diagnostics).

# Notes
- For stuck PGs, capture the PG IDs and check `ceph pg query <pgid>`.
- If `nearfull` or `full`, plan capacity expansion or cleanup.
