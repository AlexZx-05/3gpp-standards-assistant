# 3GPP Standards Assistant

A citation-grounded Retrieval-Augmented Generation (RAG) application for answering questions about selected 3GPP technical standards.

It retrieves evidence from official 3GPP PDFs, generates an answer only when the evidence is strong enough, and shows source-bound citations so each response can be traced back to the standard.

For the shortest setup path after cloning, see [QUICKSTART.md](QUICKSTART.md).

## 🎥 Demo

[![Watch the Demo](https://img.shields.io/badge/▶%20Watch%20Demo-3GPP%20Standards%20Assistant-blue?style=for-the-badge)](https://drive.google.com/file/d/1h3rXcIjzexQJVlEdjCIoofosAleIHXS9/view?usp=sharing)

## Why this project was built

3GPP specifications are large, technical, and distributed across many documents. Finding a precise answer manually can take significant time, while generic AI chatbots can produce fluent answers that are difficult to verify.

This project was built to make standards research faster and safer. Instead of relying on a model's memory, it searches an indexed collection of official specifications and presents the supporting evidence with the answer.

## What problem it solves

The application helps engineers, students, and researchers to:

- Search a controlled set of 3GPP specifications in natural language.
- Find exact supporting passages, including specification, section, and page number.
- Answer terminology-heavy questions using both semantic and keyword retrieval.
- Avoid unsupported answers by abstaining when the retrieved evidence is insufficient.
- Review the retrieved evidence before relying on an answer.

Example supported question:

> Which network function does the UE send the Registration Request message to?

The application retrieves TS 24.501 evidence and answers that the UE sends it to the AMF, with a citation to the source chunk.

## Key capabilities

- Hybrid retrieval: dense vector search in Qdrant plus BM25 keyword search.
- Reciprocal-rank fusion and cross-encoder reranking for better result ordering.
- Evidence thresholds that prevent a generated response when support is weak.
- Evidence-only answer generation with source labels such as [S1].
- Citation-label validation: citations must refer to retrieved evidence.
- Clear abstention behaviour for questions outside the indexed standards.
- React frontend, FastAPI backend, and Qdrant vector database.
- Health, document-listing, search, and chat API endpoints.

## How it works

~~~text
Official 3GPP PDFs
        ->
PDF extraction and section-aware chunking
        ->
BM25 index + embedding vectors in Qdrant
        ->
Hybrid retrieval and reciprocal-rank fusion
        ->
Cross-encoder reranking and evidence validation
        ->
Grounded answer with citations, or safe abstention
~~~

See the detailed design in [docs/architecture.md](docs/architecture.md).

## Evidence safeguards

This is designed to reduce unsupported claims; it does not claim that hallucinations are mathematically impossible.

- Each chunk preserves source metadata such as specification, release, section, page, and source file.
- Dense semantic retrieval is combined with BM25 retrieval, which is useful for exact identifiers such as AMF, S-NSSAI, and TS 24.501.
- A reranker prioritizes the most relevant retrieved evidence.
- Configurable evidence thresholds decide whether the system can answer.
- The model is instructed to use only the retrieved context.
- Invalid or missing citation labels cause the system to abstain rather than return an ungrounded response.

## Indexed knowledge base

The current local index contains 11,870 unique evidence chunks from these Release 18 specifications:

| Specification | Topic | Chunks |
| --- | --- | ---: |
| TS 23.501 | 5G System architecture | 2,098 |
| TS 23.502 | 5G System procedures | 2,492 |
| TS 24.501 | 5GS NAS protocol | 3,660 |
| TS 29.500 | Service Based Architecture realization | 423 |
| TS 38.331 | NR RRC protocol | 3,199 |

Only use PDFs that you are authorized to store and process. PDFs are placed in data/raw/ and are not committed to this repository.

## Technology stack

- Frontend: React + Vite
- Backend: FastAPI + Uvicorn
- Vector database: Qdrant
- Retrieval: sentence-transformer embeddings, BM25, reciprocal-rank fusion, and cross-encoder reranking
- Generation: an OpenAI-compatible LLM API

## Prerequisites

Install the following before running locally:

- Python 3.11 or later
- Node.js 20 or later
- Docker Desktop (to run Qdrant)
- An API key for an OpenAI-compatible LLM provider
- Official 3GPP PDF files for the specifications you want to index

## Configuration

Create your local environment file from the template:

~~~powershell
Copy-Item .env.example .env
~~~

Then set these values in .env:

~~~text
LLM_API_KEY=your_provider_key
LLM_BASE_URL=https://your-provider.example/openai/v1
LLM_MODEL=your-provider-model
~~~

Important: never commit .env, API keys, or provider credentials to GitHub.

## Run locally

### 1. Install backend dependencies

~~~powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
~~~

### 2. Start Qdrant

~~~powershell
docker compose up qdrant -d
~~~

### 3. Add and index source PDFs

Copy the selected 3GPP PDFs into data/raw/, then run:

~~~powershell
python scripts/ingest.py
~~~

The full ingestion process extracts chunks, creates embeddings, uploads vectors to Qdrant, and writes BM25 records. The first run can take longer because embedding and reranking models may need to download.

If Qdrant already contains the embeddings and you only need to regenerate the local BM25 index:

~~~powershell
python scripts/ingest.py --bm25-only
~~~

### 4. Start the backend

~~~powershell
python -m uvicorn app.main:app --app-dir backend --reload --reload-dir backend
~~~

Verify that the backend and Qdrant are available:

~~~powershell
curl http://127.0.0.1:8000/api/health
~~~

Expected response:

~~~json
{"status":"ok","qdrant":"available"}
~~~

Useful API links:

- API documentation: http://127.0.0.1:8000/docs
- Indexed documents: http://127.0.0.1:8000/api/documents

Note: http://127.0.0.1:8000/ returning 404 is normal. The backend exposes API routes; the user interface runs separately on port 5173.

### 5. Start the frontend

Open a second terminal:

~~~powershell
cd frontend
npm install
npm run dev
~~~

Open the URL shown by Vite, normally http://127.0.0.1:5173.

## Run with Docker

1. Create and configure .env as described above.
2. Place your selected PDFs in data/raw/.
3. Start all services:

~~~powershell
docker compose up --build -d
~~~

4. Run ingestion inside the backend container:

~~~powershell
docker compose exec backend python scripts/ingest.py
~~~

5. Open http://127.0.0.1:5173.

The API is available at http://127.0.0.1:8000 and Qdrant is available at http://127.0.0.1:6333.

## API overview

| Endpoint | Purpose |
| --- | --- |
| GET /api/health | Checks backend and Qdrant connectivity. |
| GET /api/documents | Lists indexed documents and chunk counts. |
| POST /api/search | Returns ranked evidence chunks without LLM generation. |
| POST /api/chat | Returns a grounded answer, citations, and retrieved sources. |

Example request:

~~~powershell
curl -X POST http://127.0.0.1:8000/api/search -H "Content-Type: application/json" -d '{"question":"Which network function does the UE send the Registration Request message to?"}'
~~~

## Evaluation and quality checks

The evaluation set at data/evaluation/questions.json contains 30 manually written cases. Run:

~~~powershell
python scripts/evaluate.py
~~~

The script writes measured retrieval metrics to data/evaluation/results.json. Do not claim metrics that have not been generated from your final indexed corpus.

Run backend tests:

~~~powershell
$env:PYTHONPATH = "backend"
pytest backend/tests -q
~~~

Build the frontend for production:

~~~powershell
cd frontend
npm run build
~~~

## Demonstration checklist

For a short project demo:

1. Start Qdrant, backend, and frontend.
2. Show /api/health returning status ok and qdrant available.
3. Ask a supported question:
   - Which network function does the UE send the Registration Request message to?
4. Show the answer, the [S1] citation, and the TS 24.501 source card.
5. Ask an out-of-scope question, for example:
   - Who is the current President of the United States?
6. Show that the application abstains because there is no supporting 3GPP evidence.

This demonstrates both useful retrieval and the system's protection against unsupported answers.

## Project structure

~~~text
backend/             FastAPI application and tests
frontend/            React user interface
scripts/             ingestion and evaluation scripts
data/raw/            local source PDFs (not committed)
data/processed/      generated BM25 records and evaluation outputs
docs/                architecture documentation
docker-compose.yml   local multi-service setup
~~~

## Limitations and future work

- PDF layouts vary, so extracted sections should be reviewed when adding a new specification.
- Citation labels verify that a cited source was retrieved; sentence-level entailment verification would be a stronger production safeguard.
- Retrieval quality depends on the selected PDFs, chunking, embeddings, reranker, and thresholds.
- A larger expert-validated evaluation set would improve confidence in measured performance.
- Production deployment should add authentication, rate limiting, monitoring, and secret management.

## License and acknowledgement

This repository contains application code and generated local indexes. 3GPP specifications remain subject to their respective copyright and distribution terms.
