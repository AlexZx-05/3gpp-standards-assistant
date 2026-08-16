import logging
from collections import Counter

from fastapi import APIRouter, HTTPException
from openai import APIStatusError, AuthenticationError
from qdrant_client import QdrantClient

from app.core.config import get_settings
from app.generation.grounded import GroundedGenerator, LLMConfigurationError
from app.models.schemas import ChatRequest, ChatResponse, Confidence, DocumentInfo, RetrievalDebug, SearchResponse, Source
from app.retrieval.hybrid import get_retriever
from app.retrieval.types import Candidate
from app.verification.evidence import ABSTENTION, answer_is_directly_grounded, validate_evidence

router = APIRouter(prefix="/api")
logger = logging.getLogger(__name__)


def as_source(candidate: Candidate) -> Source:
    metadata = candidate.metadata
    return Source(
        chunk_id=candidate.chunk_id,
        specification=metadata.get("specification", "Unknown 3GPP specification"),
        release=metadata.get("release"),
        section=metadata.get("section"),
        section_title=metadata.get("section_title"),
        page=metadata.get("page"),
        source=metadata.get("source", "Unknown source"),
        source_url=metadata.get("source_url"),
        excerpt=candidate.text[:420],
        score=round(candidate.rerank_score, 4),
    )


@router.get("/health")
def health() -> dict[str, str]:
    settings = get_settings()
    try:
        QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key).get_collections()
        qdrant = "available"
    except Exception:
        qdrant = "unavailable"
    return {"status": "ok", "qdrant": qdrant}


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    try:
        candidates, counts = get_retriever().search(request.question)
    except Exception as error:
        logger.exception("Retrieval failed")
        raise HTTPException(status_code=503, detail="Retrieval is unavailable. Confirm Qdrant is running and documents have been indexed.") from error
    accepted, reason = validate_evidence(candidates)
    debug = RetrievalDebug(**counts, evidence_accepted=accepted, reason=reason) if request.include_debug else None
    sources = [as_source(candidate) for candidate in candidates]
    if not accepted:
        return ChatResponse(answer=ABSTENTION, grounded=False, confidence=Confidence.insufficient, sources=sources, debug=debug)
    generator = GroundedGenerator()
    try:
        answer = generator.answer(request.question, candidates)
    except LLMConfigurationError as error:
        logger.warning("Invalid LLM provider configuration: %s", error)
        raise HTTPException(status_code=503, detail=str(error)) from error
    except AuthenticationError as error:
        logger.warning("LLM provider rejected configured credentials")
        raise HTTPException(status_code=502, detail="The LLM provider rejected the configured API credentials. Update LLM_API_KEY and restart the backend.") from error
    except APIStatusError as error:
        # xAI reports an invalid key as HTTP 400 rather than a standard 401.
        if error.status_code in {400, 401, 403} and "api key" in str(error).lower():
            logger.warning("LLM provider rejected configured credentials")
            raise HTTPException(status_code=502, detail="The LLM provider rejected the configured API credentials. Update LLM_API_KEY and restart the backend.") from error
        logger.exception("LLM provider returned HTTP %s", error.status_code)
        raise HTTPException(status_code=503, detail="Grounded generation is temporarily unavailable.") from error
    except Exception as error:
        logger.exception("Grounded generation failed")
        raise HTTPException(status_code=503, detail="Grounded generation is temporarily unavailable.") from error
    # Answers produced by a configured LLM must cite retrieved evidence; otherwise abstain.
    if generator.configured and not answer_is_directly_grounded(answer, len(candidates)):
        return ChatResponse(answer=ABSTENTION, grounded=False, confidence=Confidence.insufficient, sources=sources, debug=debug)
    confidence = Confidence.high if candidates[0].rerank_score >= 0.75 else Confidence.medium
    return ChatResponse(answer=answer, grounded=generator.configured, confidence=confidence, sources=sources, debug=debug)


@router.post("/search", response_model=SearchResponse)
def search(request: ChatRequest) -> SearchResponse:
    try:
        candidates, _ = get_retriever().search(request.question)
        return SearchResponse(results=[as_source(candidate) for candidate in candidates])
    except Exception as error:
        raise HTTPException(status_code=503, detail="Search is unavailable.") from error


@router.get("/documents", response_model=list[DocumentInfo])
def documents() -> list[DocumentInfo]:
    retriever = get_retriever()
    retriever.bm25.load()
    counts: Counter[tuple[str, str | None, str]] = Counter(
        (record["metadata"].get("specification", "Unknown"), record["metadata"].get("release"), record["metadata"].get("source", "Unknown"))
        for record in retriever.bm25.records
    )
    return [DocumentInfo(specification=spec, release=release, source=source, chunks=count) for (spec, release, source), count in counts.items()]
