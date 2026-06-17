---
status: accepted
---

# Use Google Gemini for embeddings and answer generation

The SPEC permits either OpenAI or Google Gemini for both the embedding model and
the answer LLM. We chose **Gemini** — `models/gemini-embedding-001` for Embeddings
and `gemini-2.5-flash-lite` for Answers — because its free tier is a good fit for a
solo postgraduate deliverable. The trade-off is less predictable rate limits than
OpenAI's paid API.

## Considered Options

- **Gemini** (chosen) — free tier, `GOOGLE_API_KEY`, `langchain-google-genai`.
- **OpenAI** — `text-embedding-3-small` + `gpt-5-nano`; more stable, but paid.
- **Support both via an env switch** — rejected as an unnecessary abstraction
  (YAGNI) for a single-deliverable project.

## Consequences

- `.env` uses `GOOGLE_API_KEY` and `GOOGLE_EMBEDDING_MODEL`;
  `langchain-google-genai` is the active provider package. (`langchain-openai`
  ships in `requirements.txt` but is unused — left in place rather than risk
  breaking the pinned lockfile.)
- The embedding model fixes the vector **dimension** of the Collection (3072 by
  default for `gemini-embedding-001`, or a truncated 768/1536). Switching providers
  or embedding models later is not just an API-key change — it requires dropping and
  re-ingesting the whole Collection.
- The SPEC's original `models/embedding-001` was **retired** (2025-10-30) and is
  superseded here by `models/gemini-embedding-001`. See
  [research](../research/gemini-langchain-google-genai.md).
