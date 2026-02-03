---
id: proxmox.backup.job_setup.v1
title: "Proxmox Backup Job Setup Plan (PBS Preferred)"
tier: 2
category: proxmox
risk: elevated
short_description: "Create a backup job plan for selected VMIDs with retention guidance and validation checks."
applies_to:
  subsystems:
    - proxmox
    - backup
  signatures:
    - backup_job_missing
    - backup_failed
  resource_types:
    - backup_job
    - vm
---

# Purpose
Provide a safe, copy/paste plan to configure Proxmox backup jobs (PBS preferred), including retention guidance and validation checks.

# When to Use
- Backups are not configured or are missing for critical VMs.
- You need a standard backup schedule and retention policy.

# Inputs
- `{{vmids}}` (list of strings/ints): VM/CT IDs to include.
- `{{schedule}}` (string): Proxmox schedule (e.g., "daily", "sun 02:00").
- `{{storage_target}}` (string): Proxmox storage ID (PBS or other).
- `{{job_id}}` (string, optional): Existing job ID for updates, retention, or rollback.

# Preconditions
- You have permission to create or modify backup jobs in Proxmox.
- Storage target is already configured and reachable.
- **Warning:** This is an elevated change. Review in UI before applying.

# Plan
1. Confirm storage target and connectivity.
2. Decide on schedule and retention (daily, weekly, monthly).
3. Create the backup job via UI or CLI.
4. Validate job configuration and run a test backup if appropriate.

# Commands
> Copy/paste as needed. Do not run automatically.

```bash
# Verify storage target
pvesh get /storage/{{storage_target}}

# Create backup job (example; review options before use)
# NOTE: This creates or updates a job. Validate in UI.
pvesh create /cluster/backup \
  --storage {{storage_target}} \
  --schedule "{{schedule}}" \
  --mode snapshot \
  --compress zstd \
  --vmid {{vmids}}

# Optional retention (PBS supports prune/retention; set per policy)
# Example: keep last 7 daily, 4 weekly, 6 monthly
pvesh set /cluster/backup/{{job_id}} --prune-backups 'keep-daily=7,keep-weekly=4,keep-monthly=6'
```

**UI steps (alternative):**
1. Datacenter → Backup → Add.
2. Select `{{storage_target}}`, schedule `{{schedule}}`, and VMIDs `{{vmids}}`.
3. Enable `snapshot` mode and compression.
4. Set retention/prune policy per your standard.

**Optional OpenTofu snippet (placeholder, do not assume provider installed):**
```hcl
# Example placeholder only. Replace with your provider configuration.
resource "proxmox_backup_job" "daily" {
  storage  = "{{storage_target}}"
  schedule = "{{schedule}}"
  vmids    = [{{vmids}}]
  mode     = "snapshot"
  compress = "zstd"
  prune    = "keep-daily=7,keep-weekly=4,keep-monthly=6"
}
```

# Validation
- Backup job appears in Datacenter → Backup with correct schedule and VMIDs.
- `pvesh get /cluster/backup` shows the new job and retention policy.
- Optional: run a manual backup and confirm it completes successfully.

# Rollback
- Disable or remove the backup job in the UI, or:
```bash
pvesh delete /cluster/backup/{{job_id}}
```

# Notes
- Prefer PBS for deduplication and retention. If using other storage, confirm it supports snapshots.
- Avoid scheduling backups during peak workloads.
