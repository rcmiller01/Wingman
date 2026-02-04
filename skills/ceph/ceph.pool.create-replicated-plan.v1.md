---
id: ceph.pool.create_replicated_plan.v1
title: "Ceph Replicated Pool Creation Plan"
tier: 2
category: ceph
risk: elevated
short_description: "Plan and command set to create a replicated pool for VM workloads with safe defaults."
applies_to:
  subsystems:
    - ceph
  signatures:
    - ceph_pool_missing
  resource_types:
    - pool
---

# Purpose
Provide a plan and copy/paste commands to create a replicated Ceph pool for VM workloads.

# When to Use
- A VM workload needs a dedicated pool.
- You are planning to separate workloads by performance or fault domain.

# Inputs
- `{{pool_name}}` (string): Name of the new pool.
- `{{size}}` (int): Replication size (e.g., 3).
- `{{pg_num}}` (int, optional): Placement group count.
- `{{crush_rule}}` (string, optional): CRUSH rule name.

# Preconditions
- Cluster is `HEALTH_OK` and capacity is sufficient.
- **Warning:** Elevated change. Review defaults and capacity impact.

# Plan
1. Confirm cluster health and capacity.
2. Choose replication size and PG count.
3. Create the pool and set the application tag.
4. Validate pool health and client access.

# Commands
> Copy/paste as needed. Do not run automatically.

```bash
# Check cluster health
ceph -s
ceph df

# Create the pool (use pg_num if provided)
ceph osd pool create {{pool_name}} {{pg_num}}

# Set replication size
ceph osd pool set {{pool_name}} size {{size}}

# Optional: apply a CRUSH rule
# ceph osd pool set {{pool_name}} crush_rule {{crush_rule}}

# Tag the pool for RBD (VM workloads)
ceph osd pool application enable {{pool_name}} rbd
```

# Validation
- `ceph osd pool ls` lists `{{pool_name}}`.
- `ceph osd pool get {{pool_name}} size` matches expected replication.
- `ceph osd pool application get {{pool_name}}` shows `rbd`.

# Rollback
- If created in error, remove the pool **only after confirming it is unused**:
```bash
ceph osd pool delete {{pool_name}} {{pool_name}} --yes-i-really-really-mean-it
```

# Notes
- **Recommended defaults:** size 3, PG count based on total OSDs and workload.
- Over-provisioning PGs can cause performance issues; tune cautiously.
- Deleting pools is destructive. Ensure no data exists before removal.
