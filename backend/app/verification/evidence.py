import re

from app.core.config import Settings, get_settings
from app.retrieval.types import Candidate

ABSTENTION = "I couldn't find sufficient evidence in the indexed 3GPP specifications to answer this reliably."
INFERENCE_LANGUAGE = re.compile(
    r"\b(?:can be inferred|appears to be|likely|probably|not explicitly stated|based on the context)\b",
    re.IGNORECASE,
)


def validate_evidence(candidates: list[Candidate], settings: Settings | None = None) -> tuple[bool, str | None]:
    settings = settings or get_settings()
    if len(candidates) < settings.min_evidence_count:
        return False, "Too few retrieved evidence chunks."
    if not candidates or candidates[0].rerank_score < settings.min_rerank_score:
        return False, "Top reranker score is below the evidence threshold."
    return True, None


def citation_labels_are_valid(answer: str, evidence_count: int) -> bool:
    labels = [int(value) for value in re.findall(r"\[S(\d+)\]", answer)]
    return bool(labels) and all(1 <= value <= evidence_count for value in labels)


def answer_is_directly_grounded(answer: str, evidence_count: int) -> bool:
    """Apply deterministic safeguards before an LLM answer reaches the user.

    This is deliberately conservative: a response that declares an inference or
    leaves a factual sentence uncited is rejected in favour of abstention.
    """
    if not citation_labels_are_valid(answer, evidence_count) or INFERENCE_LANGUAGE.search(answer):
        return False
    sentences = [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", answer) if sentence.strip()]
    factual_sentences = [sentence for sentence in sentences if re.search(r"[A-Za-z0-9]", sentence)]
    return bool(factual_sentences) and all(re.search(r"\[S\d+\]", sentence) for sentence in factual_sentences)
