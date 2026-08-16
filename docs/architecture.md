# Architecture

## Query path

```mermaid
flowchart TD
  UI[React interface] --> API[FastAPI /api/chat]
  API --> QP[Query processing]
  QP --> D[Dense retrieval: Qdrant]
  QP --> B[Keyword retrieval: BM25]
  D --> F[Reciprocal-rank fusion]
  B --> F
  F --> R[Cross-encoder reranker]
  R --> V{Evidence threshold met?}
  V -- No --> A[Abstention]
  V -- Yes --> G[Evidence-only LLM generation]
  G --> C[Citation-label validation]
  C --> OUT[Answer and retrieved source cards]
```

## Ingestion path

```mermaid
flowchart LR
  PDF[Official 3GPP PDFs] --> X[PyMuPDF extraction]
  X --> S[Section detection and clause-aware chunks]
  S --> M[Metadata enrichment]
  M --> E[Embedding model]
  E --> Q[Qdrant]
  M --> B[Persistent BM25 records]
```

### Design choices

- Each chunk carries the source filename, detected specification/release, section, section title, and page number.
- Dense and sparse results use reciprocal-rank fusion, avoiding arbitrary score-scale comparisons.
- A cross-encoder scores query/evidence pairs before the evidence threshold decides whether answering is allowed.
- The LLM receives only accepted evidence and must use `[S#]` labels. Labels outside the retrieved set cause an abstention instead of an unsupported answer.
- This is a risk-reduction system, not a claim of mathematically guaranteed zero hallucinations.
