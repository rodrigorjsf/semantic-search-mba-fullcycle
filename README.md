# Semantic Search over a PDF

Postgraduate MBA deliverable — Full Cycle / AI Software Engineering.
A RAG (Retrieval-Augmented Generation) application that ingests a PDF Document,
stores its Chunks as Embeddings in a pgVector Collection, and answers Questions
through a CLI chat loop with an Out-of-context fallback when the answer is not
in the Document.

## System flow

```mermaid
flowchart TB
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

## Run Example

<p align="center">
  <img src="docs/chat-execution-example.png" alt="Texto alternativo" width="600px" />
</p>

## Prerequisites

- **Python 3.11 or 3.12** for the classic-virtualenv path. The pinned
  dependencies publish no wheels for Python 3.13+ — on a newer interpreter use
  the [`uv`](https://docs.astral.sh/uv/) path in step 1, which pins Python 3.12
  for you automatically.
- Docker and Docker Compose
- A [Google AI Studio](https://aistudio.google.com/apikey) API key with access to
  `models/gemini-embedding-001` and `gemini-2.5-flash-lite`. The **free tier**
  works (see the rate-limit note in step 4).

## Run order

Follow these five steps in order. A reader completing all five will have a
working end-to-end session.

### 1. Install dependencies

Pick **one** of the two paths. Every run command later in this guide shows both
forms.

**Recommended — `uv` (no venv to manage, pins Python 3.12):** install
[`uv`](https://docs.astral.sh/uv/), then nothing else to do here — each `uv run …`
command below installs the pinned dependencies on the fly. This is the path
verified on Python 3.13+/WSL where the pinned wheels are unavailable otherwise.

**Or a classic virtualenv (Python 3.11/3.12 only):**

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
| `GOOGLE_EMBEDDING_MODEL` | **Yes** | `models/gemini-embedding-001` — the Collection is built at the model's default **3072-dim** (see the dimension note below). Do **not** use the retired `models/embedding-001`. |
| `DATABASE_URL` | **Yes** | `postgresql+psycopg://postgres:postgres@localhost:5432/rag` — the `+psycopg` driver suffix is mandatory; a bare `postgresql://` selects psycopg2 and the app will fail. |
| `PG_VECTOR_COLLECTION_NAME` | **Yes** | Name for the pgVector Collection, e.g. `documents`. |
| `PDF_PATH` | **Yes** | Path to the PDF to ingest, e.g. `document.pdf` (committed at repo root). |
| `OPENAI_API_KEY` | No | Listed in `.env.example` for reference only — the app uses Gemini (ADR-0001). Leave blank. |
| `OPENAI_EMBEDDING_MODEL` | No | Same — not required. Leave blank. |

> **Embedding dimension note.** The code passes `output_dimensionality=768`
> intending the 768-dim Matryoshka (MRL) truncation described in ADR-0001, but
> the pinned `langchain-google-genai` honours that only as a per-call argument,
> not the constructor one — so the live Collection is built at the model's
> **default 3072-dim**. 768-dim *is* supported on the free tier; making the code
> actually emit it (a thin embeddings wrapper over both the ingest and search
> paths, normalization moot under cosine) is a possible follow-up, not part of
> this run. Both paths use the same client today, so they agree on 3072 and
> retrieval works.

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
# or, without managing a venv (pins Python 3.12):
uv run --no-project --python 3.12 --with-requirements requirements.txt python src/ingest.py
```

This reads the PDF at `PDF_PATH`, splits it into Chunks (1 000 chars, 150
overlap), embeds each Chunk with `models/gemini-embedding-001`, and stores the
Embeddings in the pgVector Collection. The script prints the total Chunk count
on success (e.g. `Stored 67 chunks in the collection.`). Re-running rebuilds the
Collection from scratch (`pre_delete_collection=True`) so it is safe to run
multiple times without duplicating Chunks.

> **Free-tier rate limits.** The Gemini free tier 429s on a large embedding
> burst, so ingestion embeds the Chunks in small batches with a short pause
> between them and retries a batch on a 429 (the per-minute window). The bundled
> 34-page PDF (~67 Chunks) takes roughly a minute or two; larger PDFs take
> proportionally longer. A paid tier raises the limits and makes the pauses
> effectively free. Tune `EMBED_BATCH_SIZE` / `EMBED_BATCH_PAUSE` in
> `src/ingest.py` if your tier differs.

### 5. Run the chat

```bash
python src/chat.py
# or, without managing a venv (pins Python 3.12):
uv run --no-project --python 3.12 --with-requirements requirements.txt python src/chat.py
```

The CLI prints `Faça sua pergunta:` and waits for a Question. Type a question
and press Enter to receive an Answer grounded in the ingested Document. If the
answer is not found in the Document, the Out-of-context fallback is returned
instead. Exit cleanly with an empty line, `Ctrl-D`, or `Ctrl-C`. For example,
against the bundled company-table PDF:

```text
Faça sua pergunta: Qual o faturamento da empresa Alfa Energia S.A.?
R$ 722.875.391,46
Faça sua pergunta: Qual é a capital da França?
Não tenho informações necessárias para responder sua pergunta.
```

The first answer is grounded in the Document; the second is the out-of-context
fallback (the Question is outside the Document's scope).

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
# or, without a venv (pins Python 3.12, injects pytest at gate time):
uv run --no-project --python 3.12 --with-requirements requirements.txt --with pytest pytest -q
```

The fast suite uses fakes — no network or database. The opt-in integration
tests (real Postgres + Gemini) skip themselves unless both `DATABASE_URL` and
`GOOGLE_API_KEY` are present in the environment.

## Key decisions

- **Gemini only** — `models/gemini-embedding-001` for Embeddings,
  `gemini-2.5-flash-lite` for answers. See
  [ADR-0001](docs/adr/0001-gemini-for-embeddings-and-answers.md).
- **Idempotent Ingestion** — every `ingest.py` run rebuilds the Collection;
  re-running is always safe.
- **Out-of-context fallback** — questions outside the Document's scope return a
  fixed fallback phrase rather than a hallucinated answer.
