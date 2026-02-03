# Skills Library

This library is the canonical index of Tier 1–2 skills. It is intentionally concise so an AI or human can quickly discover the right runbook. Use the commands below to enumerate, view, and run skills without loading full content.

**Chat commands**
- `list skills`
- `show skill <id>`
- `run skill <id>`

## Skills Index

| id | title | tier | category | risk | short_description | file_path | subsystems | signatures | resource_types |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| proxmox.demo.skill_authoring_and_run.v1 | Demo: Skill Authoring and Safe Node Checks | 1 | proxmox | safe | Demonstrates skill structure and performs read-only Proxmox node diagnostics. | skills/proxmox/demo.skill-authoring-and-run.md | proxmox | proxmox_node_triage | node |
| proxmox.health.node_triage.v1 | Proxmox Node Health Triage | 1 | proxmox | safe | Triage Proxmox node health across CPU, memory, storage, cluster, and tasks. | skills/proxmox/proxmox.health.node-triage.v1.md | proxmox | proxmox_node_unhealthy, proxmox_task_failed | node |
| proxmox.task.failure_investigation.v1 | Proxmox Task Failure Investigation | 1 | proxmox | safe | Extract error signatures from failed Proxmox tasks for ticketing and escalation. | skills/proxmox/proxmox.task.failure-investigation.v1.md | proxmox | proxmox_task_failed | task, vm |
| proxmox.backup.job_setup.v1 | Proxmox Backup Job Setup Plan (PBS Preferred) | 2 | proxmox | elevated | Create a backup job plan for selected VMIDs with retention guidance and validation checks. | skills/proxmox/proxmox.backup.job-setup.v1.md | proxmox, backup | backup_job_missing, backup_failed | backup_job, vm |
| ceph.health.cluster_triage.v1 | Ceph Cluster Health Triage | 1 | ceph | safe | Interpret Ceph health summaries and identify next checks for WARN states. | skills/ceph/ceph.health.cluster-triage.v1.md | ceph | ceph_health_warn, ceph_health_error | cluster |
| ceph.osd.add_preflight.v1 | Ceph OSD Add Preflight | 1 | ceph | elevated | Preflight checks before adding a new OSD (disk empty, SMART OK, cluster stable). | skills/ceph/ceph.osd.add-preflight.v1.md | ceph | ceph_osd_add_requested | node, disk |
| ceph.pool.create_replicated_plan.v1 | Ceph Replicated Pool Creation Plan | 2 | ceph | elevated | Plan and command set to create a replicated pool for VM workloads with safe defaults. | skills/ceph/ceph.pool.create-replicated-plan.v1.md | ceph | ceph_pool_missing | pool |
| zfs.pool.health_triage.v1 | ZFS Pool Health Triage | 1 | zfs | safe | Interpret zpool status and events to spot degraded or failing devices. | skills/zfs/zfs.pool.health-triage.v1.md | zfs | zfs_pool_degraded, zfs_pool_faulted | pool |
| zfs.scrub.schedule_and_verify.v1 | ZFS Scrub Schedule and Verify | 2 | zfs | safe | Schedule recurring ZFS scrubs and verify outcomes with read-only checks. | skills/zfs/zfs.scrub.schedule-and-verify.v1.md | zfs | zfs_scrub_missing | pool, host |
| backup.wingman.postgres_backup_restore.v1 | Wingman Postgres Backup and Restore | 2 | backup | elevated | Backup and restore Wingman Postgres data with docker-compose compatible commands. | skills/backup/backup.wingman.postgres-backup-restore.v1.md | backup, postgres | backup_failed, postgres_restore_needed | database, container |
| backup.qdrant.rebuild_from_postgres.v1 | Qdrant Rebuild from Postgres (Wingman) | 1 | backup | safe | Explain how to rebuild Qdrant collections from Postgres without restoring Qdrant backups. | skills/backup/backup.qdrant.rebuild-from-postgres.v1.md | backup, qdrant, postgres | qdrant_index_missing, qdrant_rebuild_needed | database, vector_store |
| monitoring.prometheus.alert_triage.v1 | Prometheus Alert Triage | 1 | monitoring | safe | Interpret a Prometheus alert and map it to next diagnostic steps. | skills/monitoring/monitoring.prometheus.alert-triage.v1.md | monitoring, prometheus | prometheus_alert_firing | alert, service |
| monitoring.grafana.drilldown_playbook.v1 | Grafana Drilldown Playbook | 1 | monitoring | safe | Generic drilldown steps for latency, saturation, and error investigations. | skills/monitoring/monitoring.grafana.drilldown-playbook.v1.md | monitoring, grafana | service_latency_high, service_error_rate_high, service_saturation_high | service, dashboard |

## How skills get suggested
Wingman matches incidents using `applies_to` metadata. Subsystems narrow the domain (e.g., `ceph`), signatures reflect the symptom (e.g., `ceph_health_warn`), and resource types (e.g., `pool`) help pick the most relevant skill. Keep these fields accurate and concise.
