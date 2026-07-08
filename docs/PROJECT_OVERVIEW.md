# CypherMind — Project Overview & Architecture

A complete reference for what CypherMind is, what has been built, how the system works, and how to run it.

---

## Table of Contents

1. [What Is CypherMind?](#what-is-cyphermind)
2. [What Has Been Built](#what-has-been-built)
3. [System Architecture](#system-architecture)
4. [Directory Structure](#directory-structure)
5. [How to Install & Run](#how-to-install--run)
6. [Configuration](#configuration)
7. [Core Features](#core-features)
8. [Bug Bounty Methodology](#bug-bounty-methodology)
9. [LLM Provider Layer](#llm-provider-layer)
10. [Continuous Learning](#continuous-learning)
11. [Fine-Tuning Module](#fine-tuning-module)
12. [Reports](#reports)
13. [Frontend Pages](#frontend-pages)
14. [API Endpoints](#api-endpoints)
15. [Data Storage](#data-storage)
16. [Testing](#testing)
17. [Tech Stack](#tech-stack)

---

## What Is CypherMind?

**CypherMind** is a self-learning AI penetration testing copilot. It combines:

- Multi-agent orchestration with Q-learning
- Autonomous bug bounty hunting (13-phase Cybernote 2026 methodology)
- Hybrid RAG knowledge base
- Static analysis and taint graphs
- Red vs Blue self-play arena
- Continuous learning without retraining the LLM
- Optional fine-tuning for a custom-trained model

It runs locally with a FastAPI backend and Next.js frontend.

---

## What Has Been Built

### Phase 1 — Core Platform

| Component | Status | Description |
|-----------|--------|-------------|
| FastAPI backend | ✅ | REST API + WebSocket streaming |
| Next.js frontend | ✅ | Dashboard, engagements, chat, settings |
| SQLite database | ✅ | Engagements, findings, reports, attack memory |
| Multi-agent swarm | ✅ | Recon, SAST, Exploit, PostExploit agents |
| Q-learning orchestrator | ✅ | ε-greedy agent selection |
| Hybrid RAG | ✅ | ChromaDB + BM25 + cross-encoder reranking |
| Taint analysis | ✅ | NetworkX source-to-sink path finding |
| Self-play arena | ✅ | Red vs Blue with novel attack detection |
| Bradley-Terry preferences | ✅ | Human feedback on agent combos |

### Phase 2 — Bug Bounty Copilot

| Component | Status | Description |
|-----------|--------|-------------|
| BugBountyAgent | ✅ | LLM-driven autonomous hunter |
| 13-phase methodology | ✅ | Full Cybernote 2026 workflow |
| 30+ recon tools | ✅ | crt.sh, httpx, nuclei, wayback, ffuf, etc. |
| Wordlist management | ✅ | Upload + bundled fallbacks |
| Methodology runner | ✅ | Pre-hunt automated pipeline |
| Scope checking | ✅ | In-scope / out-of-scope validation |
| Attack memory tool | ✅ | `search_attack_memory` mid-hunt |

### Phase 3 — Learning Systems

| Component | Status | Description |
|-----------|--------|-------------|
| Attack memory | ✅ | Findings/payloads → SQLite + RAG |
| Self-play → RAG ingest | ✅ | Novel attacks auto-indexed |
| Phase Q-learning | ✅ | Best methodology phases per target |
| Policy selector | ✅ | Q-learning + Bradley-Terry for orchestrator |
| Learning hooks | ✅ | Post-hunt memory + Q-table updates |
| Learning API | ✅ | Summary, attack memory, phase policy |

### Phase 4 — LLM Provider Layer

| Component | Status | Description |
|-----------|--------|-------------|
| Pluggable providers | ✅ | NVIDIA/Kimi, Grok, OpenAI, OpenRouter, custom |
| Per-role routing | ✅ | Different model per task via `.env` |
| Settings API | ✅ | List providers, health checks |
| OpenAI-compatible client | ✅ | Single HTTP client for all providers |

### Phase 5 — Reports

| Component | Status | Description |
|-----------|--------|-------------|
| Recon reports | ✅ | Auto-generated from methodology pipeline |
| Agent reports | ✅ | Per-agent HTML with findings |
| Combined reports | ✅ | Full engagement summary |
| Reports UI | ✅ | View/download by type |
| DB persistence | ✅ | Reports stored with metadata |

### Phase 6 — Fine-Tuning (Optional)

| Component | Status | Description |
|-----------|--------|-------------|
| Dataset export | ✅ | JSONL from findings, memory, self-play |
| Enable/disable toggle | ✅ | Runtime + `.env` switch |
| Fine-tuned provider | ✅ | Separate from base LLM presets |
| Role routing | ✅ | Only configured roles use fine-tuned model |
| Fine-tuning API | ✅ | Toggle, config, build-dataset, health |

---

## System Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         Next.js Frontend (:3000)                         │
│  Dashboard │ Engagements │ Bug Bounty │ Reports │ Self-play │ Chat │ ... │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │ HTTP / WebSocket
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                        FastAPI Backend (:8000)                           │
│                                                                          │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐  ┌───────────────┐  │
│  │ API Routers │  │ Orchestrator │  │ Agent Loop  │  │ Methodology   │  │
│  │ (17 routes) │  │ (Q-learning) │  │ (tool call) │  │ Runner (13ph) │  │
│  └──────┬──────┘  └──────┬───────┘  └──────┬──────┘  └───────┬───────┘  │
│         │                │                 │                  │          │
│  ┌──────▼────────────────▼─────────────────▼──────────────────▼───────┐  │
│  │                         Agent Layer                               │  │
│  │  Recon │ SAST │ Exploit │ PostExploit │ BugBountyAgent           │  │
│  └──────┬───────────────────────────────────────────────────────────┘  │
│         │                                                                │
│  ┌──────▼──────┐  ┌──────────────┐  ┌─────────────┐  ┌─────────────┐  │
│  │ LLM Facade  │  │ RAG Service  │  │ Learning    │  │ Fine-tuning │  │
│  │ (role-based)│  │ Chroma+BM25  │  │ Hooks       │  │ (optional)  │  │
│  └──────┬──────┘  └──────────────┘  └─────────────┘  └─────────────┘  │
│         │                                                                │
│  ┌──────▼──────────────────────────────────────────────────────────┐  │
│  │                    LLM Provider Registry                         │  │
│  │  nvidia/kimi │ grok │ openai │ openrouter │ custom │ finetuned  │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────────┐  │
│  │ SQLite DB    │  │ Tool Registry│  │ Data (Q-tables, wordlists,   │  │
│  │              │  │ 30+ tools    │  │  reports, chromadb, datasets)│  │
│  └──────────────┘  └──────────────┘  └──────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘
```

### Request flow — Bug bounty hunt

```
User → POST /bug-bounty/hunt
  → BugBountyAgent.run()
    → Load attack memory context (RAG + SQLite)
    → Run pre-hunt methodology pipeline (13 phases, tools)
    → Run agent loop (LLM + tool calling, max N iterations)
      → LLM role: bug_bounty (or finetuned if enabled)
      → Tools: recon, scope check, report finding, search memory, etc.
    → Generate reports (recon + agent HTML)
    → Learning hooks (attack memory, phase Q-learning)
    → Optional: auto-export fine-tuning dataset
  → Return findings + reports
```

### Request flow — Engagement with orchestrator

```
User → POST /engagements + POST /agents/execute
  → EngagementOrchestrator
    → Q-learning selects agent combo (ε-greedy)
    → Bradley-Terry preferences influence selection
    → Run Recon → SAST → Exploit → PostExploit in sequence
    → WebSocket streams live events
    → Findings stored in DB
```

---

## Directory Structure

```
cyphermind/
├── backend/
│   └── app/
│       ├── main.py                 # FastAPI entry point
│       ├── core/
│       │   └── config.py           # Settings from .env
│       ├── api/routers/            # 17 API route modules
│       ├── agents/                 # Recon, SAST, Exploit, PostExploit, BugBounty
│       ├── db/                     # SQLAlchemy + SQLite init/migrations
│       ├── models/                 # ORM models (engagement, finding, attack_memory, …)
│       ├── services/               # orchestrator, agent_loop, rag, reports, learning
│       ├── tools/                  # 30+ methodology + recon tools
│       ├── learning/               # Q-learning, phase Q-learning, policy selector
│       ├── llm/                    # Provider layer (registry, facade, presets)
│       └── finetuning/             # Optional fine-tuning module
├── frontend/
│   └── src/app/                    # Next.js pages
├── data/
│   ├── chromadb/                   # Vector store
│   ├── finetuning/datasets/        # Exported JSONL training files
│   ├── knowledge/                  # Methodology docs for RAG
│   ├── wordlists/                  # Bundled DNS/web wordlists
│   ├── reports/                    # Generated HTML reports
│   ├── phase_q_table.json          # Learned methodology phase policy
│   └── q_table.json                # Agent orchestrator Q-table
├── docs/
│   ├── PROJECT_OVERVIEW.md         # This file
│   └── FINE_TUNING_GUIDE.md        # Fine-tuning how-to
├── scripts/
│   ├── install.sh                  # One-command setup
│   └── start.sh                    # Start backend + frontend
├── tests/unit/                     # 31 pytest tests
├── .env.example                    # Environment template
└── README.md                       # Quick start
```

---

## How to Install & Run

### Requirements

- Python 3.11+ (3.13 tested)
- Node.js 18+ and npm
- Optional: external tools for full methodology (subfinder, httpx, nuclei, ffuf, etc.)

### Quick start (recommended)

```bash
cd ~/cyphermind
bash scripts/install.sh
cp .env.example .env
# Edit .env — add at minimum NVIDIA_API_KEY or GROK_API_KEY
bash scripts/start.sh
```

Open:
- **Frontend:** http://localhost:3000
- **API docs:** http://localhost:8000/docs
- **Health:** http://localhost:8000/health

### Manual start (two terminals)

**Terminal 1 — Backend:**
```bash
cd ~/cyphermind/backend
source .venv/bin/activate
export PYTHONPATH=.
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd ~/cyphermind/frontend
npm run dev
```

### First-time `.env` setup

```bash
cp .env.example .env
```

Minimum required:
```bash
NVIDIA_API_KEY=your_key_here
LLM_DEFAULT_PROVIDER=nvidia
```

For bug bounty + self-play with different models:
```bash
NVIDIA_API_KEY=...
GROK_API_KEY=...
LLM_PROVIDER_BUG_BOUNTY=nvidia
LLM_PROVIDER_SELFPLAY=grok
```

### Logs (when using start.sh)

```
data/backend.log
data/frontend.log
```

---

## Configuration

All configuration is via `.env` at the project root. Key sections:

### LLM providers

```bash
LLM_DEFAULT_PROVIDER=nvidia
NVIDIA_API_KEY=...
GROK_API_KEY=...
LLM_PROVIDER_BUG_BOUNTY=nvidia
LLM_PROVIDER_SELFPLAY=grok
LLM_PROVIDER_RAG=nvidia
LLM_PROVIDER_CHAT=grok
```

### Bug bounty

```bash
BUG_BOUNTY_MAX_ITERATIONS=15
RUN_METHODOLOGY_ON_HUNT=true
METHODOLOGY_PIPELINE_MODE=default   # or "full"
DNS_WORDLIST=/path/to/dns-wordlist.txt
WEB_WORDLIST=/path/to/web-wordlist.txt
GITHUB_TOKEN=ghp_...                  # Phase 10 GitHub recon
PDCP_API_KEY=...                      # ProjectDiscovery Chaos
```

### Fine-tuning (disabled by default)

```bash
FINETUNING_ENABLED=false
FINETUNING_MODEL_ID=ft:your-model-id
FINETUNING_BASE_PROVIDER=nvidia
FINETUNING_ROLES=bug_bounty,agent
```

See [FINE_TUNING_GUIDE.md](./FINE_TUNING_GUIDE.md) for the full fine-tuning workflow.

### Embeddings (local, not via LLM API)

```bash
EMBEDDING_MODEL=all-MiniLM-L6-v2
```

---

## Core Features

### 1. Multi-Agent Orchestration

The orchestrator uses **ε-greedy Q-learning** to select which agents to run (Recon, SAST, Exploit, PostExploit) based on target type and past success. **Bradley-Terry** preference learning lets you rate agent combos to influence future selection.

- Q-table: `data/q_table.json`
- API: `POST /api/v1/agents/execute`

### 2. Hybrid RAG Knowledge Base

Combines:
- **ChromaDB** vector search (semantic)
- **BM25** keyword search
- **Cross-encoder reranking** for best results

Used for methodology enrichment, attack memory retrieval, and knowledge queries.

- API: `POST /api/v1/knowledge/query`
- UI: http://localhost:3000/knowledge

### 3. Taint Analysis

NetworkX-based static analysis finds data flow from sources (user input) to sinks (SQL, exec, etc.) in Python code.

- Sample: `data/samples/vulnerable_app.py`

### 4. Self-Play Arena

Red team vs Blue team LLM agents compete on vulnerable code. Novel red-team attacks are auto-ingested into RAG and attack memory.

- API: `POST /api/v1/selfplay/start`
- UI: http://localhost:3000/selfplay

### 5. Real-Time WebSocket Events

Live agent progress streamed to the frontend during engagements.

- `WS /ws/engagements/{id}`

---

## Bug Bounty Methodology

The **BugBountyAgent** implements the full **Cybernote 2026** 13-phase workflow:

| Phase | Name | Tools |
|-------|------|-------|
| 1 | Passive subdomain enum | crt.sh, subfinder, chaos |
| 2 | DNS bruteforce | ffuf, dns wordlist |
| 3 | ASN / infrastructure | whois, ASN lookup |
| 4–5 | Alive host detection | httpx |
| 6 | VHOST enumeration | ffuf |
| 7 | URL discovery | wayback, katana, gau |
| 8 | JS secret extraction | linkfinder, regex |
| 9 | Directory fuzz | ffuf, web wordlist |
| 10 | GitHub recon | GitHub API |
| 11–12 | Port scan + nuclei | nmap, nuclei templates |
| 13 | Subdomain takeover | DNS checks |

**Pipeline modes:**
- `default` — core phases (faster)
- `full` — all 13 phases

**How to run:**
```bash
# API
curl -X POST http://localhost:8000/api/v1/bug-bounty/hunt \
  -H "Content-Type: application/json" \
  -d '{"target_url": "https://target.com", "pipeline_mode": "full"}'

# UI
http://localhost:3000/bug-bounty
```

**Methodology reference:**
```bash
curl http://localhost:8000/api/v1/bug-bounty/methodology
```

---

## LLM Provider Layer

All LLM calls go through `backend/app/llm/`. Change providers in `.env` only — no code edits.

### Available presets

| Name | API | Default model |
|------|-----|---------------|
| `nvidia` / `kimi` | integrate.api.nvidia.com | moonshotai/kimi-k2.6 |
| `grok` | api.x.ai | grok-2-latest |
| `openai` | api.openai.com | gpt-4o |
| `openrouter` | openrouter.ai | claude-sonnet-4 |
| `custom` | your URL | configurable |

### Per-role routing

| Role | Env var | Typical use |
|------|---------|-------------|
| `bug_bounty` | `LLM_PROVIDER_BUG_BOUNTY` | Autonomous hunting |
| `selfplay` | `LLM_PROVIDER_SELFPLAY` | Red/Blue arena |
| `selfplay_red` | `LLM_PROVIDER_SELFPLAY_RED` | Red team |
| `selfplay_blue` | `LLM_PROVIDER_SELFPLAY_BLUE` | Blue team |
| `rag` | `LLM_PROVIDER_RAG` | RAG enrichment |
| `chat` | `LLM_PROVIDER_CHAT` | Chat UI |
| `agent` | `LLM_PROVIDER_AGENT` | General agents |

### Architecture

```
app/llm/
  base.py          — provider presets + ProviderConfig
  registry.py      — resolve name/role → provider instance
  openai_compat.py — OpenAI-compatible HTTP client
  facade.py        — chat_completion_raw(), chat_completion(role=...)
```

Check provider health:
```bash
curl http://localhost:8000/api/v1/settings/llm-providers/list
curl http://localhost:8000/api/v1/settings/llm
```

---

## Continuous Learning

CypherMind gets smarter over time **without retraining the LLM**:

| System | What it learns | Stored in |
|--------|----------------|-----------|
| **Attack Memory** | Findings, payloads, tool sequences | SQLite + RAG |
| **Self-play → RAG** | Novel red-team attack patterns | Auto-ingested |
| **Phase Q-Learning** | Best methodology phases per target type | `data/phase_q_table.json` |
| **Agent Q-Learning** | Best agent combos | `data/q_table.json` |
| **Bradley-Terry** | Human preference on agent combos | Influences orchestrator |

### What happens after each bug bounty hunt

1. Past attack patterns loaded into agent prompt
2. Q-learned methodology phases selected (not static defaults)
3. Findings + successful tool chains stored for next hunt
4. Phase Q-values updated based on results

### API

```bash
curl http://localhost:8000/api/v1/learning/summary
curl http://localhost:8000/api/v1/learning/attack-memory
curl http://localhost:8000/api/v1/learning/phase-policy
```

### Mid-hunt tool

The agent can call `search_attack_memory` to query learned patterns during a hunt.

---

## Fine-Tuning Module

A **separate, optional** module for using a custom fine-tuned model. Disabled by default.

| Feature | Description |
|---------|-------------|
| Dataset export | JSONL from findings, attack memory, self-play |
| Enable/disable | Runtime toggle + `.env` switch |
| Role routing | Only `bug_bounty` + `agent` by default |
| Separate provider | Does not affect base Kimi/Grok routing |

**Full guide:** [FINE_TUNING_GUIDE.md](./FINE_TUNING_GUIDE.md)

---

## Reports

Reports are auto-generated after hunts and agent runs:

| Type | Description |
|------|-------------|
| `recon` | Methodology pipeline results (subdomains, URLs, ports) |
| `agent` | Per-agent findings with severity breakdown |
| `combined` | Full engagement summary |
| `executive` | High-level summary |

- UI: http://localhost:3000/reports
- API: `GET /api/v1/reports`
- Files: `data/reports/`

---

## Frontend Pages

| URL | Page |
|-----|------|
| `/` | Home |
| `/dashboard` | Metrics and stats |
| `/engagements` | List engagements |
| `/engagements/new` | Create engagement |
| `/engagements/[id]` | Live engagement view |
| `/bug-bounty` | Autonomous bug bounty hunts |
| `/reports` | View/download reports |
| `/selfplay` | Red vs Blue arena |
| `/knowledge` | RAG knowledge base |
| `/chat` | LLM chat interface |
| `/settings` | LLM provider settings |
| `/login` | Authentication |

---

## API Endpoints

### Health & Dashboard

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Service health |
| `GET` | `/api/v1/dashboard/stats` | Dashboard metrics |

### Engagements & Agents

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/engagements` | Create engagement |
| `GET` | `/api/v1/engagements` | List engagements |
| `POST` | `/api/v1/agents/execute` | Run agents (RL or manual) |
| `WS` | `/ws/engagements/{id}` | Live agent events |

### Bug Bounty

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/bug-bounty/hunt` | Start autonomous hunt |
| `GET` | `/api/v1/bug-bounty/methodology` | 13-phase methodology |
| `GET` | `/api/v1/wordlists/status` | Wordlist status |
| `POST` | `/api/v1/wordlists/upload/dns` | Upload DNS wordlist |

### Knowledge & Learning

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/knowledge/query` | Hybrid RAG search |
| `GET` | `/api/v1/learning/summary` | Learning stats |
| `GET` | `/api/v1/learning/attack-memory` | Attack memory entries |
| `GET` | `/api/v1/learning/phase-policy` | Phase Q-learning policy |

### Self-Play

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/selfplay/start` | Start Red vs Blue game |

### Reports

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/reports` | List reports |
| `GET` | `/api/v1/reports/{id}` | Get report |
| `GET` | `/api/v1/reports/{id}/download` | Download HTML |

### LLM Settings

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/settings/llm-providers/list` | All presets + role mappings |
| `GET` | `/api/v1/settings/llm` | Default provider health |
| `GET` | `/api/v1/settings/llm/{provider}` | Specific provider health |

### Fine-Tuning

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/finetuning/status` | Module status |
| `POST` | `/api/v1/finetuning/toggle` | Enable/disable |
| `POST` | `/api/v1/finetuning/config` | Update model ID, roles |
| `POST` | `/api/v1/finetuning/build-dataset` | Export training JSONL |
| `GET` | `/api/v1/finetuning/health` | Test fine-tuned model |

Full interactive docs: http://localhost:8000/docs

---

## Data Storage

| Location | Contents |
|----------|----------|
| `data/cyphermind.db` | SQLite — engagements, findings, reports, attack memory |
| `data/chromadb/` | Vector embeddings for RAG |
| `data/q_table.json` | Agent orchestrator Q-learning table |
| `data/phase_q_table.json` | Methodology phase Q-learning table |
| `data/reports/` | Generated HTML reports |
| `data/finetuning/datasets/` | Exported JSONL training files |
| `data/finetuning/runtime_state.json` | Fine-tuning enable/disable state |
| `data/wordlists/` | Bundled DNS/web wordlists |
| `data/knowledge/` | Methodology and knowledge docs |

---

## Testing

```bash
cd ~/cyphermind/backend
source .venv/bin/activate
export PYTHONPATH=.
pytest ../tests -v
```

**31 tests** covering:
- LLM provider resolution and role mapping
- Fine-tuning enable/disable and role routing
- Learning systems (attack memory, phase Q-learning)
- Report generation
- Methodology tools (scope check, wordlists, CT lookup)
- Taint graph analysis

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.13, FastAPI, Uvicorn |
| Frontend | Next.js, React, TypeScript |
| Database | SQLite + SQLAlchemy (async) |
| Vector store | ChromaDB |
| Embeddings | sentence-transformers (local) |
| LLM | OpenAI-compatible APIs (NVIDIA, Grok, OpenAI, etc.) |
| ML | scikit-learn, scipy, NetworkX |
| Code analysis | tree-sitter |
| Auth | python-jose, passlib |
| Testing | pytest, pytest-asyncio |

---

## Quick Reference

```bash
# Install
bash scripts/install.sh && cp .env.example .env

# Start
bash scripts/start.sh

# Run a hunt
curl -X POST localhost:8000/api/v1/bug-bounty/hunt \
  -H "Content-Type: application/json" \
  -d '{"target_url": "https://example.com"}'

# Check learning stats
curl localhost:8000/api/v1/learning/summary

# Build fine-tuning dataset
curl -X POST localhost:8000/api/v1/finetuning/build-dataset

# Run tests
cd backend && pytest ../tests -v
```

**Documentation:**
- [FINE_TUNING_GUIDE.md](./FINE_TUNING_GUIDE.md) — How to fine-tune and enable/disable
- [README.md](../README.md) — Quick start
- http://localhost:8000/docs — Interactive API reference
