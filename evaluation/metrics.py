"""
evaluation/metrics.py
---------------------
LangSmith evaluator functions used by both the evaluation notebook and run_eval.py.

Each function follows the LangSmith evaluator signature:
    (run: langsmith.schemas.Run, example: langsmith.schemas.Example) -> dict

Returns a dict with keys: key, score (0.0–1.0), comment (optional).
"""

from langchain_openai import ChatOpenAI
from typing import TypedDict


def _make_judge(model: str = "gpt-4o-mini") -> ChatOpenAI:
    return ChatOpenAI(model=model, temperature=0)


# ── Structured output schemas ─────────────────────────────────────────────────

class CorrectnessGrade(TypedDict):
    score: int   # 0 or 1
    reason: str


class RelevanceGrade(TypedDict):
    score: int
    reason: str


class GroundednessGrade(TypedDict):
    score: int
    reason: str


# ── Prompt templates ──────────────────────────────────────────────────────────

_CORRECTNESS_PROMPT = """\
You are a strict evaluator. Given a question, a reference answer, and a candidate answer,
decide whether the candidate answer is factually correct and complete relative to the reference.
Score 1 if correct, 0 if incorrect or missing key facts.

Question: {question}
Reference: {reference}
Candidate: {answer}"""

_RELEVANCE_PROMPT = """\
You are a strict evaluator. Given a question and an answer, decide whether the answer
directly addresses the question without going off-topic.
Score 1 if relevant, 0 if not relevant or completely off-topic.

Question: {question}
Answer:   {answer}"""

_GROUNDEDNESS_PROMPT = """\
You are a strict evaluator. Given a question, an answer, and retrieved context,
decide whether every claim in the answer is supported by the context (or by common knowledge
when context is empty). Score 1 if grounded, 0 if the answer contains unsupported claims.

Question: {question}
Context:  {context}
Answer:   {answer}"""


# ── Evaluators ────────────────────────────────────────────────────────────────

def correctness_evaluator(run, example) -> dict:
    """Factual correctness vs. reference answer (requires example.outputs['answer'])."""
    llm = _make_judge().with_structured_output(CorrectnessGrade)
    question  = example.inputs["question"]
    reference = example.outputs["answer"]
    answer    = (run.outputs or {}).get("answer", "")
    grade: CorrectnessGrade = llm.invoke(
        _CORRECTNESS_PROMPT.format(question=question, reference=reference, answer=answer)
    )
    return {"key": "correctness", "score": float(grade["score"]), "comment": grade["reason"]}


def relevance_evaluator(run, example) -> dict:
    """Answer relevance — no reference required."""
    llm = _make_judge().with_structured_output(RelevanceGrade)
    question = example.inputs["question"]
    answer   = (run.outputs or {}).get("answer", "")
    grade: RelevanceGrade = llm.invoke(
        _RELEVANCE_PROMPT.format(question=question, answer=answer)
    )
    return {"key": "relevance", "score": float(grade["score"]), "comment": grade["reason"]}


def groundedness_evaluator(run, example) -> dict:
    """Answer is grounded in retrieved context (or general knowledge when context is empty)."""
    llm = _make_judge().with_structured_output(GroundednessGrade)
    question = example.inputs["question"]
    answer   = (run.outputs or {}).get("answer", "")
    context  = (run.outputs or {}).get("context", "")
    grade: GroundednessGrade = llm.invoke(
        _GROUNDEDNESS_PROMPT.format(question=question, context=context, answer=answer)
    )
    return {"key": "groundedness", "score": float(grade["score"]), "comment": grade["reason"]}


ALL_EVALUATORS = [correctness_evaluator, relevance_evaluator, groundedness_evaluator]
