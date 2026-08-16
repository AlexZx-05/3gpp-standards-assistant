"""Dense + BM25 retrieval, reciprocal-rank fusion, and reranking."""

from functools import lru_cache
from pathlib import Path

from qdrant_client import QdrantClient

from app.core.config import Settings, get_settings
from app.retrieval.bm25_store import BM25Store
from app.retrieval.types import Candidate


class HybridRetriever:
    def __init__(self, settings: Settings | None = None, bm25_path: Path | None = None) -> None:
        self.settings = settings or get_settings()
        self.bm25 = BM25Store(bm25_path or Path("data/processed/bm25_records.json"))
        self._embedder = None
        self._reranker = None

    def _embedding_model(self):
        if self._embedder is None:
            from sentence_transformers import SentenceTransformer
            self._embedder = SentenceTransformer(self.settings.embedding_model)
        return self._embedder

    def _reranker_model(self):
        if self._reranker is None:
            from sentence_transformers import CrossEncoder
            self._reranker = CrossEncoder(self.settings.reranker_model)
        return self._reranker

    def _client(self) -> QdrantClient:
        return QdrantClient(url=self.settings.qdrant_url, api_key=self.settings.qdrant_api_key)

    def dense_search(self, query: str) -> list[Candidate]:
        vector = self._embedding_model().encode(query, normalize_embeddings=True).tolist()
        response = self._client().query_points(collection_name=self.settings.qdrant_collection, query=vector, limit=self.settings.top_k_dense, with_payload=True)
        return [Candidate(str(point.id), str((point.payload or {}).get("text", "")), dict((point.payload or {}).get("metadata", {})), dense_score=float(point.score)) for point in response.points]

    @staticmethod
    def fuse(dense: list[Candidate], sparse: list[Candidate], k: int = 60) -> list[Candidate]:
        merged: dict[str, Candidate] = {}
        for rank, candidate in enumerate(dense, start=1):
            stored = merged.setdefault(candidate.chunk_id, candidate)
            stored.dense_score = candidate.dense_score
            stored.fusion_score += 1 / (k + rank)
        for rank, candidate in enumerate(sparse, start=1):
            stored = merged.setdefault(candidate.chunk_id, candidate)
            stored.bm25_score = candidate.bm25_score
            stored.fusion_score += 1 / (k + rank)
        return sorted(merged.values(), key=lambda item: item.fusion_score, reverse=True)

    def rerank(self, query: str, candidates: list[Candidate]) -> list[Candidate]:
        if not candidates:
            return []
        scores = self._reranker_model().predict([(query, candidate.text) for candidate in candidates])
        for candidate, score in zip(candidates, scores, strict=True):
            candidate.rerank_score = float(score)
        return sorted(candidates, key=lambda item: item.rerank_score, reverse=True)[: self.settings.top_k_rerank]

    def search(self, query: str) -> tuple[list[Candidate], dict[str, int]]:
        dense = self.dense_search(query)
        sparse = self.bm25.search(query, self.settings.top_k_bm25)
        fused = self.fuse(dense, sparse)
        reranked = self.rerank(query, fused[: max(self.settings.top_k_dense, self.settings.top_k_bm25)])
        return reranked, {"dense_candidates": len(dense), "bm25_candidates": len(sparse), "fused_candidates": len(fused), "reranked_candidates": len(reranked)}


@lru_cache
def get_retriever() -> HybridRetriever:
    return HybridRetriever()
