# Wingman v2.0 Roadmap

> **v1.0.0** - Locked. Single-site observer + advisor with policy-enforced control plane.
>
> **v2.0.0** - Multi-site, plugin ecosystem, execution delegation.

---

## Core Principles (Unchanged)

1. **Wingman is the brain, not the hands** - observes, advises, validates
2. **Privacy-first** - raw logs never leave local infrastructure
3. **Human-in-the-loop** - approval gates for all mutations
4. **Local AI preferred** - cloud LLM is opt-in, workers are local-only

---

## v2.0 Features

### 1. Plugin Marketplace / Third-Party Skills

**Goal:** Enable community-contributed skills without compromising security.

**Marketplace:** Centrally hosted on GitHub at `github.com/wingman-plugins/registry`

```
github.com/wingman-plugins/registry
├── plugins.json              # Index of all plugins
├── plugins/
│   ├── proxmox-snapshot-cleanup/
│   │   ├── manifest.yaml
│   │   ├── skill.py
│   │   ├── README.md
│   │   └── signature.sig     # Signed by maintainers for "verified"
│   ├── docker-log-rotate/
│   └── ...
└── CONTRIBUTING.md
```

**Local Structure:**
```
skills/
├── core/                    # Built-in skills (trusted)
├── community/               # Downloaded from marketplace
│   └── <plugin-id>/
│       ├── manifest.yaml    # Metadata, permissions, trust level
│       ├── skill.py         # Execution logic
│       └── README.md
└── local/                   # User's private skills
```

**Manifest Schema:**
```yaml
id: proxmox-snapshot-cleanup
name: Proxmox Snapshot Cleanup
version: 1.0.0
author: community
trust_level: sandboxed  # sandboxed | verified | trusted
permissions:
  - proxmox:read
  - proxmox:snapshot:delete
blast_radius:
  scope: vm
  mutates_state: true
  reversible: false
```

**Trust Model:**
| Level | Source | Capabilities |
|-------|--------|--------------|
| `trusted` | Core/built-in | Full adapter access |
| `verified` | Signed by maintainers | Declared permissions only |
| `sandboxed` | Community/unverified | Read-only, no execution |

**Sandboxing Approach:**

| Platform | Method | Notes |
|----------|--------|-------|
| **Linux** | Subprocess + seccomp | Syscall filtering, strong isolation |
| **Windows/Mac** | Subprocess + restricted imports | Fallback, blocks dangerous modules |

**Implementation:**
- Skill loader validates manifest before registration
- Sandboxed skills run in subprocess with restricted imports (+ seccomp on Linux)
- Marketplace discovery via GitHub API / raw URL fetch
- Signature verification for `verified` plugins using maintainer public key

---

### 2. Distributed Runners / Agent Workers

**Goal:** Multi-site monitoring with cost-controlled, local-only workers.

**Architecture:**
```
┌─────────────────────────────────────────────────────────────┐
│                 CONTROL PLANE (Central)                     │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  - Planning, approvals, UI                          │   │
│  │  - Cloud LLM allowed (user opt-in)                  │   │
│  │  - Aggregates facts from all workers                │   │
│  │  - Single source of truth for incidents             │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      │ PostgreSQL Queue (pg_notify)
                      │ or Redis (optional)
                      │
        ┌─────────────┼─────────────┬─────────────┐
        ▼             ▼             ▼             ▼
┌───────────┐   ┌───────────┐   ┌───────────┐   ┌───────────┐
│  Worker   │   │  Worker   │   │  Worker   │   │  Worker   │
│  Site A   │   │  Site B   │   │  Site C   │   │  Site D   │
│           │   │           │   │           │   │           │
│ Docker    │   │ Proxmox   │   │ K8s       │   │ Bare metal│
│           │   │           │   │           │   │           │
│ LOCAL     │   │ LOCAL     │   │ LOCAL     │   │ LOCAL     │
│ ONLY      │   │ ONLY      │   │ ONLY      │   │ ONLY      │
└───────────┘   └───────────┘   └───────────┘   └───────────┘
```

**Worker Constraints (Hardcoded):**
```python
# worker/config.py
ALLOW_CLOUD_LLM = False  # Not configurable - LOCAL ONLY
WORKER_MODE = True       # Disables control plane features
```

**Worker Responsibilities:**
- Fact collection (Docker, Proxmox, file logs)
- Script execution (from approved execution plugins)
- Log summarization before transmitting (privacy)
- Health reporting to control plane

**Worker LLM Options (Ranked):**
1. **No LLM (scripts only)** - Pure script execution, lightest weight, most predictable
2. **nemotron-mini:4b** (~2.7GB) - Local summarization if needed
3. **phi3:mini** (~2.3GB) - Alternative small model
4. **qwen2.5:0.5b** (~400MB) - Minimal footprint

**Recommended:** Default to scripts only. Local LLM optional for summarization.

**Worker Offline Behavior:**

When control plane is unreachable, workers operate autonomously:

```
┌─────────────────────────────────────────────────────────────┐
│                     WORKER OFFLINE MODE                     │
├─────────────────────────────────────────────────────────────┤
│ 1. Continue collecting facts                                │
│ 2. Continue executing ALREADY-APPROVED tasks only           │
│ 3. Write output to local files:                             │
│    └── /data/offline/                                       │
│        ├── facts-2024-01-15T10-30-00Z.json                  │
│        ├── facts-2024-01-15T10-31-00Z.json                  │
│        ├── execution-result-abc123.json                     │
│        └── health-2024-01-15T10-30-00Z.json                 │
│ 4. NO new plan approvals (requires control plane)           │
│ 5. Buffer limit: 24 hours or 100MB (configurable)           │
│ 6. On reconnect: control plane reads files NEWEST FIRST     │
│    - Prevents overwhelming with stale backlog               │
│    - Recent state prioritized over historical               │
└─────────────────────────────────────────────────────────────┘
```

**File Format (JSON/Markdown):**
```json
// facts-2024-01-15T10-30-00Z.json
{
    "worker_id": "site-a-docker",
    "site_name": "Site A",
    "timestamp": "2024-01-15T10:30:00Z",
    "payload_type": "facts",
    "payload": { ... }
}
```

**Reconnection Sync:**
1. Control plane polls worker `/offline/pending` endpoint
2. Worker returns list of files sorted by timestamp DESC (newest first)
3. Control plane fetches files one-by-one, newest first
4. Worker deletes files after confirmed receipt
5. Rate-limited to prevent thundering herd on reconnect

**Communication Protocol:**
```python
# Worker → Control Plane (online)
{
    "worker_id": "site-a-docker",
    "site_name": "Site A",
    "timestamp": "2024-01-15T10:30:00Z",
    "payload_type": "facts",  # facts | logs | execution_result | health
    "payload": { ... }
}

# Control Plane → Worker
{
    "task_id": "exec-123",
    "task_type": "execute_script",  # execute_script | collect_facts | health_check
    "script_id": "restart-container",
    "params": { "container": "nginx" },
    "timeout_seconds": 60
}
```

**Queue Options:**
- **PostgreSQL pg_notify** - No new infrastructure, good for <10 workers
- **Redis** - Better for 10+ workers, adds dependency
- **File-based per-worker** - Offline-capable, sync on reconnect (see above)

---

### 3. Execution Plugins

**Goal:** Wingman plans, plugins execute. Clean separation of concerns.

**Interface:**
```python
# execution_plugins/base.py
from abc import ABC, abstractmethod
from typing import Any

class ExecutionPlugin(ABC):
    """Base class for execution plugins."""

    @property
    @abstractmethod
    def plugin_id(self) -> str:
        """Unique identifier for this plugin."""
        pass

    @property
    @abstractmethod
    def supported_actions(self) -> list[str]:
        """List of action types this plugin can execute."""
        pass

    @abstractmethod
    async def validate_pre(self, action: dict) -> tuple[bool, str]:
        """Validate before execution. Returns (ok, message)."""
        pass

    @abstractmethod
    async def execute(self, action: dict) -> dict[str, Any]:
        """Execute the action. Returns result dict."""
        pass

    @abstractmethod
    async def validate_post(self, action: dict, result: dict) -> tuple[bool, str]:
        """Validate after execution. Returns (ok, message)."""
        pass

    @abstractmethod
    async def rollback(self, action: dict, result: dict) -> bool:
        """Attempt to rollback if possible. Returns success."""
        pass
```

**Built-in Plugins:**
| Plugin | Actions | Notes |
|--------|---------|-------|
| `docker` | restart, stop, logs | Uses Docker SDK |
| `proxmox` | snapshot, restart, migrate | Uses Proxmoxer |
| `script` | run_bash, run_python | Sandboxed subprocess |
| `ansible` | run_playbook | Delegates to ansible-runner |
| `http` | webhook, api_call | For external integrations |

**Plugin Registration:**
```python
# execution_plugins/registry.py
execution_registry = PluginRegistry()

# Built-in
execution_registry.register(DockerPlugin())
execution_registry.register(ProxmoxPlugin())
execution_registry.register(ScriptPlugin())

# User-installed
for plugin_path in Path("plugins/execution").glob("*/plugin.py"):
    plugin = load_plugin(plugin_path)
    execution_registry.register(plugin)
```

**Execution Flow:**
```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Wingman    │────▶│   Plugin     │────▶│   Target     │
│  (validate)  │     │  (execute)   │     │  (Docker/VM) │
└──────────────┘     └──────────────┘     └──────────────┘
       │                    │                    │
       │◀───────────────────┼────────────────────┘
       │    result + state  │
       │                    │
       ▼                    │
┌──────────────┐            │
│   Wingman    │◀───────────┘
│ (validate    │   post-execution
│  post + log) │   verification
└──────────────┘
```

---

### 4. Multi-User UI with SSO/OIDC

**Goal:** Team access with proper authentication and authorization.

**Architecture:**
```
┌─────────────────────────────────────────┐
│              Identity Provider          │
│  (Keycloak / Auth0 / Authentik / etc)   │
└─────────────────────┬───────────────────┘
                      │ OIDC
                      ▼
┌─────────────────────────────────────────┐
│              Wingman Backend            │
│  ┌─────────────────────────────────┐    │
│  │  OIDC Middleware                │    │
│  │  - Token validation             │    │
│  │  - User provisioning            │    │
│  │  - Role mapping                 │    │
│  └─────────────────────────────────┘    │
│  ┌─────────────────────────────────┐    │
│  │  RBAC Layer                     │    │
│  │  - Viewer: read-only            │    │
│  │  - Operator: approve actions    │    │
│  │  - Admin: configure, manage     │    │
│  └─────────────────────────────────┘    │
└─────────────────────────────────────────┘
```

**Roles:**
| Role | Permissions |
|------|-------------|
| `viewer` | Read dashboard, incidents, logs |
| `operator` | Approve/reject plans, execute skills |
| `admin` | Manage settings, users, plugins, workers |

**Implementation:**
- Extend existing `auth/` module with OIDC provider
- Add `user_id` and `role` to session model
- Audit log includes user attribution
- Frontend shows role-appropriate UI

**Supported Providers (via python-jose + authlib):**
- Keycloak
- Authentik
- Auth0
- Okta
- Google Workspace
- Generic OIDC

---

### 5. Declarative Generative UI / Analytics Dashboards

**Goal:** LLM chooses how to display data using a fixed component library.

**Inspiration:** [Homer Dashboard](https://github.com/bastienwirtz/homer) - YAML-configured sections with multiple component types.

**Architecture:**
```
User: "Show me what's been happening with my containers"
       │
       ▼
┌──────────────────────────────────────────┐
│  LLM analyzes available data and         │
│  generates declarative spec:             │
└──────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────┐
│  config.yaml (generated)                 │
│  ┌────────────────────────────────────┐  │
│  │ title: "Container Overview"        │  │
│  │ sections:                          │  │
│  │   - name: "Status"                 │  │
│  │     components:                    │  │
│  │       - type: stat_card            │  │
│  │         title: "Active Containers" │  │
│  │         query: "containers.active" │  │
│  │       - type: stat_card            │  │
│  │         title: "Incidents (24h)"   │  │
│  │         query: "incidents.recent"  │  │
│  │   - name: "Trends"                 │  │
│  │     components:                    │  │
│  │       - type: line_chart           │  │
│  │         title: "Restarts (7 days)" │  │
│  │         query: "restarts.weekly"   │  │
│  └────────────────────────────────────┘  │
└──────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────┐
│  Frontend renders using fixed components │
│  (validated against schema)              │
└──────────────────────────────────────────┘
```

**Fixed Component Library (the "what"):**
| Component | Purpose | Config Options |
|-----------|---------|----------------|
| `stat_card` | Single metric with optional trend | title, query, icon, color |
| `line_chart` | Time series data | title, query, x_axis, y_axis |
| `bar_chart` | Categorical comparisons | title, query, orientation |
| `table` | Tabular data | title, query, columns, sortable |
| `timeline` | Event sequences | title, query, group_by |
| `topology` | Infrastructure graph | title, query, layout |
| `heatmap` | Activity patterns | title, query, x_axis, y_axis |
| `list` | Simple item list | title, query, icon |

**LLM Controls (the "how"):**
- Which components to show
- Layout / arrangement (grid, sections)
- Which queries to use (from predefined set)
- Titles, labels, formatting
- Section grouping

**LLM Cannot:**
- Create new component types
- Execute arbitrary code
- Write raw SQL (uses named query keys)
- Access data outside approved queries

**Named Query Registry:**
```yaml
# queries.yaml - predefined safe queries
containers.active:
  sql: "SELECT COUNT(*) FROM facts WHERE type='container' AND status='running'"
  returns: integer

containers.list:
  sql: "SELECT name, status, uptime FROM facts WHERE type='container'"
  returns: table

incidents.recent:
  sql: "SELECT COUNT(*) FROM incidents WHERE created_at > NOW() - INTERVAL '24 hours'"
  returns: integer

restarts.weekly:
  sql: "SELECT DATE(created_at), COUNT(*) FROM incidents WHERE type='restart' AND created_at > NOW() - INTERVAL '7 days' GROUP BY DATE(created_at)"
  returns: timeseries
```

**Safety:**
- LLM generates YAML spec, not code
- Spec validated against JSON schema before rendering
- Only named queries allowed (no raw SQL)
- Rate limited to prevent abuse

**This is control-plane only** - can use cloud LLM if user opts in.

---

## Implementation Phases

### Phase 1: Foundation (Weeks 1-4)
- [ ] Execution plugin interface + Docker/Script plugins
- [ ] Worker agent base (fact collection, script execution)
- [ ] PostgreSQL queue (pg_notify) for worker communication
- [ ] Worker registration + health monitoring
- [ ] Worker offline file output (JSON/MD)

### Phase 2: Multi-Site (Weeks 5-8)
- [ ] Worker deployment packaging (Docker image, install script)
- [ ] Control plane aggregation of multi-worker facts
- [ ] Offline reconnection sync (newest-first)
- [ ] Incident correlation across sites
- [ ] Worker-scoped execution routing

### Phase 3: Authentication (Weeks 9-12)
- [ ] OIDC provider integration (Keycloak reference)
- [ ] RBAC implementation
- [ ] User audit logging
- [ ] Frontend auth flow + role-based UI

### Phase 4: Ecosystem (Weeks 13-16)
- [ ] Plugin manifest schema + loader
- [ ] GitHub marketplace integration (discovery, download)
- [ ] Subprocess + seccomp sandboxing (Linux)
- [ ] Subprocess + restricted imports fallback (Windows/Mac)
- [ ] Signature verification for verified plugins
- [ ] Community contribution guidelines

### Phase 5: Generative UI (Weeks 17-20)
- [ ] Fixed component library (Homer-inspired)
- [ ] Named query registry
- [ ] Declarative YAML schema
- [ ] LLM prompt engineering for spec generation
- [ ] Frontend dynamic renderer
- [ ] Pre-built dashboard templates

---

## Configuration Reference

### Control Plane (v2)
```env
# Existing v1 config plus:

# Worker Management
WORKER_QUEUE_BACKEND=postgres  # postgres | redis
REDIS_URL=redis://localhost:6379  # If using redis

# OIDC (optional)
OIDC_ENABLED=false
OIDC_ISSUER_URL=https://keycloak.example.com/realms/wingman
OIDC_CLIENT_ID=wingman
OIDC_CLIENT_SECRET=
OIDC_SCOPES=openid profile email

# Plugin Marketplace
MARKETPLACE_ENABLED=false
MARKETPLACE_REPO=github.com/wingman-plugins/registry
PLUGIN_AUTO_UPDATE=false

# Generative UI
GENERATIVE_UI_ENABLED=false
GENERATIVE_UI_MODEL=qwen2.5:7b  # Or cloud model if allowed
```

### Worker Agent (v2)
```env
# Worker identity
WORKER_ID=site-a-docker
WORKER_SITE_NAME=Site A
CONTROL_PLANE_URL=https://wingman.example.com

# Authentication
WORKER_TOKEN=<issued by control plane>

# Local only - these cannot be changed
# ALLOW_CLOUD_LLM=false (hardcoded)
# WORKER_MODE=true (hardcoded)

# Optional local LLM for summarization (default: none, scripts only)
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=nemotron-mini:4b  # Or leave empty for scripts-only mode

# Offline behavior
OFFLINE_BUFFER_DIR=/data/offline
OFFLINE_BUFFER_MAX_MB=100
OFFLINE_BUFFER_MAX_HOURS=24

# Adapters to enable
ENABLE_DOCKER=true
ENABLE_PROXMOX=false
ENABLE_FILE_LOGS=true

# Proxmox (if enabled)
PROXMOX_HOST=
PROXMOX_USER=
PROXMOX_TOKEN_NAME=
PROXMOX_TOKEN_VALUE=
```

---

## Decisions Log

| Question | Decision | Rationale |
|----------|----------|-----------|
| Plugin sandboxing | Subprocess + seccomp (Linux), restricted imports (fallback) | Strong isolation on servers, graceful degradation on dev machines |
| Marketplace hosting | GitHub (`wingman-plugins/registry`) | Free, versioned, PR-based contributions, Actions for validation |
| Worker offline behavior | Write JSON/MD files, sync newest-first on reconnect | Prevents backlog overwhelm, prioritizes recent state |
| Generative UI | Declarative YAML with fixed components | LLM chooses display, cannot create new component types |
| Worker LLM | Scripts default, nemotron-mini:4b optional | Lightest weight, most predictable, local-only enforced |

---

## Non-Goals for v2

- **Become a full SIEM** - Wingman is for homelabs, not enterprise SOC
- **Replace Ansible/Terraform** - We delegate to them, not replace
- **Real-time streaming** - Batch/polling is fine for homelab scale
- **Mobile app** - Web UI is sufficient

---

*Last updated: 2025-02*
