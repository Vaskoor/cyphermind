<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11%2B-blue?style=for-the-badge&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/Next.js-14-black?style=for-the-badge&logo=next.js" alt="Next.js">
  <img src="https://img.shields.io/badge/FastAPI-Backend-009688?style=for-the-badge&logo=fastapi" alt="FastAPI">
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License">
  <img src="https://img.shields.io/badge/Status-Active-success?style=for-the-badge" alt="Status">
</p>

<h1 align="center">🛡️ CypherMind</h1>

<h3 align="center">
Self-Learning AI Penetration Testing Copilot
</h3>

<p align="center">
Autonomous multi-agent security testing framework powered by Q-learning, Hybrid RAG, Taint Analysis, and Red vs Blue Self-Play.
</p>

---

# 🚀 Overview

**CypherMind** is an advanced AI-powered penetration testing copilot designed to assist security researchers, bug bounty hunters, and red teams.

Unlike traditional AI assistants, CypherMind continuously improves its decision-making using:

- Q-Learning orchestration
- Experience replay
- Hybrid Retrieval-Augmented Generation (RAG)
- Taint-flow analysis
- Adversarial Red vs Blue self-play

The system learns from previous engagements and stores knowledge without requiring expensive LLM retraining.

---

# ✨ Features

## 🎯 Autonomous Bug Bounty Copilot

Implements a complete multi-stage security assessment methodology including:

- Reconnaissance
- Enumeration
- Vulnerability Discovery
- Exploitation
- Validation
- Reporting

Supports integration with:

- Subfinder
- Httpx
- Nuclei
- FFUF
- Waybackurls
- Katana
- Amass
- Gau
- Assetfinder
- Custom tools

---

## 🤖 Multi-Agent Architecture

CypherMind uses specialized agents:

| Agent | Responsibility |
|---------|---------------|
| Recon Agent | Asset discovery and enumeration |
| SAST Agent | Static code analysis |
| Exploit Agent | Vulnerability validation |
| Post-Exploit Agent | Impact assessment |
| Knowledge Agent | RAG-based retrieval |
| Self-Play Agent | Adversarial training |

Agents are orchestrated through:

- ε-Greedy Q-Learning
- Bradley-Terry preference learning
- Experience replay memory

---

## 🧠 Hybrid RAG Knowledge Base

Combines multiple retrieval strategies:

- ChromaDB Vector Search
- BM25 Keyword Search
- Cross-Encoder Re-ranking
- Local Embedding Models

Benefits:

- Better retrieval quality
- Faster vulnerability research
- Knowledge persistence across engagements

---

## 🔍 Taint Analysis Engine

Graph-based taint tracking using NetworkX.

Capabilities:

- Source-to-sink tracking
- Data-flow analysis
- Injection vulnerability discovery
- Extensible language support

Current focus:

- Python

Future support:

- JavaScript
- TypeScript
- Go
- Java

---

## ⚔️ Red vs Blue Self-Play

CypherMind continuously trains itself through adversarial simulations.

### Red Team

- Generates attacks
- Creates exploit chains
- Discovers bypasses

### Blue Team

- Detects vulnerabilities
- Creates mitigations
- Evaluates exploitability

Novel findings are automatically stored inside the RAG knowledge base.

---

## 📈 Continuous Learning

CypherMind becomes smarter over time through:

- Attack memory
- Reinforcement learning
- Experience replay
- Knowledge ingestion
- Agent performance scoring

No LLM fine-tuning required.

---

## 🎓 Optional Fine-Tuning

For teams requiring customized models:

- Export datasets in OpenAI JSONL format
- Train external models
- Dynamically enable or disable fine-tuned models
- Route specific agent roles to custom models

---

## ⚡ Real-Time Event Streaming

Live updates using WebSockets:

- Agent activity
- Tool execution
- Vulnerability findings
- Hunt progress
- Self-play sessions

---

## 🎨 Modern Web Dashboard

Built with Next.js and Tailwind CSS.

Features:

- Security Dashboard
- Bug Bounty Hunts
- Knowledge Explorer
- Engagement Management
- Reports
- AI Chat Interface
- Live Event Feed

---

# 🏗️ System Architecture

```text
┌───────────────────────────────────────────────────────────────┐
│                    Next.js Frontend (3000)                   │
│                                                               │
│ Dashboard │ Engagements │ Reports │ Chat │ Knowledge Base    │
└───────────────────────┬───────────────────────────────────────┘
                        │
                        │ HTTP / WebSocket
                        ▼
┌───────────────────────────────────────────────────────────────┐
│                     FastAPI Backend (8000)                   │
│                                                               │
│  ┌─────────────┐   ┌─────────────┐   ┌────────────────────┐  │
│  │ API Layer   │   │ Orchestrator│   │ Bug Bounty Agent  │  │
│  └─────────────┘   └─────────────┘   └────────────────────┘  │
│                                                               │
│  ┌─────────────┐   ┌─────────────┐   ┌────────────────────┐  │
│  │ Hybrid RAG  │   │ Self-Play   │   │ Fine-Tuning Module │  │
│  └─────────────┘   └─────────────┘   └────────────────────┘  │
│                                                               │
│  ┌─────────────┐   ┌─────────────┐   ┌────────────────────┐  │
│  │ LLM Router  │   │ Tool Engine │   │ Data Layer         │  │
│  └─────────────┘   └─────────────┘   └────────────────────┘  │
└───────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌───────────────────────────────────────────────────────────────┐
│                        Storage Layer                          │
│                                                               │
│ SQLite │ ChromaDB │ Q-Tables │ Attack Memory │ Reports       │
└───────────────────────────────────────────────────────────────┘
```

---

# 📂 Project Structure

```text
cyphermind/
│
├── backend/
│   ├── app/
│   ├── agents/
│   ├── services/
│   ├── rag/
│   ├── selfplay/
│   └── api/
│
├── frontend/
│   ├── app/
│   ├── components/
│   ├── hooks/
│   └── lib/
│
├── data/
│   ├── chroma/
│   ├── memory/
│   └── reports/
│
├── tests/
│
├── scripts/
│
├── docs/
│
└── .env.example
```

---

# 🚀 Quick Start

## Prerequisites

- Python 3.11+
- Node.js 18+
- npm
- Git

Optional tools:

```bash
subfinder
httpx
nuclei
ffuf
katana
gau
amass
```

---

## Installation

```bash
git clone https://github.com/yourusername/cyphermind.git

cd cyphermind

bash scripts/install.sh

cp .env.example .env
```

Configure API keys inside `.env`.

Then start the platform:

```bash
bash scripts/start.sh
```

---

## Access

| Service | URL |
|----------|------|
| Frontend | http://localhost:3000 |
| Backend | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |

---

# 🔧 Manual Startup

## Backend

```bash
cd backend

source .venv/bin/activate

export PYTHONPATH=.

uvicorn app.main:app --reload --port 8000
```

---

## Frontend

```bash
cd frontend

npm install

npm run dev
```

---

# ⚙️ Configuration

Example `.env`

```env
# Default LLM Provider
LLM_DEFAULT_PROVIDER=nvidia

# NVIDIA NIM
NVIDIA_API_KEY=nvapi-xxxxxxxx

# Grok
GROK_API_KEY=gsk-xxxxxxxx

# Routing
LLM_PROVIDER_BUG_BOUNTY=nvidia
LLM_PROVIDER_SELFPLAY=grok

# Bug Bounty
BUG_BOUNTY_MAX_ITERATIONS=15
RUN_METHODOLOGY_ON_HUNT=true

# Wordlists
DNS_WORDLIST=/path/to/dns-wordlist.txt
WEB_WORDLIST=/path/to/web-wordlist.txt

# Integrations
GITHUB_TOKEN=ghp_xxxxx
PDCP_API_KEY=xxxxx

# Fine-Tuning
FINETUNING_ENABLED=false
FINETUNING_MODEL_ID=ft:model-id
FINETUNING_BASE_PROVIDER=nvidia
FINETUNING_ROLES=bug_bounty,agent
```

See `.env.example` for all available options.

---

# 🧪 API Examples

## Start Bug Bounty Hunt

```bash
curl -X POST http://localhost:8000/api/v1/bug-bounty/hunt \
-H "Content-Type: application/json" \
-d '{
  "target_url":"https://example.com",
  "pipeline_mode":"full"
}'
```

---

## Query Knowledge Base

```bash
curl -X POST http://localhost:8000/api/v1/knowledge/query \
-H "Content-Type: application/json" \
-d '{
  "query":"SQL injection in Flask",
  "top_k":5
}'
```

---

## Launch Self-Play Arena

```bash
curl -X POST http://localhost:8000/api/v1/selfplay/start \
-H "Content-Type: application/json" \
-d '{
  "target_code":"import os; os.system(request.args.get(\"cmd\"))",
  "max_rounds":5
}'
```

---

## Enable Fine-Tuned Model

```bash
curl -X POST http://localhost:8000/api/v1/finetuning/config \
-H "Content-Type: application/json" \
-d '{
  "model_id":"ft:your-model-id",
  "base_provider":"nvidia"
}'
```

```bash
curl -X POST http://localhost:8000/api/v1/finetuning/toggle \
-d '{"enabled":true}'
```

---

# 🧪 Testing

```bash
cd backend

source .venv/bin/activate

export PYTHONPATH=.

pytest ../tests -v
```

---

# 🛠️ Technology Stack

| Layer | Technology |
|---------|-----------|
| Backend | Python 3.13, FastAPI, Uvicorn |
| Frontend | Next.js 14, React, TypeScript |
| Styling | Tailwind CSS |
| Database | SQLite, SQLAlchemy |
| Vector Store | ChromaDB |
| Embeddings | Sentence Transformers |
| LLM Providers | NVIDIA NIM, Grok, OpenAI, OpenRouter |
| Analysis | NetworkX, Tree-Sitter |
| Machine Learning | Scikit-Learn, SciPy |
| Authentication | Python-JOSE, Passlib |
| Testing | Pytest, Pytest-Asyncio |

---

# 📊 Roadmap

## Phase 1
- [x] Multi-Agent Framework
- [x] Hybrid RAG
- [x] Bug Bounty Pipeline
- [x] Web Dashboard

## Phase 2
- [ ] Multi-Language Taint Analysis
- [ ] Distributed Agent Execution
- [ ] Knowledge Graph Integration
- [ ] Automated Report Generation

## Phase 3
- [ ] Autonomous Security Research Agent
- [ ] Multi-Target Campaigns
- [ ] Federated Learning
- [ ] Enterprise Collaboration Features

---

# 🤝 Contributing

Contributions are welcome.

1. Fork the repository
2. Create a feature branch
3. Commit changes
4. Submit a Pull Request

For major changes, please open an issue first to discuss the proposal.

---

# 📄 License

This project is licensed under the MIT License.

See the `LICENSE` file for details.

---

# 🙏 Acknowledgements

- ProjectDiscovery
- OWASP Community
- ChromaDB
- FastAPI
- Next.js
- Open Source Security Researchers

---

<p align="center">
  <strong>Built for Security Researchers, Bug Bounty Hunters, and AI Security Engineers.</strong>
</p>

<p align="center">
  ⭐ Star the repository if you find CypherMind useful.
</p>