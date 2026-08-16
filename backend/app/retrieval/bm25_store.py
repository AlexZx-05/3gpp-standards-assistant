"""Small persistent BM25 index built from exactly the chunks sent to Qdrant."""

import json
from pathlib import Path
import re

from rank_bm25 import BM25Okapi

from app.retrieval.types import Candidate


TOKEN_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9./_-]*")


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_PATTERN.findall(text)]


class BM25Store:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.records: list[dict] = []
        self.index: BM25Okapi | None = None

    def load(self) -> None:
        if not self.path.exists():
            self.records, self.index = [], None
            return
        self.records = json.loads(self.path.read_text(encoding="utf-8"))
        self.index = BM25Okapi([tokenize(record["text"]) for record in self.records]) if self.records else None

    def save(self, records: list[dict]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")
        self.records = records
        self.index = BM25Okapi([tokenize(record["text"]) for record in records]) if records else None

    def search(self, query: str, limit: int) -> list[Candidate]:
        if not self.index:
            self.load()
        if not self.index:
            return []
        scores = self.index.get_scores(tokenize(query))
        ordered = sorted(enumerate(scores), key=lambda item: item[1], reverse=True)[:limit]
        return [Candidate(str(self.records[i]["id"]), self.records[i]["text"], self.records[i]["metadata"], bm25_score=float(score)) for i, score in ordered if score > 0]
