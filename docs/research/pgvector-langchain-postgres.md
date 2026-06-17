# PGVector in `langchain-postgres==0.0.15` — brief

- **Scope:** the `PGVector` vector store API used by `ingest.py` (rebuild) and `search.py` (query).
- **Pinned:** `langchain-postgres==0.0.15`, `pgvector==0.3.6`, psycopg3, SQLAlchemy 2.0.43; DB image `pgvector/pgvector:pg17`.
- **Gathered:** 2026-06-16.

## Idioms

**Constructor (exact, 0.0.15):**
`PGVector(embeddings=, *, connection=None, embedding_length=None, collection_name="langchain", collection_metadata=None, distance_strategy=COSINE, pre_delete_collection=False, logger=None, relevance_score_fn=None, engine_args=None, use_jsonb=True, create_extension=True, async_mode=False)`.
Note `embeddings=` is **plural & keyword-only**; the `from_documents`/`from_texts`
classmethods use `embedding=` **singular**.

**Ingest (rebuild each run):**

```python
store = PGVector(
    embeddings=emb, collection_name="rag",
    connection="postgresql+psycopg://postgres:postgres@localhost:5432/rag",
    use_jsonb=True, pre_delete_collection=True)   # wipes collection on construct
store.add_documents(docs)
```

**Query (read-only intent):**

```python
store = PGVector(
    embeddings=emb, collection_name="rag",
    connection="postgresql+psycopg://postgres:postgres@localhost:5432/rag",
    use_jsonb=True, pre_delete_collection=False, create_extension=False)
store.similarity_search_with_score(query, k=10)
```

## Pitfalls

- **No truly read-only construct.** Every sync construct runs `__post_init__` →
  `create_tables_if_not_exists()` + `create_collection()` unconditionally.
  `create_extension=False` only suppresses `CREATE EXTENSION` (use it since the
  `vector` extension is pre-created by docker-compose); the instance still issues
  `CREATE TABLE IF NOT EXISTS` + collection get-or-create.
- **`pre_delete_collection=True` deletes on construct**, not on first write. The
  query instance must keep it `False`, else querying wipes the data just ingested.
  FK is `ondelete="CASCADE"` — deleting the collection row drops all its embeddings.
- **Connection prefix must be `postgresql+psycopg://`** (psycopg3). Bare
  `postgresql://` makes SQLAlchemy pick the psycopg2 dialect → driver
  `ModuleNotFoundError`.
- **Re-running duplicates.** Without supplied ids, each `add_documents` run
  generates fresh `uuid4` → duplicate rows. `pre_delete_collection=True` is the
  clean-rebuild path; `from_documents(...)` just wraps construct+add.
- **No ANN index.** 0.0.15 creates no HNSW/IVFFlat index; similarity is exact
  sequential scan. Fine for k=10 on one small PDF; add HNSW manually only at scale
  (requires `embedding_length` set).

## Version notes vs pinned

- All above is `langchain_postgres.PGVector` (0.0.15). The deprecated
  `langchain_community.vectorstores.PGVector` takes `connection_string=`
  (psycopg2-era) — any tutorial using `connection_string=` is the **wrong class**.
- The 0.0.15 README pushes a newer `PGVectorStore` + `PGEngine` API; ignore it —
  our code path is `PGVector`.

## Sources

- <https://github.com/langchain-ai/langchain-postgres/blob/langchain-postgres%3D%3D0.0.15/langchain_postgres/vectorstores.py>
- <https://github.com/langchain-ai/langchain-postgres/blob/langchain-postgres%3D%3D0.0.15/README.md>
