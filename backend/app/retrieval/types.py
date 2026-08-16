from dataclasses import dataclass


@dataclass
class Candidate:
    chunk_id: str
    text: str
    metadata: dict
    dense_score: float = 0.0
    bm25_score: float = 0.0
    fusion_score: float = 0.0
    rerank_score: float = 0.0
