# Wingman Operations Runbook

This runbook covers day-to-day operations for Wingman, including startup, 
configuration, troubleshooting, and maintenance procedures.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Deployable Homelab Release (Proxmox)](#deployable-homelab-release-proxmox)
3. [Execution Modes](#execution-modes)
4. [Authentication & Authorization](#authentication--authorization)
5. [Allowlists & Safety](#allowlists--safety)
6. [Key Rotation](#key-rotation)
7. [Audit Chain Verification](#audit-chain-verification)
8. [Retention & Cleanup](#retention--cleanup)
9. [Test Stack Operations](#test-stack-operations)
10. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Development Mode (Mock)

```bash
# Start dependencies
docker compose up -d

# Run backend (mock mode - default in dev)
cd backend
python -m uvicorn homelab.main:app --reload --port 8000

# Run frontend
cd frontend
npm run dev
```

### Integration Mode (Test Containers)

```bash
# Start test stack
./scripts/test-stack.ps1 up   # Windows
./scripts/test-stack.sh up    # Linux/Mac

# Run backend in integration mode
$env:EXECUTION_MODE = "integration"
$env:WINGMAN_EXECUTION_MODE = "integration"
python -m uvicorn homelab.main:app --reload --port 8000

# Run integration tests
$env:EXECUTION_MODE = "integration"
$env:WINGMAN_EXECUTION_MODE = "integration"
pytest tests/ -v -k integration
```

### Lab Mode (Real Infrastructure)

```bash
# CAUTION: This affects real infrastructure

# 1. Set execution mode
$env:EXECUTION_MODE = "lab"
$env:WINGMAN_EXECUTION_MODE = "lab"

# 2. Configure allowlists (REQUIRED)
$env:WINGMAN_CONTAINER_ALLOWLIST = "my-nginx,my-redis,my-app-*"
$env:WINGMAN_VM_ALLOWLIST = "100,101,102"
$env:WINGMAN_NODE_ALLOWLIST = "pve1,pve2"

# 3. Enable auth (recommended)
$env:AUTH_ENABLED = "true"
$env:WINGMAN_AUTH_SECRET = "your-secure-secret-key-here"

# 4. Start backend
python -m uvicorn homelab.main:app --port 8000
```

---

## Deployable Homelab Release (Proxmox)

### One-Command Deploy

```bash
cp deploy/.env.example deploy/.env
mkdir -p deploy/secrets

# Create secrets (required)
python - <<'PY' > deploy/secrets/wingman_auth_secret
import secrets
print(secrets.token_hex(32))
PY

# Proxmox secrets (choose one method)
# Option A: API token (format: user@realm!tokenname:tokenvalue)
echo "root@pam!wingman:YOUR_TOKEN_VALUE" > deploy/secrets/proxmox_api_token
: > deploy/secrets/proxmox_user
: > deploy/secrets/proxmox_password
: > deploy/secrets/proxmox_token_name

# Option B: User/password (set all three files)
: > deploy/secrets/proxmox_api_token
echo "root@pam" > deploy/secrets/proxmox_user
echo "YOUR_PASSWORD" > deploy/secrets/proxmox_password
echo "" > deploy/secrets/proxmox_token_name

# Start Wingman
docker compose -f deploy/docker-compose.yml up -d --build
```

> **Note:** If you are not using Proxmox yet, create empty secret files for
> `proxmox_api_token`, `proxmox_user`, `proxmox_password`, and `proxmox_token_name`.

### deploy/.env Reference

See `deploy/.env.example` for all options. The defaults are safe-by-default:

- `EXECUTION_MODE=lab` and `WINGMAN_EXECUTION_MODE=lab` (LAB mode fail-closed)
- Cloud LLM API keys unset
- Auth enabled with Docker secrets

### Migrations & Upgrades

Migrations run automatically on backend startup. For manual migration:

```bash
docker compose -f deploy/docker-compose.yml exec backend alembic upgrade head
```

Upgrade procedure:

```bash
git pull
docker compose -f deploy/docker-compose.yml up -d --build
```

### Backup & Restore

```bash
# Backup (Postgres + Qdrant)
./deploy/backup.sh

# Restore (pass backup dir)
./deploy/restore.sh deploy/backups/<timestamp>
```

### Smoke Test

```bash
# Optionally set API_KEY if auth is enabled and you want a non-dev key
export POSTGRES_PASSWORD=changeme
./scripts/smoke_live.sh
```

### Metrics

Wingman exposes a minimal Prometheus endpoint:

```
GET /api/health/metrics
```

---

## Execution Modes

Wingman has three execution modes that determine safety policies:

| Mode | Real Execution | Safety Policy | Use Case |
|------|---------------|---------------|----------|
| **mock** | ❌ No | None (all allowed) | Unit tests, demos, development |
| **integration** | ✅ Yes | Test containers only | Integration tests, CI/CD |
| **lab** | ✅ Yes | Allowlist-based | Production use |

### Mode Detection

Mode is determined by:

1. **Environment variable**: `EXECUTION_MODE=mock|integration|lab`
2. **Auto-detection**:
   - In pytest → mock
   - In CI → integration
   - Otherwise → mock (fail-safe)

### Mode Verification

```python
from homelab.skills.execution_modes import execution_mode_manager

# Check current mode
print(execution_mode_manager.get_status())

# Outputs:
# {
#   "mode": "lab",
#   "description": "Lab mode - real execution against infrastructure"
# }
```

---

## Authentication & Authorization

### Roles

| Role | Permissions |
|------|-------------|
| **viewer** | Read executions, logs, incidents (read-only) |
| **operator** | Create executions, run Tier 1 (low-risk) skills |
| **approver** | Approve/reject Tier 2/3 executions |
| **admin** | All permissions, including allowlist management |

### API Keys

**Development keys** (only work when `AUTH_ENABLED=false`):

```
wm_dev_viewer_key   → viewer role
wm_dev_operator_key → operator role  
wm_dev_approver_key → approver role
wm_dev_admin_key    → admin role
```

**Using API keys**:

```bash
# Via header
curl -H "X-API-Key: wm_dev_admin_key" http://localhost:8000/api/auth/whoami

# Check who you are
curl -H "X-API-Key: YOUR_KEY" http://localhost:8000/api/auth/whoami
```

### Enabling Authentication

```bash
# Required for production
$env:AUTH_ENABLED = "true"

# Set a secure secret (generate with: python -c "import secrets; print(secrets.token_hex(32))")
$env:WINGMAN_AUTH_SECRET = "your-64-char-hex-secret"
```

---

## Allowlists & Safety

### LAB Mode Fail-Closed

LAB mode **requires** allowlists. Without them, LAB mode is blocked:

```bash
# This will FAIL (no allowlists)
$env:EXECUTION_MODE = "lab"
$env:WINGMAN_EXECUTION_MODE = "lab"
# Error: LAB mode requested but no allowlists configured

# This works
$env:EXECUTION_MODE = "lab"
$env:WINGMAN_EXECUTION_MODE = "lab"
$env:WINGMAN_CONTAINER_ALLOWLIST = "nginx,redis,my-app-*"
```

### Allowlist Configuration

```bash
# Containers (comma-separated, supports prefix matching)
$env:WINGMAN_CONTAINER_ALLOWLIST = "nginx,redis,my-app-*"

# Proxmox VMs (by VMID)
$env:WINGMAN_VM_ALLOWLIST = "100,101,102"

# Proxmox Nodes
$env:WINGMAN_NODE_ALLOWLIST = "pve1,pve2"
```

### Dangerous Operations

By default, destructive operations (prune, delete) are disabled even in LAB mode:

```bash
# Enable dangerous operations (use with caution!)
$env:WINGMAN_ALLOW_DANGEROUS_OPS = "true"
```

### Read-Only Mode

Force all operations to be read-only:

```bash
$env:WINGMAN_READ_ONLY = "true"
```

### Checking Safety Status

```bash
curl http://localhost:8000/api/safety/status
```

Response:
```json
{
  "status": "armed",
  "is_lab_mode": true,
  "allowlists_configured": true,
  "dangerous_ops_available": false,
  "warnings": ["🔴 LAB MODE ARMED - Real infrastructure affected"],
  "config": {
    "container_allowlist": ["nginx", "redis"],
    "vm_allowlist": [],
    "node_allowlist": []
  }
}
```

---

## Key Rotation

### When to Rotate Keys

- Suspected key compromise
- Employee offboarding
- Regular rotation schedule (recommended: every 90 days)

### Rotation Process

```python
from homelab.auth import user_store

# 1. Generate new key for user
new_key = user_store.regenerate_api_key("user-id-here")

# 2. Provide new key to user (shown only once!)
print(f"New API key: {new_key}")

# 3. Old key is immediately invalidated
```

### Rotation with Grace Period

For zero-downtime rotation:

```python
from homelab.auth.secrets import get_key_rotation_manager

manager = get_key_rotation_manager()

# 1. Initiate rotation (both keys valid for 24 hours)
manager.initiate_rotation(
    user_id="user-123",
    old_key_hash="old-hash",
    new_key_hash="new-hash",
    rotated_by="admin-user-id",
    reason="Scheduled rotation"
)

# 2. User switches to new key

# 3. Complete rotation (after grace period)
manager.complete_rotation("user-123")
```

---

## Audit Chain Verification

### Why Verify?

The audit chain (ActionHistory) uses hash-linking to detect tampering.
Regular verification ensures audit integrity.

### Running Verification

```python
from homelab.storage.retention import retention_manager

async def verify():
    async with get_db_session() as db:
        report = await retention_manager.verify_audit_integrity(db)
        print(f"Chain valid: {report['is_valid']}")
        print(f"Total entries: {report['total_entries']}")
        print(f"Checkpoints: {len(report['checkpoints'])}")
        if report['violations']:
            print(f"VIOLATIONS: {report['violations']}")
```

### What Gets Verified

- **Hash continuity**: Each entry's `prev_hash` matches previous entry's `entry_hash`
- **Content integrity**: Recomputed hash matches stored hash
- **Sequence continuity**: No gaps in sequence numbers

### Checkpoints

Checkpoints are preserved entries that anchor the chain:

- **Genesis**: First entry (sequence_num=1)
- **Daily**: First entry of each day
- **Monthly**: First entry of each month

Even if entries are exported/archived, checkpoints allow partial verification.

---

## Retention & Cleanup

### Default Retention Periods

| Data Type | Retention | Environment Variable |
|-----------|-----------|---------------------|
| Completed executions | 7 days | `RETENTION_COMPLETED_EXECUTION_DAYS` |
| Failed executions | 14 days | `RETENTION_FAILED_EXECUTION_DAYS` |
| Other executions | 30 days | `RETENTION_EXECUTION_DAYS` |
| Log entries | 7 days | `RETENTION_LOG_DAYS` |
| Audit entries | 90 days | `RETENTION_AUDIT_DAYS` |

### Audit Entry Handling

**Important**: Audit entries are **never deleted**. They are:

1. Exported to JSON files before retention period
2. Checkpoints are preserved indefinitely
3. Chain verification remains possible

### Export Location

```bash
$env:WINGMAN_AUDIT_EXPORT_PATH = "/var/lib/wingman/audit-exports"
```

### Manual Cleanup

```python
from homelab.storage.retention import retention_manager

async def cleanup():
    async with get_db_session() as db:
        stats = await retention_manager.run_cleanup(
            executions=execution_store,
            db_session=db,
            export_path="/path/to/exports"
        )
        print(f"Cleaned: {stats.to_dict()}")
```

### Dry Run Mode

```bash
$env:RETENTION_DRY_RUN = "true"
# Cleanup will log what would be deleted but won't delete anything
```

---

## Test Stack Operations

### One-Command Management

```powershell
# Windows
.\scripts\test-stack.ps1 up       # Start
.\scripts\test-stack.ps1 down     # Stop
.\scripts\test-stack.ps1 reset    # Reset (clear data)
.\scripts\test-stack.ps1 status   # Check status
.\scripts\test-stack.ps1 health   # Health checks
.\scripts\test-stack.ps1 logs     # View logs
```

```bash
# Linux/Mac
./scripts/test-stack.sh up
./scripts/test-stack.sh down
./scripts/test-stack.sh reset
./scripts/test-stack.sh status
./scripts/test-stack.sh health
./scripts/test-stack.sh logs
```

### Test Containers

| Container | Port | Role |
|-----------|------|------|
| wingman-test-nginx | 8081 | Web server |
| wingman-test-redis | 6380 | Cache |
| wingman-test-postgres | 5433 | Database |
| wingman-test-alpine | - | General testing |

All containers have `wingman.test=true` label for safety policy.

---

## Troubleshooting

### LAB Mode Won't Enable

**Symptom**: "LAB mode requested but no allowlists configured"

**Solution**:
```bash
$env:WINGMAN_CONTAINER_ALLOWLIST = "your-containers-here"
# Must have at least one allowlist configured
```

### Rate Limited

**Symptom**: "429 Too Many Requests"

**Cause**: Too many failed authentication attempts

**Solution**: Wait for lockout to expire (check `Retry-After` header)

### Audit Chain Broken

**Symptom**: Chain verification reports violations

**Investigation**:
```python
report = await retention_manager.verify_audit_integrity(db)
for violation in report['violations']:
    print(f"Type: {violation['type']}, Seq: {violation.get('sequence_num')}")
```

**Recovery**:
- If entries were deleted externally, chain cannot be recovered
- Export affected range and document the gap
- Consider resetting chain for new entries (lose historical verification)

### Test Containers Not Starting

**Symptom**: `test-stack.ps1 up` shows containers not running

**Steps**:
1. Check Docker is running: `docker info`
2. Check port conflicts: `netstat -an | findstr "8081 6380 5433"`
3. Check logs: `.\scripts\test-stack.ps1 logs`
4. Reset stack: `.\scripts\test-stack.ps1 reset`

### Auth Not Working

**Symptom**: 401 Unauthorized

**Checks**:
1. Is auth enabled? `$env:AUTH_ENABLED`
2. Using dev keys with auth enabled? (dev keys only work when disabled)
3. Header correct? `X-API-Key: your-key` or `Authorization: Bearer token`

---

## First-Run Checklist

Before going live:

- [ ] Set `EXECUTION_MODE=lab` and `WINGMAN_EXECUTION_MODE=lab`
- [ ] Configure allowlists for your infrastructure
- [ ] Set `AUTH_ENABLED=true`
- [ ] Set secure `WINGMAN_AUTH_SECRET`
- [ ] Create real user accounts (not dev keys)
- [ ] Verify test stack works: `test-stack.ps1 health`
- [ ] Run a test execution and verify audit chain
- [ ] Configure retention export path
- [ ] Document your allowlist policy

---

## Support

- **Issues**: File on GitHub
- **Logs**: Check `backend_logs.txt` or container logs
- **Debug Mode**: Set `DEBUG=true` for verbose logging
