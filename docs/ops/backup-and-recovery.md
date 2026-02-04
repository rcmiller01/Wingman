# Backup & Recovery

This document defines a repeatable backup and restore workflow for Wingman runtime state.

## Source of Truth

- **GitHub repo (code + IaC):** declarative infrastructure, application code, and environment templates.
- **Postgres:** incidents, mappings, facts, summaries, and settings.
- **Qdrant:** rebuildable vector index. Treat as cache unless persistence is required.

## Backup Strategy

### Postgres (required)

- Run a nightly `pg_dump` to durable storage.
- Keep dumps on the same LAN but outside the host if possible.
- Script: `scripts/backup/backup_postgres.sh`.

### Qdrant (optional)

- Either:
  - Take Qdrant snapshots if you need exact vector persistence, **or**
  - Rebuild the collections from Postgres (preferred for simplicity).

### Config & Environment

- Store `.env.example` in Git.
- **Never** store secrets in the repo; use secret managers or host-level env vars.

## Restore Runbook

1. **Restore Postgres dump.**
   - Use `scripts/backup/restore_postgres.sh` with the desired dump file.
2. **Recreate Qdrant collections.**
   - Call the existing collection creation endpoint to rehydrate schemas.
3. **Reindex summaries (optional).**
   - Trigger summary reindexing if you want fast search immediately after restore.

## Operational Maturity Ladder

See the maturity ladder in [`docs/ops/maturity.md`](./maturity.md).
