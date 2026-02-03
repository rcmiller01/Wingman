---
id: backup.wingman.postgres_backup_restore.v1
title: "Wingman Postgres Backup and Restore"
tier: 2
category: backup
risk: elevated
short_description: "Backup and restore Wingman Postgres data with docker-compose compatible commands."
applies_to:
  subsystems:
    - backup
    - postgres
  signatures:
    - backup_failed
    - postgres_restore_needed
  resource_types:
    - database
    - container
---

# Purpose
Provide a safe backup and restore workflow for Wingman’s Postgres database using copy/paste commands.

# When to Use
- You need a fresh backup before maintenance.
- You need to restore from a known-good backup.

# Inputs
- `{{container_name}}` (string): Postgres container name or service name.
- `{{backup_path}}` (string): Target path on the host for the dump file.
- `{{db_name}}` (string, optional): Database name (default: wingman).
- `{{db_user}}` (string, optional): Database user (default: postgres).

# Preconditions
- Docker or docker-compose access on the host.
- **Warning:** Restore is destructive and overwrites data.

# Plan
1. Create a timestamped backup with `pg_dump`.
2. Verify the backup file exists and is non-empty.
3. Restore only if needed and after confirming the target is correct.

# Commands
> Copy/paste as needed. Do not run automatically.

```bash
# Backup
BACKUP_FILE="{{backup_path}}/wingman_$(date +%Y%m%d_%H%M%S).sql"
docker exec -t {{container_name}} pg_dump -U {{db_user}} {{db_name}} > "$BACKUP_FILE"

# Verify backup size
ls -lh "$BACKUP_FILE"
```

```bash
# Restore (destructive) - ensure you target the correct database
cat "$BACKUP_FILE" | docker exec -i {{container_name}} psql -U {{db_user}} {{db_name}}
```

# Validation
- Backup file exists and is non-empty.
- `psql` can list tables after restore:
```bash
docker exec -i {{container_name}} psql -U {{db_user}} -d {{db_name}} -c "\dt"
```
- Wingman application starts and connects to Postgres.

# Rollback
- If restore fails, reapply a previous backup file.
- Consider taking a fresh backup before attempting another restore.

# Notes
- Store backups securely and outside the container filesystem.
- For large databases, consider `pg_dump --format=custom` and `pg_restore`.
