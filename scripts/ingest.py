"""Index local PDFs in data/raw into Qdrant and the persistent BM25 store."""

import argparse
import hashlib
import sys
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from qdrant_client import QdrantClient, models

from app.core.config import get_settings
from app.ingestion.pdf import extract_pdf
from app.retrieval.bm25_store import BM25Store


def chunk_id(source: str, page: int, text: str) -> str:
    digest = hashlib.sha256(f"{source}:{page}:{text}".encode()).hexdigest()
    return str(uuid5(NAMESPACE_URL, digest))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--bm25-only",
        action="store_true",
        help="Rebuild the local BM25 records from the PDFs without recomputing Qdrant embeddings.",
    )
    args = parser.parse_args()
    settings = get_settings()
    pdfs = sorted((ROOT / "data/raw").glob("*.pdf"))
    if not pdfs:
        raise SystemExit("No PDFs found. Put official 3GPP PDFs in data/raw/ and rerun this script.")
    print(f"Extracting text from {len(pdfs)} PDF(s)...")
    all_chunks = []
    for pdf in pdfs:
        chunks = extract_pdf(pdf)
        all_chunks.extend(chunks)
        print(f"  {pdf.name}: {len(chunks)} chunks")
    if not all_chunks:
        raise SystemExit("No meaningful text was extracted from the supplied PDFs.")
    records_by_id = {}
    for chunk in all_chunks:
        identifier = chunk_id(chunk.source, chunk.page, chunk.text)
        metadata = {
            "specification": chunk.specification,
            "release": chunk.release,
            "section": chunk.section,
            "section_title": chunk.section_title,
            "page": chunk.page,
            "source": chunk.source,
            "source_url": chunk.source_url,
        }
        records_by_id[identifier] = {"id": identifier, "text": chunk.text, "metadata": metadata}
    records = list(records_by_id.values())

    if args.bm25_only:
        BM25Store(ROOT / "data/processed/bm25_records.json").save(records)
        print(f"Rebuilt BM25 records for {len(records)} chunks from {len(pdfs)} document(s).")
        return

    from sentence_transformers import SentenceTransformer
    print(f"Loading embedding model: {settings.embedding_model}")
    embedder = SentenceTransformer(settings.embedding_model)
    print(f"Embedding {len(all_chunks)} chunks. This may take several minutes on CPU.")
    vectors = embedder.encode(
        [chunk.text for chunk in all_chunks],
        normalize_embeddings=True,
        batch_size=settings.ingestion_batch_size,
        show_progress_bar=True,
    ).tolist()
    client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)
    client.recreate_collection(settings.qdrant_collection, vectors_config=models.VectorParams(size=len(vectors[0]), distance=models.Distance.COSINE))
    points = []
    for record, vector in zip(records, vectors, strict=True):
        points.append(models.PointStruct(id=record["id"], vector=vector, payload={"text": record["text"], "metadata": record["metadata"]}))
    print("Uploading chunks to Qdrant...")
    for start in range(0, len(points), 100):
        client.upsert(settings.qdrant_collection, points=points[start : start + 100], wait=True)
        print(f"  Uploaded {min(start + 100, len(points))}/{len(points)}")
    BM25Store(ROOT / "data/processed/bm25_records.json").save(records)
    print(f"Indexed {len(records)} chunks from {len(pdfs)} document(s) into {settings.qdrant_collection}.")


if __name__ == "__main__":
    main()
