# Python slice — CLI RAG script

- **Scope:** the narrow, project-specific slice only — env loading, intra-`src/` imports, the CLI loop, per-call API resilience. (Not general Python hygiene.)
- **Pinned:** Python 3.11+, `python-dotenv==1.1.1`.
- **Gathered:** 2026-06-16.

## Idioms

**1. Env loading — load once at the entry point, fail-fast helper.** Call
`load_dotenv()` once at the top of each runnable script (`chat.py`, `ingest.py`),
NOT in imported `search.py` — env vars persist process-wide once set. Use
`find_dotenv()` so the repo-root `.env` resolves even though scripts live in `src/`.

```python
import os
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())   # walks up from caller's file → finds repo-root .env

def req(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        raise SystemExit(f"Missing required env var: {name} (set it in .env)")
    return v

GOOGLE_API_KEY = req("GOOGLE_API_KEY")
```

`SystemExit` prints the message and exits non-zero with no traceback.
**Trade-off:** `pydantic-settings` (transitively locked) is overkill for 5 flat
string vars — plain `os.environ` + `req()` wins here.

**2. Robust question loop.**

```python
while True:
    try:
        q = input("Faça sua pergunta: ").strip()
    except (EOFError, KeyboardInterrupt):   # Ctrl-D / Ctrl-C
        print(); break
    if not q:                                # empty line exits
        break
    # ... answer q
```

**3. Per-question API resilience.** Catch around the single call so one failure
doesn't kill the loop:

```python
    try:
        print(chain.invoke(q))
    except Exception as e:        # broad on purpose at the CLI boundary
        print(f"[erro na chamada à API: {e}] tente novamente.")
        continue
```

## Pitfalls

- **Script vs module.** `from search import search_prompt` works with
  `python src/chat.py` because `sys.path[0]` is the script's dir (`src/`). It
  **breaks** with `python -m src.chat` and under pytest. Guidance: run as
  `python src/chat.py` from the repo root — don't mix with `python -m`.
- Don't `load_dotenv()` inside `search.py`; double-loading is harmless but obscures
  ownership.
- Bare `KeyboardInterrupt` without catching leaves an ugly traceback — always pair
  it with `EOFError`.

## Sources

- <https://saurabh-kumar.com/python-dotenv/>
- <https://docs.python.org/3/library/sys.html#sys.path>
- <https://docs.python.org/3/library/functions.html#input>
