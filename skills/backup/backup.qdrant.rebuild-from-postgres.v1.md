---
id: backup.qdrant.rebuild_from_postgres.v1
title: "Qdrant Rebuild from Postgres (Wingman)"
tier: 1
category: backup
risk: safe
short_description: "Explain how to rebuild Qdrant collections from Postgres without restoring Qdrant backups."
applies_to:
  subsystems:
    - backup
    - qdrant
    - postgres
  signatures:
    - qdrant_index_missing
    - qdrant_rebuild_needed
  resource_types:
    - database
    - vector_store
---

# Purpose
Clarify that Qdrant is rebuildable from Postgres data and provide a safe, read-only plan to reindex.

# When to Use
- Qdrant collections are missing or corrupted.
- You need to rebuild vector indexes after a restore.

# Inputs
- `{{wingman_base_url}}` (string): Base URL for the Wingman API (no secrets).
- `{{target_dimension}}` (int, optional): Expected vector dimension.

# Preconditions
- Wingman API is reachable.
- Postgres data is intact and consistent.

# Plan
1. Confirm Postgres is healthy and Wingman can read data.
2. Recreate or verify Qdrant collections (if required).
3. Trigger a reindex/rebuild job via the Wingman API.
4. Validate collection health and point counts.

# Commands
> Copy/paste as needed. Do not run automatically.

```bash
# Check Wingman health endpoint (replace with your actual base URL)
curl -s {{wingman_base_url}}/health

# Example: trigger a reindex job (endpoint name is a placeholder; confirm in docs)
curl -X POST {{wingman_base_url}}/api/admin/reindex

# Example: verify collection status (placeholder endpoint)
curl -s {{wingman_base_url}}/api/admin/qdrant/collections
```

# Validation
- Reindex job reports success.
- Collection list includes expected collections with non-zero point counts.
- Queries return expected results.

# Rollback
- Not applicable. Reindexing is non-destructive and can be re-run.

# Notes
- If dimension mismatches occur, recreate collections with the correct `{{target_dimension}}`.
- Confirm endpoint paths in your Wingman API docs before use.
