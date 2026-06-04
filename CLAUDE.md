# CLAUDE.md

Guidance for Claude Code (and humans) working in this repository.

## What this project is

An **educational, end-to-end LLMOps / AIOps reference project**. It is a working AI
chatbot, but the real purpose is to demonstrate *every stage* of taking an LLM
application to production: build → containerise → provision infra → CI/CD → deploy →
evaluate → add guardrails → observe.

When making changes, optimise for **clarity and teachability over cleverness**. Each
subsystem should map cleanly to one named LLMOps step (see the table below). Prefer
simple, well-commented code and keep the README's "definition of each step" accurate.

## The LLMOps steps and where each lives

| Step | What it means (one line) | Where in the repo |
|---|---|---|
| **Application** | The LLM agent itself: model, tools, prompt, memory | [backend/app/agent/](backend/app/agent/) |
| **RAG / ingestion** | Upload docs, chunk, embed, semantic search | [backend/app/ingestion/](backend/app/ingestion/) |
| **API & auth** | Serve the agent over HTTP with JWT auth + rate limiting | [backend/app/main.py](backend/app/main.py), [backend/app/auth/](backend/app/auth/) |
| **Frontend** | Chat UI; reverse-proxies the backend | [frontend/](frontend/) |
| **Containerise** | One image per service | [backend/Dockerfile](backend/Dockerfile), [frontend/Dockerfile](frontend/Dockerfile) |
| **Infrastructure (IaC)** | Provision ACR + AKS with Terraform | [terraform/](terraform/) |
| **Packaging / deploy** | Helm chart for all k8s resources | [k8s/aks/chart/](k8s/aks/chart/) |
| **CI/CD** | Version → build → push → deploy on git push | [.github/workflows/](.github/workflows/) |
| **Evaluation gate** | LLM-as-judge scoring; blocks bad deploys *(when enabled)* | [evaluation/](evaluation/), [agentops.yaml](agentops.yaml) |
| **Guardrails** | PII / prompt-injection / off-topic checks | [evaluation/guardrails/](evaluation/guardrails/) |
| **Observability** | Trace, monitor cost/latency, collect feedback | [notebooks/](notebooks/), LangSmith |

## Architecture (runtime)

Three pods in AKS: **frontend** (Next.js, LoadBalancer) → **backend** (FastAPI +
LangGraph, ClusterIP) → **postgres** (app tables + LangGraph memory + pgvector,
ClusterIP). Backend calls **OpenAI** (`gpt-4o-mini`) and **Tavily** (web search).

The agent has **four** tools: `get_user_info`, `save_user_info`, `internet_search`,
`search_user_documents`. Memory is two-layer: short-term checkpointer (per-thread,
auto-summarised) and long-term store (per-user facts), both in Postgres.

## Common commands

```bash
make test        # pytest backend unit tests
make lint        # ruff check + format --check on backend/
make lint-fix    # auto-fix
make eval        # run the LangSmith evaluation gate locally
```

Python deps are managed with **uv** (`uv pip install --system -e ".[dev]"`).
Python 3.12+. The frontend uses a **bleeding-edge Next.js** — see
[frontend/AGENTS.md](frontend/AGENTS.md) before touching frontend code.

## Conventions

- Backend is a modular FastAPI app: each domain (`auth`, `chat`, `ingestion`, `agent`)
  has its own `router.py` / `service.py` / `schemas.py`.
- Config is centralised in [backend/app/config.py](backend/app/config.py) via
  pydantic-settings; read from `.env`. Do not scatter `os.environ` reads.
- Evaluators live in [evaluation/metrics.py](evaluation/metrics.py) — import them, do
  not redefine them inline.

## Known rough edges

- **Guardrails are defined but not wired at runtime.** `evaluation/guardrails/` modules
  exist and are well-documented, but they only run offline (in the eval gate). There is
  no runtime hook calling them on live requests. Adding that is the natural next step.
- **The eval gate's `_predict` calls the model directly**, not the real agent. So the
  gate tests raw LLM quality, not the full agent with tools and memory. See the comment
  in `evaluation/run_eval.py` for how to swap in the real agent.
