# Roadmap — Semantic Search over a PDF

Living document. Keep it in sync with the code: when a phase lands, flip its box
to ✅ here and reflect any behavior change in `README.md` in the same commit.

Vocabulary follows [`CONTEXT.md`](../CONTEXT.md). Provider choice is recorded in
[ADR-0001](./adr/0001-gemini-for-embeddings-and-answers.md). Version-pinned
stack best-practices live in [`docs/research/`](./research/).

## What we are building

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

## Phases

```mermaid
flowchart LR
    P0["P0 · Environment<br/>& infra"] p1@==> P1["P1 · Ingestion<br/>src/ingest.py"]
    P1 p2@==> P2["P2 · Search chain<br/>src/search.py"]
    P2 p3@==> P3["P3 · CLI chat<br/>src/chat.py"]
    P3 p4@==> P4["P4 · README<br/>(living)"]
    P4 p5@==> P5["P5 · Verify<br/>& deliver"]

    p1@{ animate: true }
    p2@{ animate: true }
    p3@{ animate: true }
    p4@{ animate: true }
    p5@{ animate: true }

    classDef done fill:#14532d,stroke:#22c55e,color:#f0fdf4;
    class P0,P1,P2,P3,P4,P5 done;
```

Status legend: ⬜ todo · 🟦 in progress · ✅ done. **All phases are ✅ done** —
the app is implemented, merged to `development`, and verified end-to-end against
real Gemini + Postgres (ingestion, in-context retrieval, and the out-of-context
fallback all confirmed).

---

### ✅ P0 — Environment & infra

The scaffold (docker-compose, requirements, `.env.example`, `document.pdf`, src
stubs) is already in the repo. This phase makes it runnable.

- Create and activate a venv; `pip install -r requirements.txt`.
- Copy `.env.example` → `.env` and fill:
  - `GOOGLE_API_KEY=<your key>`
  - `GOOGLE_EMBEDDING_MODEL=models/gemini-embedding-001` — the SPEC's
    `models/embedding-001` is **retired** (research-confirmed); see the
    [Gemini brief](./research/gemini-langchain-google-genai.md).
  - `DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/rag`
    — note the **`+psycopg`** driver suffix; `langchain-postgres` needs psycopg3.
  - `PG_VECTOR_COLLECTION_NAME=documents`
  - `PDF_PATH=document.pdf`
- `docker compose up -d` — starts Postgres and runs `bootstrap_vector_ext`
  (`CREATE EXTENSION vector`).

**Done when:** `docker compose ps` shows `postgres_rag` healthy, and a `psql`
connection lists the `vector` extension.

### ✅ P1 — Ingestion (`src/ingest.py`)

- Load the Document with `PyPDFLoader(PDF_PATH)`.
- Split with `RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)`.
- Embeddings: `GoogleGenerativeAIEmbeddings(model=GOOGLE_EMBEDDING_MODEL,
  output_dimensionality=768)` — `gemini-embedding-001` defaults to 3072 dims.
  The 768 intent (lean Collection, normalization moot under cosine) is **not
  applied** by the pinned client, which honours `output_dimensionality` only as a
  per-call argument; the live Collection is 3072-dim. See the README dimension note.
- Embed in small batches with a pause + a 429 retry (`EMBED_BATCH_SIZE` /
  `EMBED_BATCH_PAUSE` in `ingest.py`) so the Gemini **free tier** survives a
  full-PDF ingest without hitting the per-minute rate limit.
- Store with `PGVector(embeddings=…, collection_name=…, connection=DATABASE_URL,
  use_jsonb=True, pre_delete_collection=True)` — note `embeddings=` is plural &
  keyword-only. **Recreate the Collection each run** (`pre_delete_collection=True`)
  so re-running never duplicates Chunks (decision locked below).

**Done when:** `python src/ingest.py` populates the Collection (row count > 0),
and running it a second time leaves the count unchanged.

### ✅ P2 — Search chain (`src/search.py`)

- Implement `search_prompt()` to build and return a callable chain that, given a
  Question: embeds it → `similarity_search_with_score(question, k=10)` →
  concatenates the 10 Chunk texts into `{contexto}` → fills the shipped
  `PROMPT_TEMPLATE` → calls `ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite")`
  → returns the Answer text.
- Keep `PROMPT_TEMPLATE` verbatim — it is the graded guardrail.
- ⚠️ Construct `PGVector` here **read-only** — leave `pre_delete_collection` at its
  default (`False`). Reusing P1's `True` would wipe the Collection you are querying.

**Done when:** invoking the chain with a known-answer Question returns the fact,
and with an out-of-context Question returns the exact Out-of-context fallback.

### ✅ P3 — CLI chat (`src/chat.py`)

- Build the chain once via `search_prompt()`, then loop: print
  `Faça sua pergunta:`, read input, invoke the chain, print the Answer; repeat
  until EOF / empty line / Ctrl-C.

**Done when:** an interactive session reproduces the SPEC example — answers a
known question and returns the fallback for an out-of-context one.

### ✅ P4 — README (living)

- Replace the README placeholder with real run instructions matching the SPEC
  "Ordem de Execução": venv → `.env` → `docker compose up -d` →
  `python src/ingest.py` → `python src/chat.py`. Embed the system-flow diagram.

**Done when:** a fresh reader can run the project end-to-end from the README alone.

### ✅ P5 — Verify & deliver

- Clean end-to-end run: `docker compose down -v` → `up -d` → ingest → chat,
  testing **both** a known-answer Question and an out-of-context Question.
- Confirm the public GitHub repo is the deliverable (code + README).

**Done when:** both question types behave correctly on a from-scratch run.

---

## Decisions locked

- **Provider: Gemini** — see [ADR-0001](./adr/0001-gemini-for-embeddings-and-answers.md).
- **Ingestion is idempotent by rebuild** — `ingest.py` recreates the Collection
  on every run (`pre_delete_collection=True`); no `--reset` flag.
- **`search.py` / `chat.py` boundary** — `search.py` owns retrieval + prompt +
  LLM and exports `search_prompt()`; `chat.py` is a thin CLI loop. Matches the
  scaffold and the SPEC's run order (only `ingest.py` and `chat.py` are invoked).
- **`document.pdf` is committed** — from the Full Cycle template; the repo stays
  reproducible and gradeable.

## Risks to confirm at runtime

All resolved — research-confirmed up front, then verified against the live key
on the end-to-end run:

- ✅ **`models/embedding-001` is retired** (shutdown 2025-10-30, research-confirmed)
  — already switched to `models/gemini-embedding-001` across `.env.example`, P0/P1,
  and ADR-0001. See the [Gemini brief](./research/gemini-langchain-google-genai.md).
- ✅ **`gemini-2.5-flash-lite` + `gemini-embedding-001` access** — confirmed
  against a live **free-tier** key: ingestion, in-context retrieval, and the
  out-of-context fallback all run end-to-end.
- ✅ **Free-tier rate limit** — the one real runtime constraint found: a full-PDF
  embedding burst 429s, mitigated by the batch+pause+retry throttle in `ingest.py`
  (see README step 4). A paid tier raises the ceiling.

## Deferred / minor

- The LLM model id is hardcoded in `search.py` (P2). Promote to a
  `GOOGLE_CHAT_MODEL` env var only if a second model is ever needed (YAGNI).
- `langchain-openai` stays unused in `requirements.txt` (see ADR-0001).
- Context separator when concatenating the 10 Chunks into `{contexto}` (`\n\n`),
  collection name value, and Python version (3.11+ for the pinned deps) are
  decide-inline details, not open decisions.
