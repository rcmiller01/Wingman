---
id: zfs.scrub.schedule_and_verify.v1
title: "ZFS Scrub Schedule and Verify"
tier: 2
category: zfs
risk: safe
short_description: "Schedule recurring ZFS scrubs and verify outcomes with read-only checks."
applies_to:
  subsystems:
    - zfs
  signatures:
    - zfs_scrub_missing
  resource_types:
    - pool
    - host
---

# Purpose
Provide a plan to schedule ZFS scrubs using systemd or cron and verify scrub results.

# When to Use
- Scrubs are not scheduled or happen irregularly.
- You need to validate recent scrub success.

# Inputs
- `{{pool_name}}` (string): ZFS pool name.
- `{{schedule}}` (string): Desired cadence (e.g., "weekly", "monthly", or a cron expression).

# Preconditions
- Access to the host with permissions to create timers or cron entries.
- Ensure the maintenance window aligns with IO load.

# Plan
1. Choose a schedule that avoids peak load.
2. Create a systemd service + timer (preferred) or a cron job.
3. Validate the timer and check scrub history after it runs.

# Commands
> Copy/paste as needed. Do not run automatically.

```ini
# /etc/systemd/system/zfs-scrub@.service
[Unit]
Description=ZFS scrub for pool %i

[Service]
Type=oneshot
ExecStart=/sbin/zpool scrub %i
```

```ini
# /etc/systemd/system/zfs-scrub@.timer
[Unit]
Description=ZFS scrub timer for pool %i

[Timer]
OnCalendar={{schedule}}
Persistent=true

[Install]
WantedBy=timers.target
```

```bash
# Enable timer for the pool
systemctl daemon-reload
systemctl enable --now zfs-scrub@{{pool_name}}.timer

# Verify timer
systemctl list-timers | grep zfs-scrub@{{pool_name}}
```

**Cron alternative (if systemd timers are unavailable):**
```cron
# Example: weekly Sunday at 02:00
0 2 * * 0 /sbin/zpool scrub {{pool_name}}
```

# Validation
- `zpool status {{pool_name}}` shows a recent scrub with no errors.
- `systemctl list-timers` shows the timer scheduled and active.

# Rollback
- Disable the timer or remove the cron entry.
```bash
systemctl disable --now zfs-scrub@{{pool_name}}.timer
```

# Notes
- Scrubs can be IO-intensive; schedule during low usage windows.
- Investigate any scrub errors promptly.
