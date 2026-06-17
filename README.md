# Semantic Search over a PDF

Postgraduate MBA deliverable — Full Cycle / AI Software Engineering.
A RAG (Retrieval-Augmented Generation) application that ingests a PDF Document,
stores its Chunks as Embeddings in a pgVector Collection, and answers Questions
through a CLI chat loop with an Out-of-context fallback when the answer is not
in the Document.

## System flow

```mermaid
flowchart LR
    subgraph Ingestion["📥 Ingestion · one-shot · src/ingest.py"]
        PDF[document.pdf] e1@--> SPLIT["Split into Chunks<br/>1000 chars · 150 overlap"]
        SPLIT e2@--> EMB1["Embed each Chunk<br/>models/gemini-embedding-001"]
        EMB1 e3@--> STORE[("pgVector<br/>Collection")]
    end
    subgraph Query["💬 Query · CLI loop · src/chat.py + src/search.py"]
        Q["User Question"] e4@--> EMB2["Embed Question"]
        EMB2 e5@--> RET["Retrieve top k=10<br/>similarity_search_with_score"]
        STORE e6@--> RET
        RET e7@--> PROMPT["Assemble prompt<br/>CONTEXTO + REGRAS"]
        PROMPT e8@--> LLM["gemini-2.5-flash-lite"]
        LLM e9@--> ANS["Answer<br/>or out-of-context fallback"]
    end

    e1@{ animate: true }
    e2@{ animate: true }
    e3@{ animate: true }
    e4@{ animate: true }
    e5@{ animate: true }
    e6@{ animate: true }
    e7@{ animate: true }
    e8@{ animate: true }
    e9@{ animate: true }

    classDef ingest fill:#1e3a8a,stroke:#3b82f6,color:#eff6ff;
    classDef query fill:#14532d,stroke:#22c55e,color:#f0fdf4;
    classDef store fill:#7c2d12,stroke:#f59e0b,color:#fffbeb;
    classDef answer fill:#4c1d95,stroke:#a855f7,color:#faf5ff;

    class PDF,SPLIT,EMB1 ingest;
    class Q,EMB2,RET,PROMPT,LLM query;
    class STORE store;
    class ANS answer;
```

## Prerequisites

- Python 3.11+
- Docker and Docker Compose
- A [Google AI Studio](https://aistudio.google.com/) API key with access to
  `models/gemini-embedding-001` and `gemini-2.5-flash-lite`

## Run order

Follow these five steps in order. A reader completing all five will have a
working end-to-end session.

### 1. Create a virtual environment and install dependencies

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

> **Contributors:** also install `pip install -r requirements-dev.txt` to get
> `pytest` and the rest of the test tooling.

### 2. Configure `.env`

Copy the example file and fill in the values:

```bash
cp .env.example .env
```

Then edit `.env`:

| Variable | Required | Value / notes |
|---|---|---|
| `GOOGLE_API_KEY` | **Yes** | Your Google AI Studio API key. |
| `GOOGLE_EMBEDDING_MODEL` | **Yes** | `models/gemini-embedding-001` — 768-dim model (ADR-0001). Do **not** use the retired `models/embedding-001`. |
| `DATABASE_URL` | **Yes** | `postgresql+psycopg://postgres:postgres@localhost:5432/rag` — the `+psycopg` driver suffix is mandatory; a bare `postgresql://` selects psycopg2 and the app will fail. |
| `PG_VECTOR_COLLECTION_NAME` | **Yes** | Name for the pgVector Collection, e.g. `documents`. |
| `PDF_PATH` | **Yes** | Path to the PDF to ingest, e.g. `document.pdf` (committed at repo root). |
| `OPENAI_API_KEY` | No | Listed in `.env.example` for reference only — the app uses Gemini (ADR-0001). Leave blank. |
| `OPENAI_EMBEDDING_MODEL` | No | Same — not required. Leave blank. |

### 3. Start the database

```bash
docker compose up -d
```

This starts two services:

- **`postgres`** — `pgvector/pgvector:pg17` on `localhost:5432`, user/password
  `postgres`/`postgres`, database `rag`.
- **`bootstrap_vector_ext`** — a one-shot container that runs
  `CREATE EXTENSION IF NOT EXISTS vector;` once `postgres` is healthy.

Allow 10–30 seconds for the health-check to pass, then confirm:

```bash
docker compose ps
```

Both services should show `healthy` / `exited 0` before proceeding.

### 4. Run Ingestion

```bash
python src/ingest.py
```

This reads the PDF at `PDF_PATH`, splits it into Chunks (1 000 chars, 150
overlap), embeds each Chunk with `models/gemini-embedding-001`, and stores the
Embeddings in the pgVector Collection. The script prints the total Chunk count
on success. Re-running rebuilds the Collection from scratch (`pre_delete_collection=True`)
so it is safe to run multiple times without duplicating Chunks.

### 5. Run the chat

```bash
python src/chat.py
```

The CLI prints `Faça sua pergunta:` and waits for a Question. Type a question
and press Enter to receive an Answer grounded in the ingested Document. If the
answer is not found in the Document, the Out-of-context fallback is returned
instead. Exit cleanly with an empty line, `Ctrl-D`, or `Ctrl-C`.

## Project structure

```
src/
  ingest.py   — Ingestion pipeline (PDF → Chunks → Embeddings → Collection)
  search.py   — Retrieval chain (Question → Embedding → top-k → prompt → LLM)
  chat.py     — CLI chat loop
tests/        — pytest suite (run with pytest)
docs/
  ROADMAP.md  — living phases tracker
  adr/        — Architecture Decision Records
  research/   — stack research notes
docker-compose.yml
.env.example
document.pdf  — committed PDF used for Ingestion
```

## Running tests

```bash
pip install -r requirements-dev.txt   # if not already installed
pytest
```

## Key decisions

- **Gemini only** — `models/gemini-embedding-001` for Embeddings,
  `gemini-2.5-flash-lite` for answers. See
  [ADR-0001](docs/adr/0001-gemini-for-embeddings-and-answers.md).
- **Idempotent Ingestion** — every `ingest.py` run rebuilds the Collection;
  re-running is always safe.
- **Out-of-context fallback** — questions outside the Document's scope return a
  fixed fallback phrase rather than a hallucinated answer.
