# CLAUDE.md

Context for Claude Code sessions working on this repository.

## Project

Serverless AWS migration of my internship capstone
([movie-analytics-capstone](https://github.com/ronliwag/movie-analytics-capstone),
the archived as-submitted version; never modify it).

Pipeline: pandas → PySpark → dbt → Power BI, orchestrated by Airflow, moving
from local PostgreSQL to **S3 + Glue Data Catalog + Athena**
(region `ap-southeast-1`).

## Working agreement

- **I make all repo changes myself**: branches, commits, pushes, PRs, merges.
  Claude guides, explains, drafts content (as files or in chat), and reviews
  PRs. Claude does **not** commit, push, or create/delete branches.
- Explain AWS concepts just-in-time, when the current phase needs them.
- Never ask me to paste secrets (access keys, passwords) into chat.
- Progress tracking lives in Notion: "Movie Analytics — AWS Serverless
  Migration" → *Session handoff & working agreement*, *Phases*,
  *Learning Log*. Read the handoff page at the start of a session. At the
  end, update phase checkboxes/status and add Learning Log entries.

## Conventions

- Work happens in WSL at `~/movie-analytics-aws`.
- Branch per change (`feat/…`, `fix/…`, `chore/…`, `docs/…`), merged via PR.
- Commit messages: `type: short description` (feat, fix, chore, docs, refactor, test).
- AWS CLI profile: `movie-pipeline` (least-privilege; S3 `ron-movie-lake-*`,
  Athena workgroup `movie-analytics`, Glue databases `movie_*`).
- `data/` is gitignored; data lives in S3.
- Tests: `pytest scripts/pandas scripts/enrichment` (PySpark tests need Java).
