"""PDF -> pgVector ingestion pipeline.

End-to-end path: read the Document, split it into Chunks of 1000
characters with 150 of overlap, embed each Chunk with Gemini, and store
them in the pgVector Collection. Re-running rebuilds the Collection from
scratch (``pre_delete_collection=True``) so Chunks never duplicate.

Injectability: ``ingest`` accepts an ``embeddings`` client and a
``store_factory`` so the fast unit tests pass fakes — no real network or
database is touched. The real LangChain components are imported lazily,
inside the default builders, so importing this module costs nothing and
the unit tests stay hermetic.

.env is loaded here — once, at the entry point — and never inside
imported modules such as config.py or search.py.
"""

import time

from dotenv import load_dotenv

from config import req

# Splitter parameters: 1000-char Chunks with 150-char overlap.
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150

# Gemini embedding model + dimensionality (see docs/adr/0001).
EMBEDDING_DIMENSIONS = 768

# Free-tier throttling: the Gemini embeddings API 429s on a large burst, so
# embed Chunks in small batches with a short pause between them. See the
# implement-rag-app skill's "Rate limits" note and docs/research.
EMBED_BATCH_SIZE = 5
EMBED_BATCH_PAUSE = 2.0

# A 429 on a batch is transient (the per-minute window) — wait this long for
# the window to clear, then retry the batch, up to this many times.
RATE_LIMIT_BACKOFF = 65.0
RATE_LIMIT_MAX_RETRIES = 4


def _is_rate_limit(exc: Exception) -> bool:
    # ponytail: match the 429 substring; the google client wraps it in a
    # generic error rather than a typed one. Tighten to a typed exception if
    # the client ever exposes one.
    return "429" in str(exc)


def _add_batch_with_retry(store, batch, sleep):
    """add_documents(batch), retrying on a rate-limit 429 with a backoff."""
    for attempt in range(RATE_LIMIT_MAX_RETRIES):
        try:
            store.add_documents(batch)
            return
        except Exception as exc:
            if not _is_rate_limit(exc) or attempt == RATE_LIMIT_MAX_RETRIES - 1:
                raise
            sleep(RATE_LIMIT_BACKOFF)


def split_into_chunks(documents):
    """Split *documents* into overlapping Chunks.

    Pure function — no network or database. Wraps
    ``RecursiveCharacterTextSplitter`` with the pinned Chunk size and
    overlap and returns the resulting ``list[Document]``.
    """
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )
    return splitter.split_documents(documents)


def _load_pdf(pdf_path):
    """Load a PDF into a ``list[Document]`` (lazy real-component import)."""
    from langchain_community.document_loaders import PyPDFLoader

    return PyPDFLoader(pdf_path).load()


def _default_embeddings():
    """Build the real Gemini embeddings client (lazy import).

    ``GOOGLE_API_KEY`` is auto-read from the environment by the client —
    it is not passed explicitly.
    """
    from langchain_google_genai import GoogleGenerativeAIEmbeddings

    return GoogleGenerativeAIEmbeddings(
        model=req("GOOGLE_EMBEDDING_MODEL"),
        output_dimensionality=EMBEDDING_DIMENSIONS,
    )


def _default_store_factory(embeddings):
    """Construct a fresh PGVector store for a clean rebuild (lazy import).

    ``pre_delete_collection=True`` wipes the Collection on construct, so
    each ingest run rebuilds from scratch and Chunks never duplicate. The
    connection string must use the ``postgresql+psycopg://`` prefix.
    """
    from langchain_postgres import PGVector

    return PGVector(
        embeddings=embeddings,
        collection_name=req("PG_VECTOR_COLLECTION_NAME"),
        connection=req("DATABASE_URL"),
        use_jsonb=True,
        pre_delete_collection=True,
    )


def ingest(
    *, pdf_path=None, documents=None, embeddings=None, store_factory=None, sleep=time.sleep
):
    """Run the ingestion pipeline and return the number of Chunks stored.

    Args:
        pdf_path: path to the PDF to ingest. Defaults to ``req("PDF_PATH")``.
        documents: pre-loaded ``list[Document]`` to ingest instead of
            loading a PDF. Lets unit tests stay hermetic.
        embeddings: embeddings client. Defaults to the real Gemini client.
        store_factory: callable ``embeddings -> store`` constructing a fresh
            vector store (clean rebuild). Defaults to the real PGVector
            factory.
        sleep: callable ``seconds -> None`` used to pause between embedding
            batches. Injectable so unit tests do not sleep for real.

    Required settings are read via ``config.req`` first, so a missing one
    raises ``SystemExit`` (fail-fast) before any loading or store build.

    Returns:
        int: the number of Chunks stored (``len(chunks)``).
    """
    # Fail fast on the required setting before any real work runs.
    if documents is None:
        if pdf_path is None:
            pdf_path = req("PDF_PATH")
        documents = _load_pdf(pdf_path)

    chunks = split_into_chunks(documents)

    if embeddings is None:
        embeddings = _default_embeddings()
    if store_factory is None:
        store_factory = _default_store_factory

    # Construct the store fresh each run → clean rebuild, no duplicate Chunks.
    store = store_factory(embeddings)

    # Embed in small batches with a pause between them: a single large burst
    # 429s on the Gemini free tier (the per-minute limit), while spacing the
    # batches keeps each request inside the window.
    for start in range(0, len(chunks), EMBED_BATCH_SIZE):
        batch = chunks[start : start + EMBED_BATCH_SIZE]
        _add_batch_with_retry(store, batch, sleep)
        if start + EMBED_BATCH_SIZE < len(chunks):
            sleep(EMBED_BATCH_PAUSE)

    count = len(chunks)
    print(f"Stored {count} chunks in the collection.")
    return count


if __name__ == "__main__":
    load_dotenv()
    ingest()
