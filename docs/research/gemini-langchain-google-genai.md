# Gemini via `langchain-google-genai==2.1.9` — brief

- **Scope:** Gemini embeddings + chat for RAG; model status, dimensions, rate limits.
- **Pinned:** `langchain-google-genai==2.1.9` (released 2025-08-04; legacy `google-ai-generativelanguage` SDK).
- **Gathered:** 2026-06-16.

## Verdict on `models/embedding-001` — RETIRED. Do not use.

`embedding-001` reached its **shutdown date 2025-10-30** per Google's official
deprecations page; `text-embedding-004` shuts down **2026-01-14** (effectively
gone). The SPEC/ROADMAP default `models/embedding-001` will **400 on a
retired/unknown model**.

**Current recommendation for this pin:** use **`models/gemini-embedding-001`** (GA),
the embedding model `2.1.9` documents and supports. (`gemini-embedding-2` is newer
than this package's SDK generation — the consolidated `google-genai` SDK only
arrives in `langchain-google-genai` 4.0.0 — so don't reach for it on 2.1.9.)

**Vector dimensions (drives the pgVector Collection):**

- `gemini-embedding-001`: default **3072**; truncatable to 128–3072 (recommended
  768 / 1536 / 3072) via `output_dimensionality`. Google says manually L2-normalize
  any non-3072 output — but with the store's default **COSINE** distance, ranking is
  scale-invariant, so a non-3072 dim works without manual normalization for cosine.
- `text-embedding-004` / `embedding-001`: 768 (both retired).

## Idioms (2.1.9)

```python
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI

emb = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-001",   # GOOGLE_API_KEY auto-read from env
    output_dimensionality=768,             # fixes Collection dim; cosine => no manual normalize
)
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash-lite",
    max_retries=6,        # honors 429 with exponential backoff
    timeout=60,
)
```

`GOOGLE_API_KEY` is auto-read by both classes — no need to pass `google_api_key=`.

## Pitfalls / rate limits (free tier)

- **`gemini-2.5-flash-lite` is valid** (released 2025-07-22) but **scheduled
  shutdown 2026-10-16** → successor `gemini-3.1-flash-lite`. Fine now; plan the swap.
- Free tier (verify in AI Studio; Google caps change): flash-lite ≈ **15 RPM /
  250k TPM / 1000 RPD**; embeddings ≈ **100 RPM / ~30k TPM / 1000 RPD**.
- **Surviving 429 on bulk ingest:** rely on built-in `max_retries` AND throttle —
  batch chunks (`embed_documents` takes a list) and sleep between batches:

```python
import time
for batch in chunked(chunks, 50):
    vectors = emb.embed_documents([c.page_content for c in batch])
    store.add_embeddings([c.page_content for c in batch], vectors)
    time.sleep(1.0)        # stay under the RPM ceiling
```

## Version notes vs pinned 2.1.9

Uses the legacy `google-ai-generativelanguage` SDK (NOT `google-genai`, which lands
in 4.0.0). `max_retries` and `output_dimensionality` are present. Prefix the
embedding model id with `models/`.

## Sources

- <https://ai.google.dev/gemini-api/docs/deprecations> — embedding-001 shutdown 2025-10-30; flash-lite shutdown 2026-10-16 (fetched 2026-06-16)
- <https://ai.google.dev/gemini-api/docs/embeddings> — 3072 default, normalize non-3072 (2026-06-16)
- <https://developers.googleblog.com/gemini-embedding-available-gemini-api/> — 2025-07
- <https://pypi.org/project/langchain-google-genai/2.1.9/> — 2025-08-04
