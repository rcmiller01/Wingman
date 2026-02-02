# Observability & Logging

## OpenTelemetry

Set `OTEL_ENDPOINT` to point to your OTLP collector (for example `http://localhost:4317`).
The backend sets `OTEL_SERVICE_NAME` to label traces.

## Loki + Grafana (compose override)

Run the logging stack alongside Wingman:

```bash
docker-compose -f docker-compose.yml -f logging.compose.override.yml up
```

Point `OTEL_ENDPOINT` at `http://localhost:4317` to ship traces and logs to the local collector.

## Collector configurations

- `infra/otel-collector/otel-collector.loki.yaml`: ships logs to Loki.
- `infra/otel-collector/otel-collector.opensearch.yaml`: ships logs + traces to OpenSearch.

Update the collector configuration to match your target endpoints before running.

## Logging sinks

Configure optional log sinks via `.env`:

- `NTFY_URL` + `NTFY_TOPIC`
- `GOTIFY_URL` + `GOTIFY_TOKEN`
- `SYSLOG_HOST` + `SYSLOG_PORT`

Log sinks emit for `ERROR` and above by default.

## File log sources (opt-in)

File log ingestion is disabled by default. Enable it per service by creating a file log source and toggling `enabled=true`:

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

Use `PATCH /api/logs/file-sources/{id}` to update paths or change `enabled`, and `DELETE /api/logs/file-sources/{id}` to remove sources. File tailing is a no-op when all sources are disabled, but enabled file logs participate in the same retention and error signature extraction flow as container logs.
