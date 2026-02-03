# Skills Library

This index lists available Tier 1 and Tier 2 skills along with their applicability. Use it as the single source for discovery and filtering; individual skills contain the full runbook details.

| id | title | tier | category | risk | short_description | file_path | applies_to.signatures | applies_to.subsystems |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| proxmox-node-health | Verify Proxmox node health | 1 | proxmox | safe | Baseline health checks for a Proxmox node before taking action. | skills/proxmox/verify-node-health.md | proxmox.node.health | proxmox |
| ceph-replicated-pool-plan | Create a replicated pool plan | 2 | ceph | elevated | Draft a plan to create a replicated Ceph pool with guardrails. | skills/ceph/create-replicated-pool-plan.md | ceph.pool.create | ceph |

## Chat Commands

- `list skills` — list available skills (supports optional filters).
- `show skill <id>` — show a skill summary and headings.
- `run skill <id>` — collect inputs, then render the plan package (no execution).
