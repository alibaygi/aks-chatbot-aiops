# Plan — Make the AIOps Steps Clear

**Goal:** The README is already clear up to *"infrastructure provisioned + chatbot
running."* The owner knows that part. What's missing is what comes **next** — the
**AIOps** part — explained just as simply. Today those pieces exist as folders
(`evaluation/`, `evaluation/guardrails/`, `notebooks/`) but nothing names them, defines
them, or shows how they fit together. That is the confusion to remove.

Keep it **simple and educational**. Definitions over detail. Do the two tasks below.

---

## Task 1 (main) — ✅ DONE (Opus, 2026-05-31)

The "After Deployment: The AIOps Loop" section is already written and inserted into
[README.md](README.md), along with: the softened intro, an updated table of contents, a
mermaid loop diagram, a short paragraph per step (Evaluate/Guard/Observe/Gate/Improve)
linking to real files, and the "three tools → four tools (+ RAG)" correction in the
"How It Works" section. **Sonnet does not need to redo this — just leave it.** The
original brief is kept below for reference.

---

<details>
<summary>Original Task 1 brief (for reference — already implemented)</summary>

Add this right after the deployment phases. Use the draft below almost as-is — it is
written deliberately plainly. The point is that a learner reads it once and understands
*what each step is and why it exists*.

> ### After Deployment: The AIOps Loop
>
> Building and deploying the chatbot is only half the job. **AIOps** (for LLM apps, also
> called **LLMOps**) is everything you do to keep an AI app *good* once it's live. Unlike
> normal software, an LLM's answers can quietly get worse — from a prompt tweak, a model
> update, or a new kind of question — without anything "crashing." So AIOps is a
> **loop** you keep running, not a one-time setup.
>
> There are five vital steps. Each already has a home in this repo:
>
> | Step | In one sentence | Where it lives |
> |---|---|---|
> | **1. Evaluate** | Automatically score answer quality — is it *correct*, *on-topic*, and *grounded* in real sources? | [evaluation/](evaluation/) |
> | **2. Guard** | Block bad **inputs** (prompt injection) and bad **outputs** (leaked PII, off-topic replies). | [evaluation/guardrails/](evaluation/guardrails/) |
> | **3. Observe** | Trace every request to see latency, token **cost**, which tools were used, and errors. | [notebooks/](notebooks/) + LangSmith |
> | **4. Gate** | Put Evaluate + Guard inside CI so a change that lowers quality **cannot deploy**. | [agentops.yaml](agentops.yaml) |
> | **5. Improve** | Collect user feedback (👍/👎), find weak spots, add them to the test set — then loop back to step 1. | the loop closes |
>
> **How to read it:** *Evaluate* tells you if the bot is good. *Guard* keeps it safe in
> the moment. *Observe* shows you what's really happening in production. *Gate* stops
> regressions from shipping. *Improve* feeds what you learn back in. Round and round.
>
> Each step below links to runnable code you can open and try.

Then, under that section, add **one short paragraph per step** (3–4 sentences) that:
explains the step in plain words, says *why it matters for an LLM specifically*, and
points to the exact file to open (e.g. `evaluation/metrics.py`,
`evaluation/guardrails/pii_check.py`, `notebooks/observability_monitoring.ipynb`,
`agentops.yaml`). No deep dives — definitions a beginner can follow.

Also: the existing intro says the project's "primary focus is build and deployment
automation." Soften that one line so the focus is the **whole lifecycle** (build →
deploy → **the AIOps loop**), so the new section doesn't feel bolted on.

</details>

---

## Task 2 — Remove the things that make the repo look confusing — ✅ DONE (Sonnet, 2026-05-31)

The owner doesn't need new infra work — just stop the repo from contradicting itself, so
the AIOps story is the clear path:

- [x] **CI pipelines:** keep only `.github/workflows/pr_checks.yaml` and
      `.github/workflows/deploy.yml`. Delete `staging.yaml`, `deploy-to-prod.yaml`, and
      `.gitlab-ci.yml` (they duplicate deploy with different auth and even a different
      CI platform — pure noise for a learner). *(Owner decision, 2026-05-31.)*
- [x] ~~**Stray EKS/Minikube leftovers:** `pyproject.toml` name + `k8s/HOW_IT_WORKS.md`~~
      **DONE (Opus, 2026-05-31):** `pyproject.toml` renamed to `chatbot-on-aks`;
      `k8s/HOW_IT_WORKS.md` fully retargeted from Minikube to AKS (Azure Load Balancer +
      public IP, Azure Disk PVC, Helm deploy). No EKS/Minikube strings remain.
- [x] **`.gitignore` hides the lessons:** it ignores `notebooks/`, so the teaching
      notebooks aren't even in git. Remove that line so they're versioned.
- [x] **Wire the evaluation gate into `deploy.yml`** *(Owner decision, 2026-05-31 —
      option A).* `deploy-to-prod.yaml` (being deleted) was the only place the eval gate
      ran in CI. To keep the README's "Gate" step literally true, add a step to
      `.github/workflows/deploy.yml` that runs the gate **before** the build/deploy steps,
      so a failing gate stops the rollout. Concretely:
      - Add a Python setup + `uv pip install --system -e ".[dev]"` step, then
        `python evaluation/run_eval.py --config agentops.yaml --output results.json`.
        `run_eval.py` already exits non-zero (code 2) on failure, which fails the job.
      - It needs `LANGSMITH_API_KEY` and `OPENAI_API_KEY` as GitHub secrets — add them to
        the step's `env:` and note them in the README's Phase 2 "Add GitHub Secrets" table.
      - Put this step **after checkout/version-bump but before `az acr build`** so no
        image is built or deployed when quality is below threshold.
      - If a learner hasn't set up a LangSmith dataset yet, a hard gate would block every
        deploy. Make it **non-blocking by default** with a clear comment showing how to
        make it blocking (e.g. guard the step with an `if` on a `RUN_EVAL_GATE` repo
        variable, defaulting off), OR document this clearly. Keep it simple and explain
        the choice in a comment so the educational intent is obvious.

---

## What NOT to do
Don't add more infra, more pipelines, or more tooling. The pieces already exist — the
job is to **name them, define them simply, and connect them into one clear loop.**
