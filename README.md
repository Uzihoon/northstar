# Northstar

Northstar is a local-first AI travel planner monorepo.

## Apps

- `apps/api` - Python/FastAPI backend, Ollama agent, RAG, Postgres persistence, evals, and smoke scripts.
- `apps/mobile` - Expo React Native mobile app for onboarding, destination discovery, trip setup, and itinerary summaries.

## Backend Commands

Run backend commands from `apps/api`:

```bash
cd apps/api
uv run pytest -q
uv run uvicorn northstar.api.app:app --reload
uv run alembic upgrade head
```

## Mobile Commands

Run mobile commands from `apps/mobile`:

```bash
cd apps/mobile
npm install
cp .env.example .env
npm run ios
```
