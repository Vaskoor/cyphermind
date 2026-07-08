# CypherMind Fine-Tuning Guide

This guide explains how to fine-tune a model for CypherMind, enable it when ready, and disable it anytime to fall back to base providers (Kimi, Grok, NVIDIA, etc.).

Fine-tuning is a **separate, optional module**. It does **not** replace continuous learning (attack memory, Q-learning, RAG). Those systems keep working with or without fine-tuning.

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Step 1 — Collect Training Data](#step-1--collect-training-data)
4. [Step 2 — Build the Dataset](#step-2--build-the-dataset)
5. [Step 3 — Train on Your Provider](#step-3--train-on-your-provider)
6. [Step 4 — Configure the Fine-Tuned Model](#step-4--configure-the-fine-tuned-model)
7. [Step 5 — Enable Fine-Tuning](#step-5--enable-fine-tuning)
8. [Step 6 — Verify It Works](#step-6--verify-it-works)
9. [Disable Fine-Tuning](#disable-fine-tuning)
10. [Configuration Reference](#configuration-reference)
11. [API Reference](#api-reference)
12. [Dataset Format](#dataset-format)
13. [Troubleshooting](#troubleshooting)

---

## Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     CypherMind Hunt Flow                        │
│  Bug bounty hunts → Findings + Attack Memory + Self-play        │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              POST /api/v1/finetuning/build-dataset              │
│  Exports JSONL → data/finetuning/datasets/cyphermind_train_*.jsonl │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│           External fine-tuning (OpenAI / NVIDIA / etc.)         │
│  Upload JSONL → Train → Receive model ID (e.g. ft:abc123)       │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  FINETUNING_MODEL_ID=ft:...  +  FINETUNING_ENABLED=true         │
│  Configured roles (bug_bounty, agent) route to fine-tuned model │
└─────────────────────────────────────────────────────────────────┘
```

**Default state:** Fine-tuning is **disabled**. All LLM roles use your normal `.env` providers.

---

## Prerequisites

- CypherMind installed and running (see [PROJECT_OVERVIEW.md](./PROJECT_OVERVIEW.md))
- At least one LLM provider configured (`NVIDIA_API_KEY`, `GROK_API_KEY`, etc.)
- Some hunt data to export (findings, attack memory, or self-play results)
- Access to a fine-tuning service that accepts **OpenAI chat JSONL** format

Supported base providers for fine-tuned inference:

| Base provider | Typical use |
|---------------|-------------|
| `nvidia` | Kimi via NVIDIA NIM |
| `openai` | OpenAI fine-tuned models |
| `grok` | xAI (if fine-tuning available) |
| `openrouter` | Routed fine-tuned endpoints |

The fine-tuned model uses the **same API base and key** as the base provider unless you override them.

---

## Step 1 — Collect Training Data

CypherMind builds training examples from three sources:

| Source | What it contains |
|--------|------------------|
| **Findings** | Reported vulnerabilities, descriptions, PoC payloads, CWE/CVE |
| **Attack Memory** | Learned exploit patterns, payloads, tool sequences |
| **Self-play (red team)** | Novel attack techniques from Red vs Blue games |

### How to accumulate data

1. **Run bug bounty hunts**
   ```bash
   curl -X POST http://localhost:8000/api/v1/bug-bounty/hunt \
     -H "Content-Type: application/json" \
     -d '{"target_url": "https://example.com", "pipeline_mode": "default"}'
   ```
   Or use the UI: http://localhost:3000/bug-bounty

2. **Run self-play sessions**
   - UI: http://localhost:3000/selfplay
   - API: `POST /api/v1/selfplay/start`

3. **Run engagement agents** — findings and attack memory are stored automatically after hunts.

The more high-quality findings and attack patterns you have, the better your fine-tuning dataset.

---

## Step 2 — Build the Dataset

### Via API (recommended)

```bash
curl -X POST http://localhost:8000/api/v1/finetuning/build-dataset \
  -H "Content-Type: application/json" \
  -d '{
    "include_findings": true,
    "include_memories": true,
    "include_selfplay": true,
    "max_samples": 2000
  }'
```

**Response example:**
```json
{
  "path": "/Users/you/cyphermind/data/finetuning/datasets/cyphermind_train_20260705_120000.jsonl",
  "filename": "cyphermind_train_20260705_120000.jsonl",
  "total_samples": 142,
  "created_at": "2026-07-05T12:00:00Z",
  "format": "openai_chat_jsonl"
}
```

### List existing datasets

```bash
curl http://localhost:8000/api/v1/finetuning/datasets
```

### Download a dataset

```bash
curl -O http://localhost:8000/api/v1/finetuning/datasets/cyphermind_train_20260705_120000.jsonl/download
```

### Auto-export after each hunt (optional)

Set in `.env`:
```bash
FINETUNING_AUTO_EXPORT=true
```

Or via API:
```bash
curl -X POST http://localhost:8000/api/v1/finetuning/config \
  -H "Content-Type: application/json" \
  -d '{"pipeline_auto_export": true}'
```

Datasets are saved to:
```
data/finetuning/datasets/cyphermind_train_YYYYMMDD_HHMMSS.jsonl
```

---

## Step 3 — Train on Your Provider

Upload the JSONL file to your provider's fine-tuning console. CypherMind does **not** run the training job itself — you train externally, then plug the resulting model ID back in.

### OpenAI

1. Go to https://platform.openai.com/finetune
2. Upload `cyphermind_train_*.jsonl`
3. Choose a base model (e.g. `gpt-4o-mini-2024-07-18`)
4. Start the job and wait for completion
5. Copy the model ID (e.g. `ft:gpt-4o-mini-2024-07-18:your-org:abc123`)

Set in `.env`:
```bash
FINETUNING_BASE_PROVIDER=openai
OPENAI_API_KEY=sk-...
FINETUNING_MODEL_ID=ft:gpt-4o-mini-2024-07-18:your-org:abc123
```

### NVIDIA NIM

1. Go to NVIDIA's fine-tuning / NIM portal (integrate.api.nvidia.com)
2. Upload the JSONL dataset
3. Fine-tune on your chosen base model (e.g. `moonshotai/kimi-k2.6`)
4. Copy the resulting model ID

Set in `.env`:
```bash
FINETUNING_BASE_PROVIDER=nvidia
NVIDIA_API_KEY=nvapi-...
FINETUNING_MODEL_ID=your-finetuned-model-id
```

### General tips

- Aim for **at least 50–100 quality examples** before training; more is better
- Remove or fix low-quality rows manually if needed (edit the JSONL)
- Keep validation split on the provider side if offered
- Note the exact model ID string — you will need it in the next step

---

## Step 4 — Configure the Fine-Tuned Model

### Option A — `.env` file (persistent)

Copy from `.env.example` and edit:

```bash
# Fine-tuning (disabled until you set a real model ID)
FINETUNING_ENABLED=false
FINETUNING_MODEL_ID=ft:your-actual-model-id-here
FINETUNING_BASE_PROVIDER=nvidia
FINETUNING_ROLES=bug_bounty,agent
FINETUNING_AUTO_EXPORT=false
FINETUNING_SUPPORTS_TOOLS=true

# Optional overrides (usually not needed)
# FINETUNING_API_BASE=https://integrate.api.nvidia.com/v1
# FINETUNING_API_KEY=your-key
```

### Option B — API (runtime, survives restarts)

```bash
curl -X POST http://localhost:8000/api/v1/finetuning/config \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": "ft:your-actual-model-id",
    "base_provider": "nvidia",
    "roles": ["bug_bounty", "agent"],
    "notes": "Trained on 500 hunt samples, July 2026"
  }'
```

Runtime state is stored in:
```
data/finetuning/runtime_state.json
```

---

## Step 5 — Enable Fine-Tuning

**Only enable after training is complete and you have a valid model ID.**

### Via `.env`

```bash
FINETUNING_ENABLED=true
```

Restart the backend after changing `.env`.

### Via API (no restart needed)

```bash
curl -X POST http://localhost:8000/api/v1/finetuning/toggle \
  -H "Content-Type: application/json" \
  -d '{"enabled": true}'
```

When enabled:
- Roles in `FINETUNING_ROLES` (default: `bug_bounty`, `agent`) use your fine-tuned model
- All other roles (`selfplay`, `rag`, `chat`, etc.) keep using their normal providers

Check which roles are routed where:
```bash
curl http://localhost:8000/api/v1/settings/llm-providers/list
```

You should see `"bug_bounty": "finetuned"` when active.

---

## Step 6 — Verify It Works

### Status check

```bash
curl http://localhost:8000/api/v1/finetuning/status
```

Expected when configured correctly:
```json
{
  "enabled": true,
  "configured": true,
  "model_id": "ft:your-model-id",
  "roles": ["bug_bounty", "agent"],
  "base_provider": "nvidia"
}
```

### Health check (sends a test prompt)

```bash
curl http://localhost:8000/api/v1/finetuning/health
```

Expected:
```json
{
  "online": true,
  "enabled": true,
  "provider": "finetuned",
  "model": "ft:your-model-id",
  "test_reply": "ok"
}
```

### Run a hunt with the fine-tuned model

```bash
curl -X POST http://localhost:8000/api/v1/bug-bounty/hunt \
  -H "Content-Type: application/json" \
  -d '{"target_url": "https://example.com"}'
```

The `bug_bounty` role will use your fine-tuned model for all LLM calls in that hunt.

---

## Disable Fine-Tuning

Disable instantly to fall back to Kimi/Grok/base models — no code changes.

### Via API

```bash
curl -X POST http://localhost:8000/api/v1/finetuning/toggle \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'
```

### Via `.env`

```bash
FINETUNING_ENABLED=false
```

Your model ID stays saved. Re-enable anytime with the toggle when you want to use it again.

---

## Configuration Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `FINETUNING_ENABLED` | `false` | Master switch — routes configured roles to fine-tuned model |
| `FINETUNING_MODEL_ID` | `""` | Your trained model ID from the provider |
| `FINETUNING_BASE_PROVIDER` | `nvidia` | Inherits API base + key from this preset |
| `FINETUNING_API_BASE` | *(inherits)* | Override API endpoint if needed |
| `FINETUNING_API_KEY` | *(inherits)* | Override API key if needed |
| `FINETUNING_ROLES` | `bug_bounty,agent` | Comma-separated roles that use fine-tuned model |
| `FINETUNING_AUTO_EXPORT` | `false` | Auto-build JSONL after each hunt |
| `FINETUNING_SUPPORTS_TOOLS` | `true` | Whether fine-tuned model supports tool calling |

### Role routing logic

```
Request for role "bug_bounty"
        │
        ▼
  FINETUNING_ENABLED?
    │           │
   yes          no
    │           │
    ▼           ▼
  role in     Use LLM_PROVIDER_BUG_BOUNTY
  FINETUNING_ROLES?   (e.g. nvidia / kimi)
    │           │
   yes          │
    │           │
    ▼           ▼
Use fine-tuned  Use base provider
model ID
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/finetuning/status` | Full module status |
| `GET` | `/api/v1/finetuning/health` | Test fine-tuned model connectivity |
| `POST` | `/api/v1/finetuning/toggle` | `{"enabled": true/false}` |
| `POST` | `/api/v1/finetuning/config` | Update model ID, roles, base provider |
| `POST` | `/api/v1/finetuning/build-dataset` | Export training JSONL |
| `GET` | `/api/v1/finetuning/datasets` | List exported datasets |
| `GET` | `/api/v1/finetuning/datasets/{filename}/download` | Download a dataset file |

Interactive docs: http://localhost:8000/docs

---

## Dataset Format

Each line in the JSONL file is one training example in **OpenAI chat format**:

```json
{
  "messages": [
    {
      "role": "system",
      "content": "You are CypherMind, an elite bug bounty hunter and penetration testing copilot. Find real vulnerabilities, explain exploitation, and provide PoC payloads."
    },
    {
      "role": "user",
      "content": "Analyze and report this security finding for a bug bounty program.\nTitle: SQL Injection in login\nSeverity hint: high"
    },
    {
      "role": "assistant",
      "content": "The login endpoint is vulnerable to SQL injection via the username parameter...\nPoC payload: admin' OR '1'='1\nCWE: CWE-89"
    }
  ]
}
```

Three example types are generated:

1. **Finding examples** — user asks to analyze a finding; assistant provides description + payload
2. **Attack memory examples** — user asks how to exploit a vuln type; assistant provides technique + payload
3. **Self-play examples** — user asks for attack technique; assistant provides red-team content

---

## Troubleshooting

### `configured: false` in status

- `FINETUNING_MODEL_ID` is empty or invalid
- API key for base provider is missing
- Fix: set model ID and ensure `NVIDIA_API_KEY` (or equivalent) is in `.env`

### `online: false` in health check

- Model ID does not exist or training job failed
- API base/key mismatch
- Fine-tuned model does not support the endpoint format
- Fix: verify model ID in provider console; try `FINETUNING_API_BASE` override

### Fine-tuning enabled but hunts still use Kimi/Grok

- Role not in `FINETUNING_ROLES` (default: `bug_bounty`, `agent`)
- Runtime state has `enabled: false` — check `data/finetuning/runtime_state.json`
- Fix: `POST /api/v1/finetuning/toggle {"enabled": true}`

### Dataset has 0 samples

- No findings in database yet — run some hunts first
- Attack memory empty — complete hunts with reported findings
- Fix: run hunts, then rebuild dataset

### Tool calling fails with fine-tuned model

Some fine-tuned models do not support function/tool calling. Set:
```bash
FINETUNING_SUPPORTS_TOOLS=false
```

### Want to retrain with more data

1. Run more hunts
2. `POST /api/v1/finetuning/build-dataset` again
3. Train new model on provider
4. Update `FINETUNING_MODEL_ID` with new ID
5. Keep fine-tuning enabled — no other changes needed

---

## Quick Reference Card

```bash
# 1. Build dataset
curl -X POST localhost:8000/api/v1/finetuning/build-dataset \
  -H "Content-Type: application/json" \
  -d '{"max_samples": 2000}'

# 2. Upload JSONL to provider console → get model ID

# 3. Configure
curl -X POST localhost:8000/api/v1/finetuning/config \
  -H "Content-Type: application/json" \
  -d '{"model_id": "ft:YOUR_MODEL_ID", "base_provider": "nvidia"}'

# 4. Enable
curl -X POST localhost:8000/api/v1/finetuning/toggle \
  -H "Content-Type: application/json" \
  -d '{"enabled": true}'

# 5. Verify
curl localhost:8000/api/v1/finetuning/health

# Disable anytime
curl -X POST localhost:8000/api/v1/finetuning/toggle \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'
```
