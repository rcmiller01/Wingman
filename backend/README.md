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
