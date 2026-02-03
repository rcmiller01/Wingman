---
id: ceph-replicated-pool-plan
title: Create a replicated pool plan
tier: 2
category: ceph
risk: elevated
short_description: Draft a plan to create a replicated Ceph pool with guardrails.
version: 1.0
applies_to:
  subsystems: [ceph]
  signatures: [ceph.pool.create]
  resource_types: [pool]
inputs:
  - name: pool_name
    type: string
    required: true
    description: Name of the new pool.
  - name: pg_num
    type: integer
    required: true
    description: Placement group count for the pool.
    min: 8
    max: 4096
  - name: size
    type: integer
    required: true
    description: Replication size (e.g., 3).
    min: 2
    max: 6
outputs:
  - plan
  - commands
---

## Purpose
Provide an elevated-risk plan for creating a replicated Ceph pool without executing changes.

## When to Use
- When planning new storage pools for workloads.
- During change review for Ceph capacity expansion.

## Inputs
- `pool_name`: target pool identifier.
- `pg_num`: placement group count.
- `size`: replica count.

## Preconditions
- Confirm cluster health is `HEALTH_OK`.
- Ensure change approval has been granted.

## Plan
1. Review current pool list and cluster health.
2. Validate desired PG count against cluster sizing guidance.
3. Prepare the pool creation commands for review.
4. Confirm rollback path and notification plan.

## Commands
```bash
# Health check
ceph status

# Review existing pools
ceph osd pool ls

# Create pool (review only)
ceph osd pool create {{pool_name}} {{pg_num}}
ceph osd pool set {{pool_name}} size {{size}}
```

## Validation
- `ceph status` reports `HEALTH_OK` post-change.
- Pool appears in `ceph osd pool ls` output with correct size.

## Rollback
- If needed, remove the pool and confirm data migration requirements:
  - `ceph osd pool delete {{pool_name}} {{pool_name}} --yes-i-really-really-mean-it`

## Notes
Coordinate with stakeholders before executing any pool changes.
