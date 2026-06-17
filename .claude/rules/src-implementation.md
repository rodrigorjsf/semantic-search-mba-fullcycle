---
paths:
  - "src/**/*.py"
---

# Implementing code in `src/`

- Drive every change through the `/tdd` skill (red-green-refactor): write a failing test first, make it pass, then refactor. No implementation code is written without a failing test first — mandatory for all of `src/` (see root `CLAUDE.md`).
- Before writing or editing chain, `PGVector`, embedding, or CLI code, consult the `implement-rag-app` skill for the version-pinned patterns and footguns, and `docs/research/` for the sources.
