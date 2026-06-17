"""Tests for the PDF -> pgVector ingestion pipeline.

TDD: these tests are written RED (before the new functions exist in
src/ingest.py), then made GREEN by implementing them.

Fast unit tests use FAKES only — no real network access and no real
database. A real database is exercised only by the opt-in integration
test at the bottom, which skips itself unless DATABASE_URL (and a real
Gemini key) are present in the environment.
"""

import os

import pytest

# src/ is added to sys.path by the root conftest.py.
from langchain_core.documents import Document

from ingest import ingest, split_into_chunks


def _make_documents(text: str) -> list:
    """Wrap raw text in a single-element list[Document]."""
    return [Document(page_content=text)]


class FakeStore:
    """In-memory stand-in for PGVector.

    Models ``pre_delete_collection=True``: each construction wipes the
    shared backing list (clean rebuild on construct), so two ingest runs
    through the same factory leave the chunk count unchanged. A real
    PGVector deletes its collection rows on construct for the same reason.
    """

    def __init__(self, backing: list):
        self.backing = backing
        self.backing.clear()  # wipe on construct, like pre_delete_collection=True

    def add_documents(self, docs):
        self.backing.extend(docs)
        return [str(i) for i in range(len(docs))]


class TestSplitIntoChunks:
    """split_into_chunks() — pure, no external services."""

    def test_produces_multiple_chunks_for_long_input(self):
        text = " ".join(f"word{i}" for i in range(500))
        chunks = split_into_chunks(_make_documents(text))
        assert len(chunks) >= 2

    def test_each_chunk_respects_size_upper_bound(self):
        text = " ".join(f"word{i}" for i in range(500))
        chunks = split_into_chunks(_make_documents(text))
        assert all(len(c.page_content) <= 1000 for c in chunks)

    def test_returns_documents(self):
        text = " ".join(f"word{i}" for i in range(500))
        chunks = split_into_chunks(_make_documents(text))
        assert all(isinstance(c, Document) for c in chunks)

    def test_consecutive_chunks_overlap(self):
        # Unique tokens make a shared token between consecutive chunks a
        # genuine overlap signal (no periodicity false-positive).
        text = " ".join(f"word{i}" for i in range(500))
        chunks = split_into_chunks(_make_documents(text))
        assert len(chunks) >= 2
        first_tokens = set(chunks[0].page_content.split())
        second_tokens = set(chunks[1].page_content.split())
        assert first_tokens & second_tokens  # non-empty overlap

    def test_short_input_yields_single_chunk(self):
        chunks = split_into_chunks(_make_documents("a short sentence"))
        assert len(chunks) == 1
        assert chunks[0].page_content == "a short sentence"


class TestIngest:
    """ingest() orchestrator — fakes only, no network/DB."""

    def test_stores_chunks_in_the_collection(self):
        backing: list = []
        text = " ".join(f"word{i}" for i in range(500))
        docs = _make_documents(text)
        expected = len(split_into_chunks(docs))

        ingest(
            documents=docs,
            embeddings=object(),
            store_factory=lambda emb: FakeStore(backing),
        )

        assert len(backing) == expected
        assert expected >= 2  # guard: the input really did split

    def test_reports_number_of_chunks_stored(self):
        backing: list = []
        text = " ".join(f"word{i}" for i in range(500))
        docs = _make_documents(text)
        expected = len(split_into_chunks(docs))

        result = ingest(
            documents=docs,
            embeddings=object(),
            store_factory=lambda emb: FakeStore(backing),
        )

        assert result == expected

    def test_reports_count_to_stdout(self, capsys):
        backing: list = []
        text = " ".join(f"word{i}" for i in range(500))
        docs = _make_documents(text)
        expected = len(split_into_chunks(docs))

        ingest(
            documents=docs,
            embeddings=object(),
            store_factory=lambda emb: FakeStore(backing),
        )

        out = capsys.readouterr().out
        assert str(expected) in out

    def test_rebuild_leaves_chunk_count_unchanged(self):
        # The headline no-duplicate criterion. The factory is called every
        # run and each FakeStore construction clears the shared backing, so
        # a second run does NOT double the count. This goes red if ingest()
        # caches the store (factory called once) or skips the clean rebuild.
        backing: list = []
        text = " ".join(f"word{i}" for i in range(500))
        docs = _make_documents(text)

        def factory(emb):
            return FakeStore(backing)

        ingest(documents=docs, embeddings=object(), store_factory=factory)
        first_count = len(backing)

        ingest(documents=docs, embeddings=object(), store_factory=factory)
        second_count = len(backing)

        assert second_count == first_count
        assert second_count >= 2  # not the trivial empty-collection pass

    def test_fails_fast_when_required_setting_missing(self, monkeypatch):
        # PDF_PATH is req()'d first, before any load/build, so a missing
        # setting trips SystemExit (config.req) before any real work runs.
        monkeypatch.delenv("PDF_PATH", raising=False)
        with pytest.raises(SystemExit):
            ingest()

    def test_fail_fast_message_names_missing_setting(self, monkeypatch):
        monkeypatch.delenv("PDF_PATH", raising=False)
        with pytest.raises(SystemExit) as exc_info:
            ingest()
        assert "PDF_PATH" in str(exc_info.value)


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL") or not os.getenv("GOOGLE_API_KEY"),
    reason="requires a database and a real Gemini API key",
)
def test_integration_collection_is_populated_and_stable():
    """Opt-in: requires a real Postgres+pgvector DB and a Gemini key.

    Verifies the Collection is populated after ingestion and that a
    second run leaves the chunk count unchanged (clean rebuild, no
    duplicates).
    """
    from langchain_google_genai import GoogleGenerativeAIEmbeddings
    from langchain_postgres import PGVector

    from config import req

    # document.pdf lives at the worktree root (one level up from tests/).
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pdf_path = os.path.join(repo_root, "document.pdf")

    embeddings = GoogleGenerativeAIEmbeddings(
        model=req("GOOGLE_EMBEDDING_MODEL"),
        output_dimensionality=768,
    )
    collection = req("PG_VECTOR_COLLECTION_NAME")
    # DATABASE_URL must use the postgresql+psycopg:// prefix (psycopg3).
    connection = req("DATABASE_URL")

    def factory(emb):
        return PGVector(
            embeddings=emb,
            collection_name=collection,
            connection=connection,
            use_jsonb=True,
            pre_delete_collection=True,
        )

    first = ingest(pdf_path=pdf_path, embeddings=embeddings, store_factory=factory)
    assert first > 0

    second = ingest(pdf_path=pdf_path, embeddings=embeddings, store_factory=factory)
    assert second == first

    # The collection is queryable and populated after the rebuild.
    read_store = PGVector(
        embeddings=embeddings,
        collection_name=collection,
        connection=connection,
        use_jsonb=True,
        pre_delete_collection=False,
        create_extension=False,
    )
    hits = read_store.similarity_search("test", k=1)
    assert len(hits) >= 1
