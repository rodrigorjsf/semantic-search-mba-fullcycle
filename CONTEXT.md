# Semantic Search over a PDF

A command-line assistant that answers questions using *only* the content of a
single PDF. Content is ingested into a pgVector store once, then retrieved and
fed to an LLM that is constrained to never answer from outside that content.

## Language

**Document**:
The single source PDF whose content is the only knowledge the system may use to
answer. There is exactly one.
_Avoid_: corpus, knowledge base, dataset.

**Chunk**:
A contiguous slice of the Document that is embedded and stored as one
retrievable unit.
_Avoid_: segment, passage, fragment.

**Embedding**:
The numeric vector that represents the meaning of a Chunk or of a Question.
_Avoid_: vector, encoding.

**Ingestion**:
The one-shot process that reads the Document, splits it into Chunks, embeds
them, and stores them in the Collection. Re-running it rebuilds the Collection
from scratch.
_Avoid_: indexing, import, loading.

**Collection**:
The named set of stored Chunk Embeddings in pgVector that Retrieval searches
over.
_Avoid_: index, table, store.

**Retrieval**:
Selecting the Chunks whose Embeddings are most similar to a Question's
Embedding.
_Avoid_: search, lookup.

**Question**:
The user's natural-language input typed at the CLI.
_Avoid_: query, prompt — the prompt is the assembled LLM input, not the
Question.

**Out-of-context fallback**:
The fixed Answer returned when the Document does not contain the requested
information: "Não tenho informações necessárias para responder sua pergunta."
_Avoid_: error, refusal, "I don't know".
