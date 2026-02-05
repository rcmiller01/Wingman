# Phase 1 Worker Operations Runbook

## Scope
This runbook covers Tickets PH1-WKR-011 through PH1-QA-016:
- worker script execution
- control plane delegation
- offline buffering + replay
- worker/queue observability
- phase completion validation

## Feature Flags
- `WORKER_DELEGATION_ENABLED` (`false` default)
- `WORKER_DEFAULT_ID`
- `WORKER_SITE_NAME`

Set delegation on control plane only after at least one worker is online.

## Worker Startup
1. Start backend API.
2. Start worker process (`python -m worker.main`).
3. Verify registration and heartbeat:
   - `GET /api/workers/health`
   - worker should show `online` status and non-stale `last_seen`.

## Delegated Execution Flow
1. An approved action enters `PlanExecutor`.
2. If worker delegation is enabled and target is worker-eligible, a `worker_tasks` row is queued and `pg_notify` is emitted.
3. Worker claims task and executes one of:
   - `collect_facts`
   - `execute_script`
   - `execute_action`
4. Worker submits result envelope.
5. Control plane reconciles status back into:
   - `worker_tasks`
   - `action_history`
   - `todo_steps`

## Offline Mode
When result submission fails (network/control plane outage):
1. Worker writes envelope to offline spool dir.
2. Files are named `<payload_type>-<timestamp>-<task_id>.json`.
3. Replay runs continuously, newest-first.
4. File is deleted only after successful ack (`/api/workers/results` 2xx).

## Observability
Use these endpoints for triage:
- `GET /api/workers/health`
  - online/offline worker state
  - queue depth summary
- `GET /api/workers/metrics`
  - queue depth
  - task failure count
  - average task latency
  - heartbeat freshness per worker
  - offline backlog size (reported by workers)

## Troubleshooting
### Queue not draining
- Check `GET /api/workers/health` queue depth.
- Confirm worker heartbeat freshness.
- Confirm worker task claims are happening.

### Tasks stuck in executing
- Verify worker result submission succeeds.
- Check worker offline directory for buffered payloads.
- Check `worker_results` for matching idempotency key.

### Replay not clearing
- Validate backend reachability from worker host.
- Validate `/api/workers/results` accepts payload.
- Ensure payload_type is one of: `facts`, `logs`, `execution_result`, `health`.

## Phase 1 Completion Checklist
- [x] Plugins execute through registry
- [x] Worker receives and processes queued tasks
- [x] Worker registration + heartbeat available
- [x] Offline buffering stores and replays results
- [x] Operators can inspect queue/worker health with metrics
