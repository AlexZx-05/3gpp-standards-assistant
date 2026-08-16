from enum import Enum

from pydantic import BaseModel, Field, field_validator


class Confidence(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"
    insufficient = "insufficient"


class ChatRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    include_debug: bool = False

    @field_validator("question")
    @classmethod
    def non_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Question cannot be empty.")
        return value


class Source(BaseModel):
    chunk_id: str
    specification: str
    release: str | None = None
    section: str | None = None
    section_title: str | None = None
    page: int | None = None
    source: str
    source_url: str | None = None
    excerpt: str
    score: float | None = None


class RetrievalDebug(BaseModel):
    dense_candidates: int
    bm25_candidates: int
    fused_candidates: int
    reranked_candidates: int
    evidence_accepted: bool
    reason: str | None = None


class ChatResponse(BaseModel):
    answer: str
    grounded: bool
    confidence: Confidence
    sources: list[Source] = Field(default_factory=list)
    debug: RetrievalDebug | None = None


class SearchResponse(BaseModel):
    results: list[Source]


class DocumentInfo(BaseModel):
    specification: str
    release: str | None = None
    source: str
    chunks: int
