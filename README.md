# Homelab Copilot

> Privacy-forward infrastructure copilot for homelabs

[![Phase](https://img.shields.io/badge/Phase-0%20Scaffold-blue)](./homelab_copilot_build_design_doc_for_ide.md)

## Overview

Homelab Copilot observes your Proxmox + Docker infrastructure, explains incidents using a narrative layer, and guides remediation via a policy-enforced control plane—all while keeping your raw logs private.

### Key Principles

- **Cloud-first reasoning** via user API keys; **local fallback** for classification/summarization
- **No raw logs sent to cloud models** — only distilled summaries and RAG context
- **No autonomous destructive actions** — Guide mode only (user approves every step)

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Node.js 20+ (for local development)
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
   - Backend API: http://localhost:3001
   - Qdrant Dashboard: http://localhost:6333/dashboard

### Development

```bash
# Install dependencies
npm install

# Run backend + frontend in dev mode
npm run dev

# Run backend tests
npm run test -w backend

# Database migrations
cd backend && npx prisma migrate dev
```

## Project Structure

```
Wingman/
├── backend/           # Node.js/Express API
│   ├── prisma/        # Database schema & migrations
│   └── src/           # Application source
├── frontend/          # Next.js dashboard
│   └── src/app/       # App router pages
├── infra/             # Infrastructure configs
│   └── setup.sh       # Interactive setup wizard
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
