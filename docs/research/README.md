# Stack research — best-practices references

Version-pinned best-practices briefs for this project's stack, gathered
**2026-06-16** to ground the development harness (skills + rules). Each brief is
scoped to the exact **pinned** dependency version in `requirements.txt` — not
"latest". Consult these when in doubt about an idiom, an API signature, or a
deprecation.

| Brief | Scope | Key pin |
|-------|-------|---------|
| [langchain-rag.md](./langchain-rag.md) | RAG chain wiring (LCEL), loaders, splitters | `langchain==0.3.27` |
| [pgvector-langchain-postgres.md](./pgvector-langchain-postgres.md) | `PGVector` store API, connection string, footguns | `langchain-postgres==0.0.15` |
| [gemini-langchain-google-genai.md](./gemini-langchain-google-genai.md) | Gemini embeddings + chat, model status, rate limits | `langchain-google-genai==2.1.9` |
| [python-cli-slice.md](./python-cli-slice.md) | dotenv config, CLI loop, intra-`src/` imports | `python-dotenv==1.1.1` |

> ⚠️ **Headline finding:** Gemini `models/embedding-001` is **retired** (shutdown
> 2025-10-30). Use **`models/gemini-embedding-001`**. See the Gemini brief.

Each brief is a point-in-time snapshot. Re-verify against official docs if a pin
changes or a model is deprecated.
