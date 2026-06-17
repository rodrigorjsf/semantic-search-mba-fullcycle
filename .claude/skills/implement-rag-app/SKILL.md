---
name: implement-rag-app
description: Version-pinned cheat-sheet of patterns and footguns for implementing this RAG-over-PDF app (LangChain 0.3.x + langchain-postgres PGVector + Gemini + python-dotenv CLI). Use when implementing or editing src/ingest.py, src/search.py, or src/chat.py, wiring the LCEL chain, configuring PGVector, choosing the Gemini embedding/chat model, or building the CLI question loop.
---

# Implement this RAG-over-PDF app

Cheat-sheet for `src/ingest.py`, `src/search.py`, `src/chat.py`. Pinned stack:
LangChain 0.3.27, langchain-postgres 0.0.15, langchain-google-genai 2.1.9,
python-dotenv 1.1.1. Sources + depth: [`docs/research/`](../../../docs/research/).

> **Mandatory:** all implementation here is driven through the `/tdd` skill
> (red-green-refactor) — no exceptions. This cheat-sheet is the *what* (patterns);
> `/tdd` is the *how* (process). Write the failing test first.

## Footguns (these are the usual mistakes — get them right)

- **PGVector** is imported from `langchain_postgres`, NOT
  `langchain_community.vectorstores`. The constructor arg is `embeddings=`
  (plural, keyword-only).
- **`pre_delete_collection`** deletes the collection **on construct**. Set it
  `True` only in `ingest.py` (clean rebuild, kills duplicate chunks). In
  `search.py` keep it `False` (default) plus `create_extension=False`, otherwise
  querying wipes the data you just ingested.
- **Connection string** needs the psycopg3 prefix: `postgresql+psycopg://…`. A
  bare `postgresql://` selects the psycopg2 dialect → `ModuleNotFoundError`.
- **Embedding model is `models/gemini-embedding-001`** — `models/embedding-001`
  is retired and 400s. Default dim 3072; pass `output_dimensionality=768` to keep
  the Collection lean (cosine distance makes normalization moot).
- **The chain is LCEL**: `prompt | llm | StrOutputParser()` + `.invoke(...)`.
  Never `LLMChain`, `RetrievalQA`, `.run()`, or `.__call__`.
- Use `similarity_search_with_score(q, k=10)` and concat `page_content` yourself —
  a retriever Runnable drops the scores.
- In `PROMPT_TEMPLATE`, escape any literal brace as `{{`/`}}`; only `{contexto}`
  and `{pergunta}` are template variables.
- `GOOGLE_API_KEY` is auto-read from the env — don't pass `google_api_key=`.
- `load_dotenv(find_dotenv())` once at the top of `ingest.py` and `chat.py`, never
  in `search.py`. Run as `python src/chat.py` from the repo root (not `python -m`).

## Quick start

**Ingest — rebuild each run:**
```python
emb = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001", output_dimensionality=768)
store = PGVector(embeddings=emb, collection_name=COLL, connection=DATABASE_URL,
                 use_jsonb=True, pre_delete_collection=True)
chunks = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150) \
    .split_documents(PyPDFLoader(PDF_PATH).load())
store.add_documents(chunks)
```

**Search — read-only store + LCEL chain:**
```python
store = PGVector(embeddings=emb, collection_name=COLL, connection=DATABASE_URL,
                 use_jsonb=True, pre_delete_collection=False, create_extension=False)
prompt = PromptTemplate.from_template(PROMPT_TEMPLATE)   # {contexto} {pergunta}
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", max_retries=6, timeout=60)
chain = prompt | llm | StrOutputParser()

def answer(question):
    hits = store.similarity_search_with_score(question, k=10)
    contexto = "\n\n".join(doc.page_content for doc, _score in hits)
    return chain.invoke({"contexto": contexto, "pergunta": question})
```

**Chat — survives bad input and per-question API errors:**
```python
while True:
    try: q = input("Faça sua pergunta: ").strip()
    except (EOFError, KeyboardInterrupt): print(); break
    if not q: break
    try: print(answer(q))
    except Exception as e: print(f"[erro: {e}] tente novamente.")
```

## Rate limits (free tier)

flash-lite ≈ 15 RPM, embeddings ≈ 100 RPM. For bulk ingest, batch
`embed_documents` and `time.sleep(1.0)` between batches; `max_retries=6` handles
429 backoff. Details in the
[Gemini brief](../../../docs/research/gemini-langchain-google-genai.md).

## Deeper

[LangChain RAG](../../../docs/research/langchain-rag.md) ·
[PGVector](../../../docs/research/pgvector-langchain-postgres.md) ·
[Gemini](../../../docs/research/gemini-langchain-google-genai.md) ·
[Python CLI](../../../docs/research/python-cli-slice.md)
