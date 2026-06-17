# LangChain 0.3.x — RAG chain brief

- **Scope:** wiring a retrieval→prompt→LLM chain for this app.
- **Pinned:** `langchain==0.3.27`, `langchain-core==0.3.74`, `langchain-text-splitters==0.3.9`, `langchain-community==0.3.27`.
- **Gathered:** 2026-06-16.

## Idioms

**1. LCEL chain (this app — scores preserved, manual concat).** Because we use
`similarity_search_with_score(query, k=10)`, do NOT use a retriever Runnable (it
drops scores). Format docs to a string ourselves, then pipe:

```python
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

prompt = PromptTemplate.from_template(PROMPT_TEMPLATE)   # has {contexto} {pergunta}
chain = prompt | llm | StrOutputParser()                # llm = ChatGoogleGenerativeAI

results = store.similarity_search_with_score(question, k=10)
contexto = "\n\n".join(doc.page_content for doc, _score in results)
answer = chain.invoke({"contexto": contexto, "pergunta": question})  # -> str
```

**2. Custom multi-line template → PromptTemplate.** `from_template` auto-detects
`{contexto}`/`{pergunta}` as input variables; no manual `input_variables=` needed.
Use `PromptTemplate`, not `ChatPromptTemplate`, for a single rendered string (chat
models accept it fine).

**3. Loader + splitter (0.3.x import paths).**

```python
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

docs = PyPDFLoader("document.pdf").load()              # list[Document], one per page
splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
chunks = splitter.split_documents(docs)                # preserves metadata
```

## Pitfalls

- **Avoid `LLMChain`** (deprecated 0.1.17) → `prompt | llm | StrOutputParser()`.
- **Avoid `RetrievalQA` / `ConversationalRetrievalChain` / `load_qa_chain`**
  (deprecated 0.1.17) → LCEL. Our score-based concat is already the LCEL-correct path.
- **Avoid `chain(...)` / `.__call__` / `.run()` / `.predict()`** → use `.invoke()`.
- **PGVector** import from `langchain_postgres`, NOT the deprecated
  `langchain_community.vectorstores.PGVector`.
- `from_template` treats literal braces as variables — escape them as `{{` / `}}`.

## Version notes vs pinned

- `prompt | llm | StrOutputParser()` is stable 0.2 → 0.3 → 1.0 — safe.
- `LLMChain`/`RetrievalQA` deprecations are **active** in 0.3.x (emit warnings).
- **1.0 trap:** `python.langchain.com` now redirects to v1.0 docs. Tutorials showing
  `create_agent` / `langchain.agents` v1 imports are NOT our era. The import paths
  above are unchanged 0.3 ↔ 1.0.

## Sources

- <https://docs.langchain.com/oss/python/migrate/langchain-v1>
- <https://reference.langchain.com/python/langchain_text_splitters/>
- <https://www.aurelio.ai/learn/langchain-lcel>
