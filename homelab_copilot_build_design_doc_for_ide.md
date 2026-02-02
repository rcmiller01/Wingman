# Homelab Copilot

## Build Design Doc for AI Coder (Phased Implementation)

**Goal:** Provide a complete, implementable blueprint for an AI coding agent to build the Homelab Copilot MVP and successive phases.

**Non-negotiables:**
- **Cloud-first reasoning** via user API keys; **local fallback** model for always-on classification/summarization/tool-selection.
- **No raw logs sent to cloud models.** Only distilled summaries and historical context (RAG output) + current incident summary may be sent.
- **No autonomous destructive actions.** Only **Guide** and **Assist** modes; Assist is bounded to non-auth, non-destructive steps.
- **Plugins never execute.** Plugins only observe/interpret/recommend using action templates.

---

## 1) Product Summary

Homelab Copilot is a privacy-forward infrastructure copilot for homelabs that:
- Observes Proxmox + containers and related infrastructure signals
- Explains incidents using a narrative layer
- Guides remediation via a policy-enforced control plane
- Keeps long-term operational memory via incident narratives + periodic log summary documents
- Integrates outward via webhooks (Discord/Telegram/SMTP/assistant bots)

### Support Contract (enforced by architecture)
**WILL:** observe state, correlate symptoms, explain incidents, propose safe steps, record changes, provide recovery artifacts.
**WILL NOT:** debug app business logic, run autonomous destructive actions, store secrets, exfiltrate raw logs.

---

## ARCHITECTURE SWITCH NOTICE (MANDATORY)

This document supersedes any prior plans that used Node/Express/Prisma or other stacks. **All implementation must follow the Python 3.12 + FastAPI control-plane-first architecture described below.** If you see conflicting instructions elsewhere, **ignore them** and adhere to this document.

### Hard Reset IDE Prompt
Use the following directive verbatim when starting work in an IDE or agent:

> Discard any previous Node/Prisma/Express backend plan. Start a new backend implementation in **Python 3.12** using **FastAPI**, following the **Control Plane First Rule** and the architecture in this document.

### Control Plane First Rule
The Control Plane is the core of the system and must be implemented **before** any UI, external integrations, or execution adapters. The Control Plane owns: situation building, plan proposal/validation, policy enforcement, todo generation, execution routing, verification, and audit/memory recording.

#### Forbidden shortcuts
- **Do not** implement a backend in Node/Express/Prisma or port any previous Node design.
- **Do not** build UI flows or dashboards before the Control Plane is functional.
- **Do not** bypass plan validation, policy checks, or approval gates to “speed up” execution.
- **Do not** allow plugins or integrations to execute actions directly.
- **Do not** send raw logs to cloud LLMs under any circumstances.

---

## 2) Core Architecture (Locked)

### Layers
1. **Intelligence Layer**
   - Cloud models (OpenAI/Anthropic/OpenRouter) invoked on demand
   - Local model (Ollama) always-on for: classification, summarization, tool selection, incident triage
2. **Control Plane (Core)**
   - Builds Situation from facts
   - Requests PlanProposal from cloud model when needed
   - Validates plan deterministically
   - Applies policy (Guide/Assist)
   - Generates TodoSteps
   - Routes approved steps to executors
   - Verifies outcomes
   - Records audit + memory
3. **Execution Layer**
   - Proxmox adapter, Docker/Podman adapter, Ansible runner, Browser controller
4. **Plugin System**
   - Observer + Diagnostic plugins; no secrets; no execution
5. **Persistent State Store**
   - Fact Store, Action History, Incident Narratives, Access Logs, Log Summary Documents, RAG index

### Control Plane State Machine
OBSERVE → ASSESS → PLAN → VALIDATE → GENERATE TODO → AWAIT APPROVAL → EXECUTE → VERIFY → RECORD
- Bounded retries and bounded plan iterations.

---

## 3) Observability Model (Locked)

### Sources
- **Lifecycle & resources** (Proxmox + Docker/Podman APIs)
- **Network reality** (DNS reachability; Pi-hole integration later)
- **Logs** (PRIMARY):
  - Always: container stdout/stderr collection
  - Optional: user-declared file log paths per app/service
- **Filesystem monitoring** (opt-in at launch):
  - inotify-based watch on selected mounts/paths; can be enabled later

### Log retention + summaries
- Raw logs retained **90 days**
- Before purge, generate **Log Summary Document** (covers last 90 days)
- Log Summary Documents retained **12 months**
- Incident narratives persist indefinitely unless user deletes

### Cloud boundary
- Raw logs never sent to cloud.
- Only RAG-distilled historical context + current incident summary are sent to cloud when needed.

---

## 4) Incident Narrative (Locked)

Incident Narrative is the primary long-term memory artifact.

**Fields (minimum):**
- incident_id, time_range, severity
- affected_resources[] (ResourceRef)
- symptoms[] (facts/events)
- root_cause_hypothesis + confidence
- evidence_refs (fact IDs, error signatures)
- resolution_steps (TodoStep IDs) + mode used
- verification_results
- outcome (resolved/mitigated/unresolved)
- lessons_learned (short)
- links to related incidents

**RAG uses only:** incident narratives + log summary documents.

---

## 5) Action Template System (Locked)

Plugins and planners recommend only **ActionTemplate** intents.
Control Plane translates them into executable **TodoSteps**.

### MVP ActionTemplate enum
- restart_resource
- start_resource
- stop_resource
- collect_diagnostics
- verify_resource_health
- validate_paths
- validate_permissions
- validate_dns_resolution
- validate_network_connectivity
- create_snapshot
- rollback_to_snapshot
- guided_ui_configuration (Guide only)

**Forbidden:** raw commands, API endpoints, credentials in templates.

---

## 6) Plugin Specification (Locked)

### Plugin types
- Observer: emits Facts/Events
- Diagnostic: emits Findings/Hypotheses/Recommendations (ActionTemplates)

### Security
- Plugins must declare read scopes; **secret_access must be none**.
- Plugins cannot execute.

### Output objects
- Fact, Event, Finding, Hypothesis, Recommendation
- ResourceRef must be stable (proxmox://node/vmid, docker://container_id, etc.)

---

## 7) Notifications / External Integrations (Locked)

### Primary integration primitive: Webhooks
- Copilot emits structured events via webhook router
- Targets: Discord, Telegram, SMTP gateway, OpenClaw/assistant bots

### Event types (MVP)
- incident_detected
- incident_resolved
- approval_required
- digest_ready
- degraded_mode_enabled

**Assistant integration is decoupled**: assistants subscribe to webhook events; they do not get execution authority.

---

## 8) Tech Stack (Complete)

### Runtime & Packaging
- **Docker-first** deployment (single compose for MVP)
- Optional: deploy as an LXC on Proxmox

### Backend (Control Plane + API)
- **Python 3.12**
- **FastAPI** (HTTP API)
- **Pydantic v2** (schemas)
- **SQLAlchemy** (DB access)
- **Alembic** (migrations)

### Background Jobs / Scheduling
- **APScheduler** (MVP scheduler)
- (Later) **Celery + Redis** or **RQ** if needed

### Datastores
- **PostgreSQL** (recommended default for MVP)
- **SQLite** (dev mode option)
- **Qdrant** (vector store for RAG; local)

### Integrations / Adapters
- **Proxmox**: proxmoxer (API client)
- **Docker/Podman**: docker SDK for Python
- **Ansible**: ansible-runner
- **Browser** (Guide-only, later phase): Playwright

### Log ingestion
- Docker logs API (stdout/stderr)
- File tailer for user-declared logs
- Parsing: regex + structured parsing where available

### Filesystem monitoring (opt-in)
- inotify via watchdog (Linux)

### LLM Providers
- Cloud: OpenAI, Anthropic, OpenRouter (unified client)
- Local: **Ollama**
  - Target small tool-capable model family: Qwen2.5/3 ~7–8B (configurable)

### Frontend (Dashboard)
- **Next.js (React) + TypeScript**
- UI components: shadcn/ui (or equivalent)
- Auth: local user/pass or reverse-proxy auth (MVP: local-only)

### Security
- Secrets: do not store in DB; use env vars + optional local secret store integration later
- No raw logs to cloud.

---

## 9) Project Structure (Repo Layout)

Monorepo:
- /backend
  - /app
    - api (FastAPI routers)
    - control_plane
    - adapters (proxmox, docker, ansible, browser)
    - collectors (logs, facts, network, optional filesystem)
    - plugins (registry, loader, interfaces)
    - policy (guide/assist rules)
    - rag (indexing + retrieval)
    - storage (db models, repositories)
    - notifications (webhook router)
- /frontend
  - dashboard UI
- /infra
  - docker-compose.yml
  - env templates
  - migrations

---

## 10) Phased Delivery Plan (with Success Endpoints)

### Phase 0 — Scaffold & Foundations
**Build:**
- Monorepo scaffolding, docker-compose (backend+db+qdrant)
- Basic FastAPI health endpoints
- DB schema + migrations baseline

**Success endpoint:**
- `docker compose up` yields working API + DB + Qdrant; CI runs lint + unit tests.

---

### Phase 1 — Observability MVP (Read-only)
**Build:**
- Proxmox adapter: list nodes, VMs/LXCs, status, basic metrics
- Docker adapter: list containers, status, restart counts, resource usage
- Fact Collector pipeline (adapters→collectors→normalizers→fact store)
- Frontend dashboard: inventory + current health summary

**Success endpoint:**
- Dashboard shows Proxmox + container inventory and live health.
- Facts stored and queryable for last N hours.

---

### Phase 2 — Logging MVP (Primary evidence)
**Build:**
- Container stdout/stderr ingestion (per container)
- Log storage with retention metadata
- UI: per-service log view (bounded)
- Error signature extraction into Log Facts (no raw logs to cloud)
- User-declared log file paths support (opt-in per service)

**Success endpoint:**
- For a chosen container, Copilot stores logs locally and emits log-derived facts.
- Users can add a file path log source for a service and see parsed errors.

---

### Phase 3 — Incident Engine + Narratives (Local intelligence)
**Build:**
- Incident detection rules (restart loops, repeated error signatures, dependency unreachable)
- Incident Narrative generation (local model permitted)
- Action History + Access Log tables
- Notification router with outgoing webhooks

**Success endpoint:**
- When an error repeats or restart loop occurs, an incident is created with a narrative.
- Webhook emits `incident_detected`.

---

### Phase 4 — Control Plane Guide Mode (Plans + To-dos)
**Build:**
- PlanProposal interface (cloud model) using only incident summary + RAG context when needed
- Deterministic plan validator (JSON schema + safety constraints)
- Policy engine for Guide mode
- Todo UI: approve step-by-step
- Executors: Docker restart/start/stop + diagnostics bundle
- Verification checks

**Success endpoint:**
- User can approve a safe step (e.g., restart a container) and see verification results.
- All actions are recorded in Action History.

---

### Phase 5 — Memory Compression + RAG (Historical intelligence)
**Build:**
- RAG indexing of Incident Narratives
- 90-day Log Summary Document generator; retention 12 months
- Retrieval: “similar incidents” surfaced internally
- Cloud LLM invocation only when needed, using current incident summary + retrieved context

**Success endpoint:**
- Copilot identifies recurring issue patterns across months and references prior outcomes.
- No raw logs are sent to cloud.

---

### Phase 6 — Plugin System (Extensibility)
**Build:**
- Plugin manifest schema + loader
- Plugin registry + capability checks
- Sample plugins:
  - Generic Container Health Diagnostics
  - Plex/Arr interaction diagnostics (narrow)

**Success endpoint:**
- Plugins can be installed/removed; they emit findings/recommendations; no execution.

---

### Phase 7 — Assist Mode + Browser (Optional / Post-MVP)
**Build:**
- Assist mode eligibility rules (non-auth, non-destructive only)
- Playwright browser controller for guided_ui_configuration (Guide-only)
- Safer long-running workflows

**Success endpoint:**
- Assist can auto-run low-risk actions; browser flows require explicit approval.

---

## 11) Definition of Done (MVP)

MVP = **Phases 0–5 only**. Anything beyond this section is explicitly out of scope unless manually approved.

### MVP Must Include (Hard Requirements)
- Proxmox + Docker observability (inventory + health)
- Container stdout/stderr log ingestion
- Optional user-declared file log ingestion
- Incident detection + Incident Narrative generation
- Guide Mode only (no Assist Mode in MVP)
- Action Templates + Todo approval flow
- Safe executor actions (restart/start/stop + diagnostics only)
- Webhook notifications
- 90-day log retention + Log Summary Document generation
- Log Summary Documents retained for 12 months
- RAG retrieval using **only** Incident Narratives + Log Summary Documents

### MVP Must NOT Include (Explicitly Forbidden)
- Assist Mode automation
- Filesystem monitoring enabled by default
- Browser automation
- Plugin marketplace or discovery UI
- Kubernetes support
- Terraform
- Multi-user RBAC
- Cloud-hosted SaaS mode
- Fine-tuning of any LLM
- Chat-style interfaces for Copilot

---

## 12) Engineering Guardrails

- Never send raw logs to cloud
- Enforce schema validation for any model output
- Store secrets outside DB
- Bound all loops (retries and re-plans)
- Ensure auditability (action + access logs)

---

## 13) Initial Implementation Notes

- Start with Docker adapter + logs ingestion: fastest path to visible value.
- Proxmox integration next: inventory and correlations.
- Keep filesystem monitoring off by default (feature flag + per-path opt-in).
- Design DB migrations early (facts, logs, incidents, actions).

---

## 14) Minimal MVP Checklist (For AI Coder)

The following checklist defines the **smallest acceptable implementation**. Do not exceed it.

### Backend
- [ ] FastAPI app boots via docker-compose
- [ ] PostgreSQL schema exists for:
  - facts
  - logs (with retention metadata)
  - incidents
  - incident_narratives
  - action_history
  - access_logs
- [ ] Docker adapter can:
  - list containers
  - read status
  - read restart count
  - fetch stdout/stderr logs
- [ ] Proxmox adapter can:
  - list nodes
  - list VMs/LXCs
  - read status
- [ ] Fact Collector pipeline stores normalized facts
- [ ] Incident detection rules trigger on:
  - restart loops
  - repeated error signatures
- [ ] Incident Narrative is generated and persisted
- [ ] Webhook router sends incident_detected event

### Control Plane (Guide Mode Only)
- [ ] ActionTemplate enum implemented
- [ ] Plan validator enforces schema and safety rules
- [ ] Todo list generated from approved plan
- [ ] User approval required for every step
- [ ] Docker executor supports restart/start/stop
- [ ] Verification checks run after execution

### Logs & Memory
- [ ] Raw logs retained for 90 days
- [ ] Log Summary Document generated before purge
- [ ] Log Summary Document stored for 12 months
- [ ] RAG index built only from narratives + summaries

### Frontend
- [ ] Dashboard loads
- [ ] Shows inventory
- [ ] Shows active incidents
- [ ] Shows incident narrative view
- [ ] Shows pending approvals

---

## 15) Stop Conditions for AI Coder (Critical)

The AI coder **MUST STOP** implementation when all conditions below are true:

- All MVP checklist items are completed
- docker-compose up works without manual intervention
- Dashboard renders without runtime errors
- A restart loop produces:
  - an incident
  - a narrative
  - a webhook notification
- A safe action can be approved and executed in Guide Mode

### Do NOT Add Unless Explicitly Requested
- Additional tests beyond basic unit tests for validators and policies
- Abstractions for future features
- Additional adapters or plugins
- Performance optimizations
- Refactors for elegance
- Over-engineered logging pipelines

If unsure whether something is needed:
**DO NOT IMPLEMENT IT.**

---

## 16) Handoff Prompt for IDE Agent (Copy/Paste)

You are an expert full-stack engineer.

Your task is to implement **only** the MVP defined in this document.

Rules:
- Follow the phased plan strictly; stop at Phase 5.
- Do not add features, abstractions, or tests not explicitly required.
- Enforce schema validation on all LLM outputs.
- Never send raw logs to cloud models.
- Prefer the simplest working implementation.

If a requirement is ambiguous, choose the **simpler interpretation**.

Deliverables:
- Working docker-compose
- Backend API + DB migrations
- Frontend dashboard
- Incident Narratives + Log Summary Documents
- Guide Mode control plane

Stop when the MVP checklist is satisfied.
