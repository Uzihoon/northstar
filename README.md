# Northstar

Northstar is a local-first AI travel planner monorepo.

## Apps

- `apps/api` - Python/FastAPI backend, Ollama agent, RAG, Postgres persistence, evals, and smoke scripts.
- `apps/mobile` - Mobile app workspace placeholder.

## Backend Commands

Run backend commands from `apps/api`:

```bash
cd apps/api
uv run pytest -q
uv run uvicorn northstar.api.app:app --reload
uv run alembic upgrade head
```

## Mobile

The mobile app will live in `apps/mobile` and talk to the backend through the API contracts in `apps/api`.
