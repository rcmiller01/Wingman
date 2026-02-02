# Codex Tasks: Proposed Enhancements

These tasks convert the proposed enhancements into discrete, trackable issues.

## Logging & Observability

### Task 1: Add OpenTelemetry request tracing + correlation IDs
**Goal**: Ensure every request has a `request_id` and OTEL trace/span IDs propagated across backend, adapters, and LLM calls.

**Scope**
- Add Express middleware for `request_id` creation/propagation.
- Ensure adapters and LLM calls accept and log the propagated ID.
- Update log format to include `request_id`, `trace_id`, and `span_id`.

**Acceptance Criteria**
- Every inbound request logs `request_id` + trace IDs.
- Adapter and LLM logs include the same IDs.

### Task 2: OTEL instrumentation for backend + Prisma + adapters
**Goal**: Add structured OTEL spans for key backend flows.

**Scope**
- Instrument Express routes.
- Instrument Prisma queries.
- Instrument adapter calls (e.g., docker/proxmox) and LLM calls.

**Acceptance Criteria**
- Spans visible in OTEL Collector output for API, Prisma, adapters, LLM.

### Task 3: Add OTEL export configs for Loki + Elastic/OpenSearch
**Goal**: Provide OTEL Collector configuration to export logs/traces to Loki and Elastic/OpenSearch.

**Scope**
- Add example OTEL Collector configs for Loki and Elastic/OpenSearch.
- Document environment variables needed to enable each target.

**Acceptance Criteria**
- Configs exist and are referenced in documentation.

### Task 4: Provide logging.compose.override.yml for Loki + Grafana
**Goal**: Offer a turnkey homelab logging stack.

**Scope**
- Add compose override file spinning up OTEL Collector, Loki, and Grafana.
- Provide minimal Grafana data source setup instructions.

**Acceptance Criteria**
- Running `docker-compose -f docker-compose.yml -f logging.compose.override.yml up` brings up logging stack.

### Task 5: Add homelab log sinks (ntfy/Gotify + syslog)
**Goal**: Enable lightweight incident notifications and syslog output.

**Scope**
- Add log sink integrations for ntfy/Gotify.
- Add syslog output configuration for log forwarding.

**Acceptance Criteria**
- Logs can be delivered to ntfy/Gotify and a syslog server.

## Alerting Chains & Escalation

### Task 6: Pluggable alert destinations (Email, Chat, Ops)
**Goal**: Provide multiple alert notification backends.

**Scope**
- Email via SMTP.
- Chat: Discord, Slack, Matrix, Telegram.
- Ops: PagerDuty and Opsgenie (basic integration).

**Acceptance Criteria**
- Each destination can be configured via environment variables.
- Basic test event can be sent to each destination.

### Task 7: Escalation policy engine (YAML-based)
**Goal**: Define escalation rules in YAML.

**Scope**
- Support `match` conditions (severity, tags).
- Support `notify` targets and `escalate_after`.
- Support multiple policies.

**Acceptance Criteria**
- Policies are parsed and applied to outgoing alerts.

### Task 8: Quiet hours + noise controls
**Goal**: Prevent alert storms and allow scheduled suppression.

**Scope**
- Quiet hours schedule.
- Per-service and per-severity rate limits.
- Deduplication by incident fingerprint.

**Acceptance Criteria**
- Alerts are suppressed during quiet hours.
- Rate limiting and dedupe prevent noisy alert loops.

## Naming & Conceptual Clarity

### Task 9: Unify branding across README, UI, compose
**Goal**: Standardize on a primary brand and apply it consistently.

**Scope**
- Update README to use the primary brand (e.g., “Wingman: Homelab Copilot”).
- Update UI titles.
- Update docker-compose service names.

**Acceptance Criteria**
- Brand name is consistent across docs/UI/compose.

### Task 10: Add phase docs for observability + incident engine
**Goal**: Create short docs for phases to clarify goals and status.

**Scope**
- Add `docs/phase1-observability.md`.
- Add `docs/phase3-incident-engine.md`.
- Include goals, data flows, config examples, status checklist.

**Acceptance Criteria**
- Both phase docs exist and follow the specified template.

### Task 11: Standardize adapter naming + documentation
**Goal**: Ensure adapter naming consistency and consolidated env var docs.

**Scope**
- Standardize adapter naming convention (`adapter-<target>`).
- Add `docs/adapters.md` listing env vars, auth methods, examples.

**Acceptance Criteria**
- Adapter naming conventions documented.
- Env var table present with examples.
