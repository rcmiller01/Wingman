# Phase 1 Anchor Ticket Backlog (IDE-Ready)

This backlog turns the v2 Phase 1 anchor into an execution-ordered set of tickets that can be picked up by any IDE agent or developer.

## How to Use This Backlog

- Complete tickets top-to-bottom unless marked parallelizable.
- Each ticket includes:
  - **Why** (purpose)
  - **Scope** (what to change)
  - **Implementation hints** (where to start)
  - **Definition of Done** (clear acceptance checks)
  - **Depends on** (ordering)

---

## Milestone Summary

## Progress

- ✅ `PH1-ADR-001` completed: `docs/adr/0001-phase1-contracts-and-boundaries.md`.
- ✅ `PH1-EXEC-002` completed: base package added at `backend/homelab/execution_plugins/` with tests in `backend/tests/execution_plugins/test_registry.py`.

---


Phase 1 roadmap items covered by this backlog:
- Execution plugin interface + Docker/Script plugins
- Worker agent base (fact collection, script execution)
- PostgreSQL queue (pg_notify) for worker communication
- Worker registration + health monitoring
- Worker offline file output (JSON/MD)

---

## Ticket 01 — ADR: Phase 1 Contracts and Boundaries

**ID:** `PH1-ADR-001`  
**Priority:** P0  
**Type:** Architecture/Docs  
**Depends on:** none

### Why
Lock architecture decisions before refactoring execution and adding workers.

### Scope
Create an ADR in `docs/` describing:
1. Execution plugin contract (methods, errors, lifecycle).
2. Worker task/result envelope schema.
3. Queue semantics (at-least-once, idempotency key handling).
4. Offline buffering contract (file naming, max size/time policy).

### Implementation hints
- Align with `docs/v2-roadmap.md` message formats and constraints.
- Explicitly define migration from current `PlanExecutor` path.

### Definition of Done
- ADR committed and linked from roadmap or runbook.
- At least one sequence diagram showing: approval -> queue -> worker -> result.

---

## Ticket 02 — Execution Plugin Base Package

**ID:** `PH1-EXEC-002`  
**Priority:** P0  
**Type:** Backend  
**Depends on:** `PH1-ADR-001`

### Why
Introduce the abstraction required by Phase 1 without breaking current actions.

### Scope
Add `backend/homelab/execution_plugins/` with:
- `base.py` defining `ExecutionPlugin` interface.
- `models.py` for plugin input/output payloads.
- `registry.py` for plugin registration and lookup.
- `errors.py` for typed plugin exceptions.

### Implementation hints
- Keep interface async and close to roadmap (`validate_pre`, `execute`, `validate_post`, `rollback`).
- Add strict typing and small dataclasses/pydantic models.

### Definition of Done
- Unit tests cover registry register/get/list and duplicate plugin handling.
- Plugin contract documented in module docstring.

---

## Ticket 03 — Built-in Docker Plugin

**ID:** `PH1-EXEC-003`  
**Priority:** P0  
**Type:** Backend  
**Depends on:** `PH1-EXEC-002`

### Why
Move existing Docker execution logic into the new plugin system.

### Scope
Create `backend/homelab/execution_plugins/docker_plugin.py`:
- Support restart/start/stop actions.
- Use current docker adapter methods.
- Include pre-validation for target/resource identifiers.

### Implementation hints
- Reuse validation patterns from current executor/router paths where possible.
- Return normalized structured results.

### Definition of Done
- Tests verify success, invalid input, and adapter failure surfaces.
- Plugin registered in registry bootstrap.

---

## Ticket 04 — Built-in Script Plugin (Sandboxed Subprocess MVP)

**ID:** `PH1-EXEC-004`  
**Priority:** P0  
**Type:** Backend/Security  
**Depends on:** `PH1-EXEC-002`

### Why
Phase 1 requires script execution capability for workers.

### Scope
Create `backend/homelab/execution_plugins/script_plugin.py`:
- Actions: `run_bash`, `run_python`.
- Allowlist/guardrails for command execution.
- Timeout + output size caps.

### Implementation hints
- Use subprocess with explicit command arrays (no shell interpolation when possible).
- Emit both stdout/stderr excerpts + truncation flags.

### Definition of Done
- Tests cover timeout, blocked command, successful script execution.
- Security assumptions documented in code comments.

---

## Ticket 05 — Plan Executor Refactor to Plugin Routing

**ID:** `PH1-EXEC-005`  
**Priority:** P0  
**Type:** Backend  
**Depends on:** `PH1-EXEC-003`, `PH1-EXEC-004`

### Why
Control plane should execute through plugin registry, not hardcoded branching.

### Scope
Refactor `backend/homelab/control_plane/plan_executor.py`:
- Route action execution through plugin registry.
- Keep existing action status transitions and DB updates.
- Preserve compatibility for currently supported actions.

### Implementation hints
- Introduce action->plugin/action mapping helper.
- Keep legacy fallback path behind feature flag for safe rollout.

### Definition of Done
- Existing execution flow still works for restart/start/stop.
- Integration test verifies approved action reaches plugin and updates status.

---

## Ticket 06 — Worker Service Skeleton

**ID:** `PH1-WKR-006`  
**Priority:** P0  
**Type:** Backend/Infra  
**Depends on:** `PH1-ADR-001`

### Why
Establish runtime boundary between control plane and worker execution.

### Scope
Add `backend/worker/` package with:
- `main.py` loop entrypoint.
- `config.py` worker settings.
- `client.py` for control-plane communication.
- `runner.py` task dispatch router.

### Implementation hints
- Include hardcoded worker constraints from roadmap (local-only cloud LLM off).
- Keep worker loop simple and observable (structured logs).

### Definition of Done
- Worker boots, reads config, performs heartbeat stub, exits cleanly on signal.

---

## Ticket 07 — Worker Task Envelope + API Endpoints

**ID:** `PH1-WKR-007`  
**Priority:** P0  
**Type:** Backend/API  
**Depends on:** `PH1-WKR-006`

### Why
Control plane and workers need stable message schemas.

### Scope
Implement shared schema models for:
- Task assignment payload.
- Worker result payload (facts/logs/execution_result/health).

Add API endpoints (or service layer) for:
- Worker fetch task.
- Worker submit result.

### Implementation hints
- Reuse envelope naming from roadmap to avoid future migration.
- Validate payloads strictly.

### Definition of Done
- Contract tests pass for valid/invalid payloads.
- Backward-compatible defaults for optional fields.

---

## Ticket 08 — PostgreSQL Queue with pg_notify

**ID:** `PH1-QUE-008`  
**Priority:** P0  
**Type:** Backend/DB  
**Depends on:** `PH1-WKR-007`

### Why
Phase 1 queue transport target is pg_notify.

### Scope
Add queue persistence and notifications:
- Migration for `worker_tasks` table.
- Producer on control-plane side.
- Worker listener/consumer.
- Task status transitions: queued -> claimed -> running -> done/failed.

### Implementation hints
- `NOTIFY` payload should be small (task id), fetch body from DB.
- Include retry count + next retry time.

### Definition of Done
- End-to-end local flow: queued task wakes worker and task is consumed.
- Retry behavior covered by tests.

---

## Ticket 09 — Worker Registration and Heartbeats

**ID:** `PH1-WKR-009`  
**Priority:** P1  
**Type:** Backend/DB/API  
**Depends on:** `PH1-WKR-006`

### Why
Control plane must know worker availability/capabilities.

### Scope
Add worker registry model + API:
- Register worker on startup.
- Periodic heartbeat updates.
- Expose worker status list endpoint for operators.

### Implementation hints
- Store `worker_id`, `site_name`, `capabilities`, `last_seen_at`, `status`.
- Mark worker offline if stale heartbeat exceeds threshold.

### Definition of Done
- Operator endpoint shows online/offline workers accurately.
- Heartbeat staleness logic covered by tests.

---

## Ticket 10 — Worker Fact Collection Executor

**ID:** `PH1-WKR-010`  
**Priority:** P1  
**Type:** Worker  
**Depends on:** `PH1-WKR-006`, `PH1-WKR-007`

### Why
Worker must run observation tasks from control plane.

### Scope
Implement worker handler for `collect_facts` tasks:
- Collect docker/proxmox/file-log facts based on worker config.
- Submit normalized fact payloads.

### Implementation hints
- Reuse existing collector logic where feasible, but isolate worker runtime concerns.

### Definition of Done
- Task executes and returns facts payload with timestamps + worker metadata.

---

## Ticket 11 — Worker Script Execution Executor

**ID:** `PH1-WKR-011`  
**Priority:** P1  
**Type:** Worker  
**Depends on:** `PH1-WKR-006`, `PH1-WKR-007`, `PH1-EXEC-004`

### Why
Worker needs to execute approved scripts delegated by control plane.

### Scope
Implement worker handler for `execute_script` tasks:
- Invoke script plugin from worker runtime.
- Return structured execution result with policy metadata.

### Implementation hints
- Include deterministic error codes for timeout/validation/runtime failure.

### Definition of Done
- Integration test validates approval -> queue -> worker script execution -> result persisted.

---

## Ticket 12 — Control Plane Routing to Workers

**ID:** `PH1-CP-012`  
**Priority:** P1  
**Type:** Backend  
**Depends on:** `PH1-QUE-008`, `PH1-WKR-009`, `PH1-WKR-010`, `PH1-WKR-011`

### Why
Control plane currently executes locally; Phase 1 requires delegated execution.

### Scope
Adjust control-plane execution step:
- For worker-eligible tasks, enqueue instead of local execute.
- Handle async result reconciliation back into action/todo records.

### Implementation hints
- Keep local execution fallback for non-worker targets behind feature flag.

### Definition of Done
- Approved tasks route to matching worker by capabilities.
- Action status reflects worker completion/failure correctly.

---

## Ticket 13 — Offline Buffer Writer (Worker)

**ID:** `PH1-OFF-013`  
**Priority:** P1  
**Type:** Worker  
**Depends on:** `PH1-WKR-006`

### Why
Workers must keep operating during control-plane outage.

### Scope
Implement local offline writer:
- Write facts/results/health as JSON files under configured offline dir.
- Enforce buffer size and max age constraints.

### Implementation hints
- Use atomic writes and deterministic filenames with ISO timestamps.

### Definition of Done
- Simulated outage writes files correctly.
- Rotation/eviction policy honors size/time limits.

---

## Ticket 14 — Offline Replay + Acknowledgement

**ID:** `PH1-OFF-014`  
**Priority:** P1  
**Type:** Worker/API  
**Depends on:** `PH1-OFF-013`, `PH1-WKR-007`

### Why
Buffered outputs must sync back on reconnect, newest-first.

### Scope
Implement replay contract:
- List pending offline files newest-first.
- Fetch/submit file payloads to control plane.
- Delete only after successful ack.

### Implementation hints
- Add rate limiting in replay loop.
- Keep replay resumable after interruption.

### Definition of Done
- Reconnect simulation proves newest-first replay and ack-delete semantics.

---

## Ticket 15 — Observability for Queue + Workers

**ID:** `PH1-OBS-015`  
**Priority:** P2  
**Type:** Backend/Operations  
**Depends on:** `PH1-QUE-008`, `PH1-WKR-009`

### Why
Need operational visibility to run Phase 1 in real environments.

### Scope
Add logs/metrics for:
- queue depth
- task latency
- task failure count
- heartbeat freshness
- offline backlog size

### Definition of Done
- Operators can identify stuck queue, dead workers, replay backlog quickly.

---

## Ticket 16 — End-to-End Test Matrix + Runbook

**ID:** `PH1-QA-016`  
**Priority:** P1  
**Type:** QA/Docs  
**Depends on:** all above functional tickets

### Why
Phase completion needs reproducible verification.

### Scope
Add:
- E2E tests for critical flows.
- `docs/` runbook section for worker rollout and failure recovery.
- Checklist mapped to Phase 1 roadmap checkboxes.

### Definition of Done
- CI/local test suite validates all Phase 1 anchors.
- Runbook includes outage/reconnect and queue troubleshooting steps.

---

## Suggested Sprint Order (Easy Pickup)

### Sprint A (Architecture + Execution Core)
1. `PH1-ADR-001`
2. `PH1-EXEC-002`
3. `PH1-EXEC-003`
4. `PH1-EXEC-004`
5. `PH1-EXEC-005`

### Sprint B (Worker + Contracts + Queue)
6. `PH1-WKR-006`
7. `PH1-WKR-007`
8. `PH1-QUE-008`
9. `PH1-WKR-009`

### Sprint C (Delegation + Offline)
10. `PH1-WKR-010`
11. `PH1-WKR-011`
12. `PH1-CP-012`
13. `PH1-OFF-013`
14. `PH1-OFF-014`

### Sprint D (Hardening)
15. `PH1-OBS-015`
16. `PH1-QA-016`

---

## Parallel Work Notes

Safe parallel groups once dependencies are met:
- `PH1-EXEC-003` and `PH1-EXEC-004` can run in parallel after `PH1-EXEC-002`.
- `PH1-WKR-009` can run in parallel with `PH1-QUE-008` after worker skeleton exists.
- `PH1-WKR-010` and `PH1-WKR-011` can run in parallel after task envelope is finalized.

---

## Final Exit Criteria (Phase 1 Complete)

Phase 1 is complete when the following are true in test evidence and runbook:
1. Plugins execute actions through a registry.
2. Worker receives and processes queued tasks via pg_notify.
3. Worker registers and heartbeats are monitored.
4. Worker continues with offline buffering during outages.
5. Offline replay syncs newest-first with acknowledgement.
