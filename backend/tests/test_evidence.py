from app.core.config import Settings
from app.retrieval.hybrid import HybridRetriever
from app.retrieval.types import Candidate
from app.verification.evidence import answer_is_directly_grounded, citation_labels_are_valid, validate_evidence


def candidate(identifier: str, score: float = 0.8) -> Candidate:
    return Candidate(identifier, "Registration Request text", {"specification": "TS 24.501"}, rerank_score=score)


def test_evidence_accepts_a_strong_reranked_chunk() -> None:
    accepted, reason = validate_evidence([candidate("one")], Settings(min_rerank_score=0.5))
    assert accepted is True
    assert reason is None


def test_evidence_rejects_weak_retrieval() -> None:
    accepted, reason = validate_evidence([candidate("one", 0.1)], Settings(min_rerank_score=0.5))
    assert accepted is False
    assert "below" in reason


def test_fusion_rewards_result_present_in_both_indexes() -> None:
    dense = [candidate("shared"), candidate("dense-only")]
    sparse = [candidate("shared"), candidate("sparse-only")]
    fused = HybridRetriever.fuse(dense, sparse)
    assert fused[0].chunk_id == "shared"


def test_citation_validation_rejects_unretrieved_labels() -> None:
    assert citation_labels_are_valid("The AMF is described here [S1].", 1)
    assert not citation_labels_are_valid("Unsupported [S2].", 1)
    assert not citation_labels_are_valid("No citations.", 1)


def test_direct_grounding_rejects_inference_language() -> None:
    answer = "It can be inferred that the UE registers with the network [S1]."
    assert not answer_is_directly_grounded(answer, 1)


def test_direct_grounding_requires_a_citation_for_each_sentence() -> None:
    assert answer_is_directly_grounded("The UE initiates registration [S1].", 1)
    assert not answer_is_directly_grounded("The UE initiates registration [S1]. The AMF processes it.", 1)
