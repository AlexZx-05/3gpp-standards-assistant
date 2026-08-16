"""Run retrieval metrics against the local, human-maintained evaluation set."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.retrieval.hybrid import get_retriever
from app.verification.evidence import validate_evidence


def reciprocal_rank(expected: set[str], actual: list[str]) -> float:
    for rank, item in enumerate(actual, start=1):
        if item in expected:
            return 1 / rank
    return 0.0


def main() -> None:
    cases = json.loads((ROOT / "data/evaluation/questions.json").read_text(encoding="utf-8"))
    retriever = get_retriever()
    answerable = [case for case in cases if case.get("expected_sources")]
    hits_at_5 = hits_at_10 = section_hits_at_5 = 0
    mrr = 0.0
    abstention_correct = 0
    details = []
    for case in cases:
        candidates, _ = retriever.search(case["question"])
        sources = [candidate.metadata.get("specification") for candidate in candidates]
        sections = [candidate.metadata.get("section") for candidate in candidates]
        accepted, _ = validate_evidence(candidates)
        expected = set(case.get("expected_sources", []))
        if expected:
            hits_at_5 += bool(expected.intersection(sources[:5]))
            hits_at_10 += bool(expected.intersection(sources[:10]))
            mrr += reciprocal_rank(expected, sources)
            expected_sections = set(case.get("expected_sections", []))
            if expected_sections:
                section_hits_at_5 += bool(expected_sections.intersection(sections[:5]))
        if case.get("should_abstain"):
            abstention_correct += int(not accepted)
        details.append({
            "id": case["id"],
            "retrieved_sources": sources,
            "retrieved_sections": sections,
            "top_reranker_score": candidates[0].rerank_score if candidates else None,
            "evidence_accepted": accepted,
        })
    metrics = {
        "answerable_cases": len(answerable),
        "recall_at_5": hits_at_5 / len(answerable) if answerable else None,
        "recall_at_10": hits_at_10 / len(answerable) if answerable else None,
        "mrr": mrr / len(answerable) if answerable else None,
        "section_recall_at_5": section_hits_at_5 / sum(bool(case.get("expected_sections")) for case in answerable) if any(case.get("expected_sections") for case in answerable) else None,
        "abstention_cases": sum(bool(case.get("should_abstain")) for case in cases),
        "abstention_accuracy": abstention_correct / max(1, sum(bool(case.get("should_abstain")) for case in cases)),
        "details": details,
    }
    output = ROOT / "data/evaluation/results.json"
    output.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
