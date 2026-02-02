# Homelab Copilot

> Privacy-forward infrastructure copilot for homelabs

[![Phase](https://img.shields.io/badge/Phase-0%20Scaffold-blue)](./homelab_copilot_build_design_doc_for_ide.md)

## Overview

Homelab Copilot is a privacy-forward infrastructure copilot for homelabs. It observes Proxmox and container infrastructure, synthesizes incident narratives, and proposes remediation steps via a policy-enforced control plane—while keeping raw logs private.

### Key Principles

- **Cloud-first reasoning** via user API keys; **local fallback** for always-on classification/summarization
- **No raw logs sent to cloud models** — only distilled summaries and RAG context
- **No autonomous destructive actions** — Guide/Assist modes require user approval

### Architecture at a Glance

1. **Intelligence Layer**
   - Cloud LLMs (OpenAI/Anthropic/OpenRouter) used on-demand.
   - Local LLM (Ollama) always on for classification/summarization/tool selection.
2. **Control Plane (Core)**
   - Builds Situations from facts/logs.
   - Proposes and validates plans.
   - Enforces Guide/Assist policies.
   - Generates todo steps and records audit/memory artifacts.
3. **Execution Layer**
   - Adapters for Proxmox, Docker/Podman, and planned automations.
4. **Persistent Stores**
   - PostgreSQL for facts, actions, incidents, and policy state.
   - Qdrant for RAG indexing (incident narratives and log summaries).

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Node.js 20+ (frontend development)
- Python 3.12+ (backend development)
- Ollama with a local model (e.g., `ollama pull qwen2.5:7b`)

### Setup

1. **Clone and configure:**
   ```bash
   git clone <repo-url>
   cd Wingman
   bash infra/setup.sh
   ```
   The setup wizard will prompt for your API keys and Proxmox credentials.

2. **Start the services:**
   ```bash
   docker compose up --build
   ```

3. **Access the dashboard:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - Qdrant Dashboard: http://localhost:6343/dashboard

### Development

```bash
# Install frontend dependencies
npm install

# Start the frontend (Next.js)
npm run dev:frontend

# Start the backend locally
cd backend
pip install -r requirements.txt
uvicorn homelab.main:app --reload --port 8000
```

```bash
# Initialize database tables (first run)
cd backend
python create_tables.py
```

## Project Structure

```
Wingman/
├── backend/           # Python/FastAPI control plane
│   ├── homelab/       # Application source
│   ├── alembic/       # Database migrations
│   └── create_tables.py
├── frontend/          # Next.js dashboard
│   └── src/app/       # App router pages
├── infra/             # Infrastructure configs
│   └── setup.sh       # Interactive setup wizard
├── docs/              # Observability + alerting docs
├── docker-compose.yml # Service orchestration
└── .env.example       # Environment template
```

## Phased Implementation

| Phase | Name | Status |
|-------|------|--------|
| 0 | Scaffold & Foundations | ✅ Current |
| 1 | Observability MVP | ⏳ Next |
| 2 | Logging MVP | ⏳ |
| 3 | Incident Engine | ⏳ |
| 4 | Control Plane (Guide Mode) | ⏳ |
| 5 | Memory Compression + RAG | ⏳ |

See [Build Design Doc](./homelab_copilot_build_design_doc_for_ide.md) for full specification.

## License

Private — See design doc for usage constraints.
