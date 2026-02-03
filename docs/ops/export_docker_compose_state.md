# Export Docker Compose State (Optional)

If you run Wingman via Docker Compose, keep a copy of the runtime state that helps with a clean restore.

## What to Export

- Compose files you use (`docker-compose.yml`, overrides).
- `.env` values (store securely, never in Git).
- Container image tags or digests in use.

## Suggested Procedure

1. Save compose files to your infra repo.
2. Export environment variables to a secure secret store.
3. Record running image tags:
   ```bash
   docker compose images
   ```
4. Store everything alongside your Postgres dump metadata for a full restore.
