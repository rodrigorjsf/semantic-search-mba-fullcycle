# Handoff: PRD #1 RAG-over-PDF — orchestrate run complete & merged

**Created:** 2026-06-18T00:31Z
**Branch:** `development` (in sync with `origin/development`, 0 ahead / 0 behind)
**Session Duration:** ~1h orchestrate run (2026-06-17 ~02:55–03:54Z) + follow-up Q&A

---

## Summary

The autonomous `/orchestrate 1` run for **PRD #1** (RAG-over-PDF CLI) is **complete and merged**.
All 5 agent slices (#2–#6) passed across 4 dependency waves; the final integration
PR **#13 has been merged** into `development` (`a703077`). The full app now lives on
`development`. The only remaining work is **human-side**: configure `.env` with real
credentials and run the app end-to-end against real Gemini + Postgres (tracked as the
still-open issue **#7**). There is one uncommitted, manual README edit in the tree.

---

## Work Completed

### Changes Made

- [x] Resumed the in-progress run `prd1-20260617-024032` and drove all 4 waves to done.
- [x] Slices #2–#6 implemented (TDD), reviewed (opus), gate-verified, squash-merged into the umbrella.
- [x] Final integration PR **#13** opened, then **merged** to `development` (app is live there).
- [x] Issues #2–#6 transitioned `ready-for-agent` → `ready-for-human`, now **CLOSED**.
- [x] Authoritative integrated verification: `31 passed, 2 skipped` on the umbrella tip.
- [x] 4 upstream plugin issues filed: `agent-engineering-toolkit#295, #332, #333, #334`.
- [x] `CLAUDE.md` Applied Learning bullets committed (`b797eb8`, pushed).
- [x] Project memory consolidated (new `orchestrate-run-gotchas.md` via `dreamer`).

### Key Decisions

| Decision | Rationale | Alternatives Considered |
| --- | --- | --- |
| Override `reverify-slice` `failed{build}` on #4 | It was a plugin false-negative (`build: not-configured` is tolerated everywhere else); empirically confirmed the merged worktree's tests passed (26) before proceeding | Treat as FAILED (would have cascade-skipped #5/#6 on a bug) |
| Re-spawn #3 implementer after socket crash | Transient API error left a clean worktree (no envelope, nothing landed) — infra hiccup, not a subagent verdict | Mark slice FAILED (wrong for a transient error) |
| `git config --local` identity | MCP git seam runs with `GIT_CONFIG_GLOBAL=/dev/null`, so global `~/.gitconfig` was invisible → `Author identity unknown` | Push/commit without identity (impossible) |

---

## Files Affected

### Created (via merged PR #13)
- `src/config.py` — `req(name)` fail-fast `.env` loader (raises `SystemExit` naming the missing var).
- `tests/test_config.py`, `tests/test_ingest.py`, `tests/test_search.py`, `tests/test_chat.py`, `tests/__init__.py`.
- `conftest.py` — adds `src/` to `sys.path` for pytest discovery.
- `requirements-dev.txt` — `pytest` (kept out of the pinned runtime `requirements.txt`).

### Modified (via merged PR #13)
- `src/ingest.py` — ingestion: `RecursiveCharacterTextSplitter` 1000/150 → Gemini `models/gemini-embedding-001` (768-dim) → PGVector `pre_delete_collection=True` clean rebuild; injectable embeddings + store; prints/returns chunk count.
- `src/search.py` — `search_prompt(store=None, llm=None)` returns a `RunnableLambda` whose `.invoke(question_str)` does top-10 `similarity_search_with_score` → `"\n\n".join` into `{contexto}` → **verbatim** `PROMPT_TEMPLATE` guardrail → `gemini-2.5-flash-lite` → answer string. Fallback: `"Não tenho informações necessárias para responder sua pergunta."`
- `src/chat.py` — `run_chat(answer_callable, input_fn, output_fn)` injectable CLI loop; clean exit on empty/EOF/Ctrl-C; per-question API-error resilience.
- `README.md` — full run guide + colored/animated Mermaid system-flow diagram.
- `CLAUDE.md` (commit `b797eb8`) — 2 Applied Learning bullets.

### Uncommitted (working tree, NOT mine — left as-is)
- `README.md` — one manual edit: the system-flow Mermaid header `flowchart LR` → `flowchart TB` (diagram orientation). Decide whether to commit or discard.

---

## Technical Context

### Architecture
Single-PDF RAG over LangChain 0.3.x + `langchain-postgres` PGVector 0.0.15 + Gemini, python-dotenv CLI.
`ingest.py` (one-shot ingestion) and `chat.py` (interactive loop) are entry points that
`load_dotenv()` in `__main__`; `config.py`/`search.py`/`ingest.py` never load dotenv at import.

### Configuration (`.env`, gitignored)
Five **required** settings (app fails fast if any is missing):
`GOOGLE_API_KEY`, `GOOGLE_EMBEDDING_MODEL` (`models/gemini-embedding-001`),
`DATABASE_URL` (**must** use `postgresql+psycopg://` — e.g. `postgresql+psycopg://postgres:postgres@localhost:5432/rag`),
`PG_VECTOR_COLLECTION_NAME`, `PDF_PATH` (`document.pdf` is committed at repo root).
`OPENAI_*` lines in `.env.example` are unused (ADR-0001 = Gemini only).

### Test gate
`uv run --no-project --python 3.12 --with-requirements requirements.txt --with pytest pytest -q`
(pytest injected at gate time; `requirements.txt` stays pytest-free). Homebrew Python 3.14 has no
wheels for the pins — never let the gate fall back to bare `python3`.

### Database
`docker compose up -d` → `postgres` (pgvector/pgvector:pg17, localhost:5432, postgres/postgres, db `rag`)
+ `bootstrap_vector_ext` (auto `CREATE EXTENSION vector`). Takes ~10–30s; `docker compose ps` to confirm healthy.

---

## Things to Know

### Gotchas & Pitfalls
- **Git identity must be `--local`** in this repo (the MCP git seam ignores global config). Already applied to `.git/config`; a fresh clone re-hits it.
- **`reverify-slice` false-fails on `not-configured` build** (upstream `#332`) — if you re-run orchestrate here, verify tests pass then override.
- **`DATABASE_URL` needs `postgresql+psycopg://`** — a bare `postgresql://` selects psycopg2 and fails.
- **`main` is the default branch, not `development`** — final-PR `Closes` keywords are inert; #2–#6 nonetheless got closed (manually/backstop).
- **`run-state.json` `resolvedRouting.fallback`** must be omitted (not `null`) for non-premium slices (upstream `#333`).

### Verification boundary (important for a graded deliverable)
`31 passed, 2 skipped` — the **2 skipped are the opt-in DB integration tests** for #3/#4.
**Real Gemini + PGVector were never exercised**; the guardrail/fallback are proven only against
fake chat models. "Tests green" ≠ "app proven end-to-end."

---

## Current State

### What's Working
- Full app merged on `development`; fast unit suite green (`31 passed, 2 skipped`).
- 3 run artifacts rendered: `.orchestrate/runs/prd1-20260617-024032/{dashboard,graph,report}.html`.
- Run checkpoint `status: completed`, schema-valid.

### What's Not Done (human-side)
- `.env` not created; real credentials not configured.
- App never run against real Gemini/Postgres (issue **#7** open).
- One uncommitted `README.md` diagram-orientation edit pending a decision.

### Tests
- [x] Unit (fakes, no network/DB): `31 passed, 2 skipped`.
- [ ] Opt-in integration (real DB + Gemini): never run.
- [ ] Manual end-to-end: not done (issue #7).

---

## Next Steps

### Immediate (Start Here)
1. **Decide the uncommitted `README.md` edit** (`flowchart LR`→`TB`): `git add README.md && git commit` it, or `git checkout -- README.md` to discard.
2. **Configure `.env`**: `cp .env.example .env`, then set `GOOGLE_API_KEY` (key from https://aistudio.google.com/apikey) and the other 4 required vars (see Technical Context). `.env` is gitignored.
3. **Run end-to-end** (this is issue **#7**):
   ```bash
   docker compose up -d            # wait until `docker compose ps` shows healthy
   python src/ingest.py            # ingest the PDF (prints chunk count)
   python src/chat.py              # ask questions; verify the out-of-context fallback
   ```

### Subsequent
- Run the opt-in integration tests once with real `DATABASE_URL` + `GOOGLE_API_KEY` set.
- Close PRD **#1** and **#7** once manual evaluation passes.

### Blocked On
- Nothing. A Google AI Studio API key + a running Docker are all that's needed.

---

## Related Resources

### Documentation / Links
- Final integration PR: `#13` (merged). Slice PRs: `#8`–`#12` (merged).
- Upstream plugin issues: `rodrigorjsf/agent-engineering-toolkit#295, #332, #333, #334`.
- Run artifacts: `.orchestrate/runs/prd1-20260617-024032/{dashboard,graph,report}.html`.
- Prior handoff (setup phase): `docs/handoffs/HANDOFF_ORCHESTRATE_START_PRD1.md`.

### Commands to Run
```bash
git diff README.md                          # inspect the uncommitted LR->TB edit
cp .env.example .env                         # then fill GOOGLE_API_KEY + the 4 others
docker compose up -d && docker compose ps    # start DB, confirm healthy
python src/ingest.py && python src/chat.py   # ingest, then chat
uv run --no-project --python 3.12 --with-requirements requirements.txt --with pytest pytest -q   # unit suite
```

### Search Queries
- `PROMPT_TEMPLATE` in `src/search.py` — the graded guardrail (keep verbatim).
- `def req` in `src/config.py` — the fail-fast env loader.
- `pre_delete_collection` in `src/ingest.py` — the clean-rebuild idiom.

---

## Open Questions
- [ ] Keep the README diagram as `flowchart TB` (the uncommitted edit) or revert to `LR`?
- [ ] Make `development` the default branch so future `Closes` keywords fire natively?

---

## Session Notes
The orchestrate run itself is fully concluded and durable; nothing about it needs re-running.
This handoff exists to carry the **human follow-up** (credentials + real end-to-end run = issue #7)
into a fresh session. Do not re-run `/orchestrate 1` — the run is `completed` and its issues are closed.

---

_Generated post-run as a checkpoint. Start a new session and use this document as initial context._
