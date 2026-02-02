# Homelab Copilot - Python Backend

Python 3.12 + FastAPI + SQLAlchemy backend for Homelab Copilot.

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
uvicorn app.main:app --reload --port 8000
```

## Structure

- `app/api/` - FastAPI routers
- `app/control_plane/` - State machine & planner
- `app/adapters/` - Docker, Proxmox adapters
- `app/collectors/` - Fact & log collectors
- `app/policy/` - Guide mode enforcement
- `app/storage/` - SQLAlchemy models
- `app/rag/` - Vector indexing
- `app/notifications/` - Webhook router

## File log sources (opt-in)

File log ingestion is disabled by default. To enable it, configure a file log source and set `enabled=true`:

```bash
POST /api/logs/file-sources
{
  "name": "nginx-error",
  "path": "/var/log/nginx/error.log",
  "resource_ref": "file://nginx/error",
  "enabled": true,
  "retention_days": 90
}
```

Use `PATCH /api/logs/file-sources/{id}` to toggle `enabled` or update paths, and `DELETE /api/logs/file-sources/{id}` to remove a source. If no file sources are enabled, the file tailer is a no-op. Logs are stored with the standard retention policy and participate in error signature detection.
