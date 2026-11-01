@AGENTS.md

## Claude Code specifics
- Use plan mode for anything touching the job lifecycle or schema type system.
- Run `make lint test` before declaring a task finished.
- Subdirectory rules: `backend/AGENTS.md` and `frontend/AGENTS.md` apply when working there — read them first.
- Prefer small, reviewable diffs; one concern per commit.
