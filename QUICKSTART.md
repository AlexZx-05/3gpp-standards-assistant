# Quick Start: Run After Cloning

This guide lets another developer run the 3GPP Standards Assistant after cloning this repository.

## What you need

- Python 3.11+
- Node.js 20+
- Docker Desktop
- Your own OpenAI-compatible LLM API credentials
- Official 3GPP PDF files that you are authorized to use

The repository intentionally does not contain API keys, virtual environments, PDF files, or generated search indexes.

## 1. Clone the repository

~~~bash
git clone https://github.com/AlexZx-05/3gpp-standards-assistant.git
cd 3gpp-standards-assistant
~~~

## 2. Add your own credentials

Copy the safe template:

~~~powershell
Copy-Item .env.example .env
~~~

Open `.env` and fill in only your own provider values:

~~~text
LLM_API_KEY=your_provider_key
LLM_BASE_URL=https://your-provider.example/openai/v1
LLM_MODEL=your-provider-model
~~~

Never commit or share your `.env` file.

## 3. Add authorized source PDFs

Place the selected official PDFs in `data/raw/`. For example:

~~~text
data/raw/TS_23.501.pdf
data/raw/TS_23.502.pdf
data/raw/TS_24.501.pdf
data/raw/TS_29.500.pdf
data/raw/TS_38.331.pdf
~~~

The PDFs are required because the application answers from retrieved specification evidence. They are not included in GitHub due to source distribution and repository-size concerns.

## 4. Install and run

~~~powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
docker compose up qdrant -d
python scripts/ingest.py
python -m uvicorn app.main:app --app-dir backend --reload --reload-dir backend
~~~

In a separate terminal:

~~~powershell
cd frontend
npm install
npm run dev
~~~

Open `http://127.0.0.1:5173` in a browser.

## 5. Verify

~~~powershell
curl http://127.0.0.1:8000/api/health
~~~

Expected response:

~~~json
{"status":"ok","qdrant":"available"}
~~~

Then ask a supported question in the frontend:

> Which network function does the UE send the Registration Request message to?

