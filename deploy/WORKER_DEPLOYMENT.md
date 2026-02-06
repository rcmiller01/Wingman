# Multi-Site Worker Deployment Guide

## Overview

This guide explains how to deploy workers to multiple sites using the Phase 2 multi-site architecture.

## Quick Start

### 1. Deploy Workers Using Docker Compose

```bash
# From the project root
cd deploy
docker-compose -f worker-compose.yml up -d
```

This will start 3 workers across 3 different sites:
- `worker-site-a-01` - Site A (with Docker capabilities)
- `worker-site-b-01` - Site B (with Docker capabilities)
- `worker-site-c-01` - Site C (no Docker capabilities)

### 2. Verify Workers Are Running

```bash
docker-compose -f worker-compose.yml ps
```

### 3. Check Worker Logs

```bash
# View logs for a specific worker
docker-compose -f worker-compose.yml logs -f worker-site-a

# View logs for all workers
docker-compose -f worker-compose.yml logs -f
```

---

## Configuration

### Environment Variables

All worker settings can be configured via environment variables with the `WORKER_` prefix:

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `WORKER_ID` | Unique worker identifier | `worker-<random>` | `worker-site-a-01` |
| `WORKER_SITE` | Site name for this worker | `default` | `site-a` |
| `WORKER_CONTROL_PLANE_URL` | Control plane API URL | `http://localhost:8000` | `http://backend:8000` |
| `WORKER_POLL_INTERVAL_SECONDS` | Task polling interval | `5.0` | `10.0` |
| `WORKER_HEARTBEAT_INTERVAL_SECONDS` | Heartbeat interval | `30.0` | `60.0` |
| `WORKER_OFFLINE_DIR` | Offline buffer directory | `./offline` | `/app/offline` |
| `WORKER_CAPABILITIES` | Worker capabilities (JSON) | `{}` | `{"docker": true}` |

### Example: Custom Worker Configuration

```yaml
services:
  my-custom-worker:
    build:
      context: ../backend
      dockerfile: worker/Dockerfile
    environment:
      - WORKER_ID=my-worker-01
      - WORKER_SITE=my-site
      - WORKER_CONTROL_PLANE_URL=http://backend:8000
      - WORKER_POLL_INTERVAL_SECONDS=10
      - WORKER_HEARTBEAT_INTERVAL_SECONDS=60
      - WORKER_CAPABILITIES={"docker": true, "gpu": false}
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - my-worker-offline:/app/offline
    restart: unless-stopped
```

---

## Worker Capabilities

Workers can declare capabilities that are used for task routing. Common capabilities:

- **`docker`**: Can execute Docker-based tasks
- **`gpu`**: Has GPU access
- **`network_access`**: Can make external network calls
- **`privileged`**: Can run privileged operations

### Declaring Capabilities

**Via Environment Variable**:
```bash
WORKER_CAPABILITIES='{"docker": true, "gpu": true}' python -m worker.main
```

**Via Docker Compose**:
```yaml
environment:
  - WORKER_CAPABILITIES={"docker": true, "gpu": true}
```

---

## Deployment Scenarios

### Scenario 1: Home Lab + Remote Datacenter

Deploy one worker in your home lab and one in a remote datacenter:

```yaml
services:
  worker-home:
    environment:
      - WORKER_ID=worker-home-01
      - WORKER_SITE=home-lab
      - WORKER_CONTROL_PLANE_URL=http://backend:8000
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock

  worker-datacenter:
    environment:
      - WORKER_ID=worker-dc-01
      - WORKER_SITE=datacenter-1
      - WORKER_CONTROL_PLANE_URL=http://backend:8000
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
```

### Scenario 2: Cloud + Edge Workers

Deploy workers in the cloud and at edge locations:

```yaml
services:
  worker-cloud:
    environment:
      - WORKER_ID=worker-cloud-01
      - WORKER_SITE=aws-us-east-1
      - WORKER_CAPABILITIES={"docker": false, "network_access": true}

  worker-edge:
    environment:
      - WORKER_ID=worker-edge-01
      - WORKER_SITE=edge-location-1
      - WORKER_CAPABILITIES={"docker": true, "network_access": false}
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
```

### Scenario 3: Multiple Workers Per Site

Run multiple workers at the same site for load balancing:

```yaml
services:
  worker-site-a-01:
    environment:
      - WORKER_ID=worker-site-a-01
      - WORKER_SITE=site-a

  worker-site-a-02:
    environment:
      - WORKER_ID=worker-site-a-02
      - WORKER_SITE=site-a

  worker-site-a-03:
    environment:
      - WORKER_ID=worker-site-a-03
      - WORKER_SITE=site-a
```

---

## Offline Buffer

Workers automatically buffer results when the control plane is unreachable. The offline buffer:

- **Persists to disk** in the `WORKER_OFFLINE_DIR` directory
- **Automatically flushes** when connection is restored
- **Handles conflicts** using timestamp-based resolution

### Offline Buffer Volume

Always mount a volume for the offline buffer to ensure persistence across container restarts:

```yaml
volumes:
  - worker-offline:/app/offline
```

---

## Monitoring

### Check Worker Status

Workers send heartbeats to the control plane. Check worker status via the API:

```bash
curl http://localhost:8000/api/workers
```

### View Worker Tasks

```bash
curl http://localhost:8000/api/workers/worker-site-a-01/tasks
```

---

## Troubleshooting

### Worker Not Connecting

1. **Check control plane URL**:
   ```bash
   docker-compose logs worker-site-a | grep "control_plane_url"
   ```

2. **Verify network connectivity**:
   ```bash
   docker-compose exec worker-site-a curl http://backend:8000/health
   ```

3. **Check database connection**:
   ```bash
   docker-compose logs worker-site-a | grep "database"
   ```

### Worker Not Claiming Tasks

1. **Verify site name matches**:
   - Worker `site` must match task `site_name`

2. **Check capabilities**:
   - Worker must have required capabilities for the task

3. **View worker logs**:
   ```bash
   docker-compose logs -f worker-site-a
   ```

### Offline Buffer Not Flushing

1. **Check offline directory permissions**:
   ```bash
   docker-compose exec worker-site-a ls -la /app/offline
   ```

2. **Verify control plane is reachable**:
   ```bash
   docker-compose exec worker-site-a curl http://backend:8000/health
   ```

---

## Best Practices

1. **Use descriptive site names**: `home-lab`, `datacenter-1`, `aws-us-east-1`
2. **Set appropriate polling intervals**: Balance responsiveness vs. load
3. **Mount offline buffer volumes**: Ensure persistence across restarts
4. **Declare capabilities accurately**: Enable proper task routing
5. **Monitor worker heartbeats**: Detect offline workers quickly
6. **Use unique worker IDs**: Avoid conflicts across sites

---

## Next Steps

- **Component 2**: Multi-Worker Fact Aggregation
- **Component 3**: Offline Reconnection Sync
- **Component 4**: Cross-Site Incident Correlation
- **Component 5**: Worker-Scoped Execution Routing
