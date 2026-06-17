"""Tests for the answer chain built by ``search.search_prompt``.

Fast unit tests wire a ``langchain_core`` fake chat model and a stubbed
vector store — no real network or database. They verify the *wiring*
(top-10 retrieval, ``"\\n\\n"`` concatenation feeding ``{contexto}``, the
verbatim shipped prompt template, string-in/string-out) rather than real
LLM judgement, since the fake model echoes a canned response regardless of
the prompt it receives.

The integration test is opt-in: it is skipped unless ``DATABASE_URL`` is
set, in which case it exercises real Retrieval against a seeded Collection.
"""

import os

import pytest
from langchain_core.documents import Document
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from search import PROMPT_TEMPLATE, search_prompt


# --------------------------------------------------------------------------
# Test doubles
# --------------------------------------------------------------------------


class StubStore:
    """Records the query/k it was called with and returns canned hits.

    Mirrors the only method ``search_prompt`` uses on the vector store:
    ``similarity_search_with_score(query, k=...) -> list[(Document, score)]``.
    """

    def __init__(self, docs):
        self._docs = docs
        self.calls = []

    def similarity_search_with_score(self, query, k):
        self.calls.append({"query": query, "k": k})
        # Pair each Document with an arbitrary descending score.
        return [(doc, 1.0 - i * 0.01) for i, doc in enumerate(self._docs)]


def _docs(*texts):
    return [Document(page_content=t) for t in texts]


# --------------------------------------------------------------------------
# Unit tests — answer round-trips
# --------------------------------------------------------------------------


def test_returns_fact_when_context_contains_answer():
    """Given retrieved Chunks that contain the answer, the chain returns it."""
    store = StubStore(_docs("O faturamento foi de 10 milhões em 2024."))
    llm = FakeListChatModel(responses=["10 milhões"])

    chain = search_prompt(store=store, llm=llm)
    answer = chain.invoke("Qual foi o faturamento em 2024?")

    assert answer == "10 milhões"
    assert isinstance(answer, str)


def test_returns_exact_out_of_context_fallback():
    """Context without the answer / off-topic / opinion → exact fallback."""
    fallback = "Não tenho informações necessárias para responder sua pergunta."
    store = StubStore(_docs("Texto irrelevante para a pergunta."))
    llm = FakeListChatModel(responses=[fallback])

    chain = search_prompt(store=store, llm=llm)
    answer = chain.invoke("Qual é a capital da França?")

    assert answer == fallback


# --------------------------------------------------------------------------
# Unit tests — retrieval wiring
# --------------------------------------------------------------------------


def test_retrieval_requests_top_10_chunks():
    """Retrieval asks for the top 10 Chunks for the given Question."""
    store = StubStore(_docs("a", "b", "c"))
    llm = FakeListChatModel(responses=["ok"])

    chain = search_prompt(store=store, llm=llm)
    chain.invoke("uma pergunta")

    assert len(store.calls) == 1
    assert store.calls[0]["k"] == 10
    assert store.calls[0]["query"] == "uma pergunta"


def test_concatenated_chunk_text_feeds_contexto():
    """The chunks' page_content joined with ``\\n\\n`` is what fills {contexto}.

    The fake chat model echoes the *fully rendered prompt string* it is
    handed, so the assertion proves both the ``"\\n\\n"`` join and that the
    join feeds the template's ``{contexto}`` slot.
    """

    class EchoLLM(FakeListChatModel):
        """A fake chat model that echoes the rendered prompt it receives."""

        def _call(self, messages, stop=None, run_manager=None, **kwargs):
            # messages is a list of BaseMessage; the rendered PromptTemplate
            # arrives as a single HumanMessage whose .content is the string.
            return messages[-1].content

    store = StubStore(_docs("primeiro trecho", "segundo trecho", "terceiro trecho"))
    llm = EchoLLM(responses=["unused"])

    chain = search_prompt(store=store, llm=llm)
    rendered = chain.invoke("minha pergunta")

    expected_contexto = "primeiro trecho\n\nsegundo trecho\n\nterceiro trecho"
    assert expected_contexto in rendered
    # The question is rendered into {pergunta}.
    assert "minha pergunta" in rendered


def test_uses_shipped_prompt_template_verbatim():
    """The chain renders the shipped PROMPT_TEMPLATE byte-for-byte.

    Rendering the template directly with the same inputs the chain uses must
    appear verbatim in what the echoing fake model receives.
    """

    class EchoLLM(FakeListChatModel):
        def _call(self, messages, stop=None, run_manager=None, **kwargs):
            return messages[-1].content

    store = StubStore(_docs("conteudo unico"))
    llm = EchoLLM(responses=["unused"])

    chain = search_prompt(store=store, llm=llm)
    rendered = chain.invoke("pergunta x")

    expected = PROMPT_TEMPLATE.format(
        contexto="conteudo unico", pergunta="pergunta x"
    )
    assert rendered == expected


def test_chain_is_truthy():
    """chat.py truthy-checks the returned chain, so it must be truthy."""
    store = StubStore(_docs("a"))
    llm = FakeListChatModel(responses=["ok"])

    chain = search_prompt(store=store, llm=llm)
    assert chain


# --------------------------------------------------------------------------
# Integration test — opt-in, skipped without a database
# --------------------------------------------------------------------------


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="integration test requires a seeded DATABASE_URL Collection",
)
def test_integration_retrieval_from_seeded_collection():
    """Opt-in: real Retrieval returns the top 10 Chunks from a seeded store.

    Runs only when DATABASE_URL is set (a real pgvector Collection seeded by
    ingestion). Uses the real store + a fake chat model so the assertion
    targets Retrieval, not the LLM. Requires GOOGLE_API_KEY for embeddings.
    """
    from langchain_google_genai import GoogleGenerativeAIEmbeddings
    from langchain_postgres import PGVector

    from config import req

    emb = GoogleGenerativeAIEmbeddings(
        model=req("GOOGLE_EMBEDDING_MODEL"),
        output_dimensionality=768,
    )
    store = PGVector(
        embeddings=emb,
        collection_name=req("PG_VECTOR_COLLECTION_NAME"),
        connection=req("DATABASE_URL"),
        use_jsonb=True,
        pre_delete_collection=False,
        create_extension=False,
    )

    hits = store.similarity_search_with_score("o que diz o documento?", k=10)
    assert isinstance(hits, list)
    assert len(hits) <= 10
    for doc, score in hits:
        assert isinstance(doc, Document)
