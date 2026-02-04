# Wingman Skills Reference

This document describes all available skills, their parameters, risk levels,
and expected behavior.

## Table of Contents

1. [Understanding Skills](#understanding-skills)
2. [Risk Tiers](#risk-tiers)
3. [Health Check Skills](#health-check-skills)
4. [Diagnostic Skills](#diagnostic-skills)
5. [Operations Skills](#operations-skills)
6. [Inventory Skills](#inventory-skills)
7. [Proxmox Skills](#proxmox-skills)

---

## Understanding Skills

### What is a Skill?

A skill is a templated, auditable action that Wingman can execute against your infrastructure.
Each skill has:

- **ID**: Unique identifier (e.g., `health-docker-ping`)
- **Risk Level**: Determines approval requirements
- **Parameters**: Required and optional inputs
- **Blast Radius**: What systems it affects

### Skill Categories

| Category | Description | Examples |
|----------|-------------|----------|
| **diagnostics** | Read-only inspection | Logs, status, stats |
| **remediation** | Fix problems | Restart, start, stop |
| **maintenance** | Housekeeping | Prune, cleanup |
| **monitoring** | Observe systems | Events, metrics |

---

## Risk Tiers

| Tier | Risk | Approval | Example |
|------|------|----------|---------|
| **Tier 1** | 🟢 Low | Auto-approve | Health checks, reading logs |
| **Tier 2** | 🟡 Medium | Human approval | Restart container, start/stop |
| **Tier 3** | 🔴 High | Approval + audit | Prune, delete, destructive ops |

### How Risk is Determined

- **Read-only operations** → Low risk
- **Reversible mutations** → Medium risk  
- **Irreversible/destructive** → High risk

---

## Health Check Skills

These skills are read-only and safe to run at any time.

### `health-docker-ping`

Check if Docker daemon is responsive.

| Property | Value |
|----------|-------|
| **Risk** | 🟢 Low (Tier 1) |
| **Category** | diagnostics |
| **Adapters** | docker |
| **Mutates** | No |
| **Scope** | Host |

**Parameters**: None

**Example Output**:
```
Docker 24.0.7 on Alpine Linux
```

---

### `health-container-status`

Get health and running status of a specific container.

| Property | Value |
|----------|-------|
| **Risk** | 🟢 Low (Tier 1) |
| **Category** | diagnostics |
| **Adapters** | docker |
| **Mutates** | No |
| **Scope** | Single container |

**Parameters**:
| Name | Required | Description |
|------|----------|-------------|
| `container` | ✅ | Container name or ID |

**Example**:
```bash
# Request
{ "container": "nginx" }

# Output
Status: running, Health: healthy, Running: true
```

---

### `health-container-list`

List all containers with their status and ports.

| Property | Value |
|----------|-------|
| **Risk** | 🟢 Low (Tier 1) |
| **Category** | diagnostics |
| **Adapters** | docker |
| **Mutates** | No |
| **Scope** | Host |

**Parameters**:
| Name | Required | Description |
|------|----------|-------------|
| `all` | ❌ | Include stopped containers |

**Example Output**:
```
NAMES           STATUS          PORTS                   IMAGE
nginx           Up 2 hours      0.0.0.0:80->80/tcp     nginx:latest
redis           Up 2 hours      6379/tcp               redis:7
```

---

### `health-resource-usage`

Show CPU, memory, and network usage for containers.

| Property | Value |
|----------|-------|
| **Risk** | 🟢 Low (Tier 1) |
| **Category** | diagnostics |
| **Adapters** | docker |
| **Mutates** | No |
| **Scope** | Host |

**Parameters**:
| Name | Required | Description |
|------|----------|-------------|
| `container` | ❌ | Specific container (default: all) |

**Example Output**:
```
NAME    CPU %   MEM USAGE / LIMIT   NET I/O
nginx   0.15%   32MiB / 512MiB      1.2MB / 500KB
redis   0.05%   16MiB / 256MiB      800KB / 200KB
```

---

### `health-disk-usage`

Show disk space used by Docker.

| Property | Value |
|----------|-------|
| **Risk** | 🟢 Low (Tier 1) |
| **Category** | diagnostics |
| **Adapters** | docker |
| **Mutates** | No |
| **Scope** | Host |

**Parameters**: None

**Example Output**:
```
TYPE            TOTAL     ACTIVE    SIZE      RECLAIMABLE
Images          10        5         2.5GB     1.2GB (48%)
Containers      8         3         500MB     200MB (40%)
Volumes         5         5         1GB       0B (0%)
```

---

## Diagnostic Skills

### `diag-logs-tail`

Get recent logs from a container (bounded).

| Property | Value |
|----------|-------|
| **Risk** | 🟢 Low (Tier 1) |
| **Category** | diagnostics |
| **Adapters** | docker |
| **Mutates** | No |
| **Scope** | Single container |

**Parameters**:
| Name | Required | Default | Description |
|------|----------|---------|-------------|
| `container` | ✅ | - | Container name |
| `lines` | ❌ | 100 | Number of lines |
| `since` | ❌ | - | Time filter (e.g., "1h", "2024-01-01") |

**Example**:
```bash
{ "container": "nginx", "lines": 50, "since": "1h" }
```

---

### `diag-logs-errors`

Search container logs for error patterns.

| Property | Value |
|----------|-------|
| **Risk** | 🟢 Low (Tier 1) |
| **Category** | diagnostics |
| **Adapters** | docker |
| **Mutates** | No |
| **Scope** | Single container |

**Parameters**:
| Name | Required | Description |
|------|----------|-------------|
| `container` | ✅ | Container name |
| `pattern` | ❌ | Custom grep pattern (default: error\|fail\|exception) |

---

### `diag-container-processes`

Show processes running inside a container.

| Property | Value |
|----------|-------|
| **Risk** | 🟢 Low (Tier 1) |
| **Category** | diagnostics |
| **Adapters** | docker |
| **Mutates** | No |
| **Scope** | Single container |

**Parameters**:
| Name | Required | Description |
|------|----------|-------------|
| `container` | ✅ | Container name |

---

### `diag-container-events`

Show recent Docker events for a container.

| Property | Value |
|----------|-------|
| **Risk** | 🟢 Low (Tier 1) |
| **Category** | monitoring |
| **Adapters** | docker |
| **Mutates** | No |
| **Scope** | Single container |

**Parameters**:
| Name | Required | Default | Description |
|------|----------|---------|-------------|
| `container` | ✅ | - | Container name |
| `since` | ❌ | 1h | Time window |

---

## Operations Skills

⚠️ These skills **modify state** and require approval.

### `ops-container-restart`

Restart a Docker container.

| Property | Value |
|----------|-------|
| **Risk** | 🟡 Medium (Tier 2) |
| **Category** | remediation |
| **Adapters** | docker |
| **Mutates** | ⚡ Yes |
| **Scope** | Single container |
| **Reversible** | ✅ Yes |

**Parameters**:
| Name | Required | Default | Description |
|------|----------|---------|-------------|
| `container` | ✅ | - | Container name |
| `timeout` | ❌ | 10 | Stop timeout in seconds |

**Blast Radius**: Single container will restart. Connections will be dropped.

**Verification**: Checks `docker inspect` to confirm container is running after restart.

---

### `ops-container-start`

Start a stopped Docker container.

| Property | Value |
|----------|-------|
| **Risk** | 🟡 Medium (Tier 2) |
| **Category** | remediation |
| **Adapters** | docker |
| **Mutates** | ⚡ Yes |
| **Scope** | Single container |
| **Reversible** | ✅ Yes (can stop) |

**Parameters**:
| Name | Required | Description |
|------|----------|-------------|
| `container` | ✅ | Container name |

---

### `ops-container-stop`

Gracefully stop a Docker container.

| Property | Value |
|----------|-------|
| **Risk** | 🟡 Medium (Tier 2) |
| **Category** | remediation |
| **Adapters** | docker |
| **Mutates** | ⚡ Yes |
| **Scope** | Single container |
| **Reversible** | ✅ Yes (can start) |

**Parameters**:
| Name | Required | Default | Description |
|------|----------|---------|-------------|
| `container` | ✅ | - | Container name |
| `timeout` | ❌ | 10 | Graceful shutdown timeout |

**Blast Radius**: Container will stop. All connections will be dropped.

---

## Inventory Skills

### `inv-docker-images`

List Docker images on the host.

| Property | Value |
|----------|-------|
| **Risk** | 🟢 Low (Tier 1) |
| **Category** | diagnostics |
| **Adapters** | docker |
| **Mutates** | No |
| **Scope** | Host |

**Parameters**:
| Name | Required | Description |
|------|----------|-------------|
| `all` | ❌ | Include intermediate images |

---

### `inv-docker-volumes`

List Docker volumes.

| Property | Value |
|----------|-------|
| **Risk** | 🟢 Low (Tier 1) |
| **Category** | diagnostics |
| **Adapters** | docker |
| **Mutates** | No |
| **Scope** | Host |

---

## Proxmox Skills

These skills interact with Proxmox VE. They require Proxmox credentials configured.

### `health-proxmox-node`

Get status of a Proxmox node.

| Property | Value |
|----------|-------|
| **Risk** | 🟢 Low (Tier 1) |
| **Category** | diagnostics |
| **Adapters** | proxmox |
| **Mutates** | No |
| **Scope** | Single node |

**Parameters**:
| Name | Required | Description |
|------|----------|-------------|
| `node` | ✅ | Proxmox node name (e.g., "pve1") |

---

### `health-proxmox-vm-status`

Get status of a VM or LXC container.

| Property | Value |
|----------|-------|
| **Risk** | 🟢 Low (Tier 1) |
| **Category** | diagnostics |
| **Adapters** | proxmox |
| **Mutates** | No |
| **Scope** | Single VM |

**Parameters**:
| Name | Required | Default | Description |
|------|----------|---------|-------------|
| `node` | ✅ | - | Proxmox node name |
| `vmid` | ✅ | - | VM or LXC ID |
| `type` | ❌ | qemu | "qemu" for VMs, "lxc" for containers |

---

### `health-proxmox-list-vms`

List all VMs on a Proxmox node.

| Property | Value |
|----------|-------|
| **Risk** | 🟢 Low (Tier 1) |
| **Category** | diagnostics |
| **Adapters** | proxmox |
| **Mutates** | No |
| **Scope** | Node |

**Parameters**:
| Name | Required | Description |
|------|----------|-------------|
| `node` | ✅ | Proxmox node name |

---

## Network Skills

### `health-network-ping`

Ping a host from the Wingman server.

| Property | Value |
|----------|-------|
| **Risk** | 🟢 Low (Tier 1) |
| **Category** | diagnostics |
| **Adapters** | network |
| **Mutates** | No |
| **Scope** | External host |

**Parameters**:
| Name | Required | Default | Description |
|------|----------|---------|-------------|
| `host` | ✅ | - | Hostname or IP |
| `count` | ❌ | 4 | Number of pings |

---

### `health-http-check`

Check if an HTTP endpoint is responding.

| Property | Value |
|----------|-------|
| **Risk** | 🟢 Low (Tier 1) |
| **Category** | diagnostics |
| **Adapters** | network |
| **Mutates** | No |
| **Scope** | External endpoint |

**Parameters**:
| Name | Required | Default | Description |
|------|----------|---------|-------------|
| `url` | ✅ | - | Full URL to check |
| `expected_status` | ❌ | 200 | Expected HTTP status code |

---

### `health-docker-network-list`

List Docker networks.

| Property | Value |
|----------|-------|
| **Risk** | 🟢 Low (Tier 1) |
| **Category** | diagnostics |
| **Adapters** | docker |
| **Mutates** | No |
| **Scope** | Host |

**Parameters**: None

---

## Quick Reference Card

### Read-Only Skills (Safe Anytime)

```
health-docker-ping          Docker daemon health
health-container-status     Single container status  
health-container-list       List all containers
health-resource-usage       CPU/memory stats
health-disk-usage           Docker disk usage
health-proxmox-node         Proxmox node status
health-proxmox-vm-status    VM/LXC status
health-proxmox-list-vms     List VMs
health-network-ping         Network ping
health-http-check           HTTP endpoint check
health-docker-network-list  List networks
diag-logs-tail              Container logs
diag-logs-errors            Find errors in logs
diag-container-processes    Container processes
diag-container-events       Docker events
inv-docker-images           List images
inv-docker-volumes          List volumes
```

### Mutation Skills (Require Approval)

```
ops-container-restart       🟡 Restart container
ops-container-start         🟡 Start container
ops-container-stop          🟡 Stop container
```

### Usage Tips

1. **Start with health checks** - Run `health-container-list` to see what's available
2. **Check before fixing** - Use `health-container-status` before restarting
3. **Read logs first** - Use `diag-logs-tail` to understand issues
4. **Verify after actions** - Each mutation skill has a verification step

---

## Adding Custom Skills

Skills are registered in `backend/homelab/skills/`. To add a new skill:

```python
from homelab.skills.models import Skill, SkillMeta, SkillCategory, SkillRisk
from homelab.skills.registry import skill_registry

skill_registry.register(Skill(
    meta=SkillMeta(
        id="my-custom-skill",
        name="My Custom Skill",
        description="Does something useful",
        category=SkillCategory.diagnostics,
        risk=SkillRisk.low,
        target_types=["docker"],
        required_params=["container"],
        # Blast radius
        adapters=["docker"],
        mutates_state=False,
        target_scope="single",
    ),
    template="docker my-command {{ container }}",
))
```

See `backend/homelab/skills/day1_skills.py` for more examples.
