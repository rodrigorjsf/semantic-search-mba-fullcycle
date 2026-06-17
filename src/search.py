PROMPT_TEMPLATE = """
CONTEXTO:
{contexto}

REGRAS:
- Responda somente com base no CONTEXTO.
- Se a informação não estiver explicitamente no CONTEXTO, responda:
  "Não tenho informações necessárias para responder sua pergunta."
- Nunca invente ou use conhecimento externo.
- Nunca produza opiniões ou interpretações além do que está escrito.

EXEMPLOS DE PERGUNTAS FORA DO CONTEXTO:
Pergunta: "Qual é a capital da França?"
Resposta: "Não tenho informações necessárias para responder sua pergunta."

Pergunta: "Quantos clientes temos em 2024?"
Resposta: "Não tenho informações necessárias para responder sua pergunta."

Pergunta: "Você acha isso bom ou ruim?"
Resposta: "Não tenho informações necessárias para responder sua pergunta."

PERGUNTA DO USUÁRIO:
{pergunta}

RESPONDA A "PERGUNTA DO USUÁRIO"
"""

from langchain_core.runnables import RunnableLambda


def search_prompt(store=None, llm=None):
    """Build the invokable answer chain with the out-of-context guardrail.

    Returns an object whose ``.invoke(question: str) -> str`` runs the full
    pipeline: retrieve the 10 most similar Chunks, concatenate their text
    into ``{contexto}``, render the shipped ``PROMPT_TEMPLATE`` verbatim,
    call the Gemini answer model, and return the Answer string.

    Args:
        store: A vector store exposing
            ``similarity_search_with_score(query, k) -> list[(Document, score)]``.
            When ``None``, a real read-only ``PGVector`` is built from env.
        llm: A chat model. When ``None``, a real
            ``ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite")`` is built.

    The vector store and chat model are injectable so fast unit tests can
    pass a stubbed store and a ``langchain_core`` fake chat model. Called
    with no arguments (as ``chat.py`` does), it builds the real components.
    """
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.prompts import PromptTemplate

    if store is None:
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        from langchain_postgres import PGVector

        from config import req

        embeddings = GoogleGenerativeAIEmbeddings(
            model=req("GOOGLE_EMBEDDING_MODEL"),
            output_dimensionality=768,
        )
        store = PGVector(
            embeddings=embeddings,
            collection_name=req("PG_VECTOR_COLLECTION_NAME"),
            connection=req("DATABASE_URL"),
            use_jsonb=True,
            pre_delete_collection=False,
            create_extension=False,
        )

    if llm is None:
        from langchain_google_genai import ChatGoogleGenerativeAI

        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash-lite",
            max_retries=6,
            timeout=60,
        )

    inner = PromptTemplate.from_template(PROMPT_TEMPLATE) | llm | StrOutputParser()

    def answer(question: str) -> str:
        hits = store.similarity_search_with_score(question, k=10)
        contexto = "\n\n".join(doc.page_content for doc, _score in hits)
        return inner.invoke({"contexto": contexto, "pergunta": question})

    return RunnableLambda(answer)