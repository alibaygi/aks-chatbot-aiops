#!/usr/bin/env python3
"""
evaluation/run_eval.py
----------------------
CLI entry point for the evaluation gate used in CI/CD pipelines.

Usage:
    python evaluation/run_eval.py [--config agentops.yaml] [--output results.json]

Exit codes:
    0 — all metrics pass their configured thresholds
    2 — one or more metrics are below threshold (evaluation gate fails)
    1 — unexpected error

The script reads thresholds from agentops.yaml, runs LangSmith evaluate() against
the golden dataset, writes a results.json file, and prints a summary table.
"""

import argparse
import json
import os
import statistics
import sys
import uuid
from pathlib import Path

import yaml
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langsmith import Client, traceable

# Ensure the repo root is on the path so `evaluation.metrics` is importable
sys.path.insert(0, str(Path(__file__).parent.parent))
from evaluation.metrics import ALL_EVALUATORS  # noqa: E402


# ── Target function ───────────────────────────────────────────────────────────

@traceable(name="run_eval_predict")
def _predict(inputs: dict) -> dict:
    """
    Simple predict function: calls gpt-4o-mini directly.
    In production replace this with a call to the live /api/v1 endpoint.
    """
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    response = llm.invoke(inputs["question"])
    return {"answer": response.content, "context": ""}


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Run LangSmith evaluation gate")
    parser.add_argument(
        "--config",
        default=str(Path(__file__).parent.parent / "agentops.yaml"),
        help="Path to agentops.yaml (default: repo root)",
    )
    parser.add_argument(
        "--output",
        default="results.json",
        help="Path to write results JSON (default: results.json)",
    )
    args = parser.parse_args()

    # ── Load env ──────────────────────────────────────────────────────────────
    load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env", override=False)
    api_key = os.environ.get("LANGSMITH_API_KEY", "")
    project  = os.environ.get("LANGSMITH_PROJECT", "aks-chatbot")
    if not api_key:
        print("ERROR: LANGSMITH_API_KEY is not set.", file=sys.stderr)
        return 1

    # ── Load thresholds ───────────────────────────────────────────────────────
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"ERROR: config file not found: {config_path}", file=sys.stderr)
        return 1
    with config_path.open() as fh:
        config = yaml.safe_load(fh)
    thresholds: dict[str, float] = config.get("evaluation", {}).get("thresholds", {})
    print(f"Thresholds: {thresholds}")

    # ── Run evaluation ────────────────────────────────────────────────────────
    client = Client(api_key=api_key)
    dataset_name = config.get("evaluation", {}).get("dataset", "aks-chatbot-golden-v1")
    experiment_prefix = f"ci-{uuid.uuid4().hex[:8]}"

    print(f"Running evaluation on dataset '{dataset_name}' …")
    results = client.evaluate(
        _predict,
        data=dataset_name,
        evaluators=ALL_EVALUATORS,
        experiment_prefix=experiment_prefix,
        num_repetitions=1,
        max_concurrency=2,
    )

    # ── Aggregate scores ──────────────────────────────────────────────────────
    scores: dict[str, list[float]] = {}
    for result in results._results:
        for fb in result.get("evaluation_results", {}).get("results", []):
            if fb.score is not None:
                scores.setdefault(fb.key, []).append(float(fb.score))

    summary = {
        metric: {
            "mean": statistics.mean(vals),
            "pass_rate": sum(1 for s in vals if s >= 0.5) / len(vals),
            "n": len(vals),
        }
        for metric, vals in scores.items()
    }

    # ── Write results.json ────────────────────────────────────────────────────
    output = {
        "experiment": experiment_prefix,
        "dataset": dataset_name,
        "summary": summary,
        "passed": True,
        "failures": [],
    }

    print(f"\n{'Metric':<16} {'Mean':>6}  {'Pass rate':>10}  {'Threshold':>10}  {'Status':>6}")
    print("-" * 56)
    all_passed = True
    for metric, stat in summary.items():
        threshold = thresholds.get(metric, 0.0)
        passed = stat["mean"] >= threshold
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_passed = False
            output["failures"].append(
                {"metric": metric, "mean": stat["mean"], "threshold": threshold}
            )
        print(
            f"{metric:<16} {stat['mean']:>6.3f}  {stat['pass_rate']:>9.0%}  "
            f"{threshold:>9.2f}  {status:>6}"
        )

    output["passed"] = all_passed

    Path(args.output).write_text(json.dumps(output, indent=2))
    print(f"\nResults written to {args.output}")

    if not all_passed:
        print("\nEvaluation gate FAILED — metrics below threshold.", file=sys.stderr)
        return 2

    print("\nEvaluation gate PASSED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
