# RAG Research Pipeline Design

## Goal

Build a semi-automated research pipeline that can backfill or refresh Northstar travel knowledge for a country/city, while separating durable planning knowledge from fresh, specific options.

## Product Workflow

Northstar should let us choose a country/city to research or refresh. By default, it researches broad destination themes such as overview, neighborhoods, cafes, restaurants, sightseeing, transport, and accommodation. It should also support a narrower theme-only run, such as cafes only, and optional trusted URLs supplied by the operator.

The pipeline uses a research agent to search the web freely, prioritizing trusted URLs and trusted domains when available. A second critic LLM reviews the gathered evidence, assigns trust ratings, and blocks unsupported or unsafe items. Everything except blocked output can be stored, but all stored content must keep source URLs, freshness metadata, and trust labels.

Later, an admin dashboard can show research runs, trust ratings, blocked items, published versions, and rollback actions. The v1 implementation can be CLI/API-first and dashboard-ready without building the dashboard yet.

## Data Model Split

Long-term destination knowledge goes to RAG notes:

- City overview and traveler fit
- Neighborhood and area guidance
- Transit patterns and planning caveats
- Sightseeing strategy
- Food and dietary caveats
- Budget-level guidance
- Common mistakes
- Stable itinerary heuristics

Short-term or specific options go to a candidate table:

- Cafes
- Restaurants
- Hotels and accommodations
- Shops or bookstores when useful
- Specific attractions when freshness matters
- Booking, reservation, official, or source links
- Trust rating, price level, and last checked timestamp

This keeps RAG focused on planning wisdom and keeps specific options filterable, refreshable, auditable, and available to the agent through safe database-backed tools.

## Research Flow

```text
research-city Kyoto --country Japan
-> create research run
-> generate theme-specific search plans
-> prioritize trusted URLs and trusted domains
-> freely search the web for missing coverage
-> fetch accepted pages
-> extract clean source text
-> generate stable Markdown notes
-> generate structured place candidates
-> run deterministic validation
-> run critic LLM review
-> exclude blocked items
-> publish RAG notes
-> replace/re-ingest RAG chunks for published notes
-> store non-blocked candidates with trust labels
-> store run report, source snapshots, and review decisions
```

## Trust Ratings

Use four trust ratings:

- `high`: official source, reputable platform, or multiple strong independent confirmations.
- `medium`: reputable source with plausible supporting evidence.
- `low`: single useful source or weak support, included with caution.
- `blocked`: unsupported, suspicious, contradicted, inaccessible, or not useful enough to store.

The planner can use `high`, `medium`, and `low`, but must preserve labels in reasoning and user-facing links when appropriate. `blocked` output is retained in research reports for auditing but is not published to RAG or candidate search.

## Freshness Rules

Exact prices, exact opening hours, closures, current availability, event schedules, and booking availability are live facts. They should not become durable RAG claims.

Use price levels instead of exact prices:

- `free`
- `budget`
- `moderate`
- `expensive`
- `luxury`
- `varies`

Candidate records should include `last_checked_at` and source URLs. During itinerary planning, the agent can call a future freshness tool to re-check important URLs before recommending specific options.

## Agent Tooling

The LLM should not receive raw database access. It should receive safe tools:

- `search_rag_notes`: retrieve stable planning knowledge from RAG.
- `search_candidates`: search specific cafes, restaurants, accommodations, and other options.
- `get_candidate_details`: inspect one candidate with sources and review metadata.
- `freshness_check_url`: fetch or verify a candidate URL before final recommendation.

Planner context should combine:

```text
saved user profile
trip request
RAG notes
candidate search results
freshness checks when needed
live tools such as weather later
```

## V1 Scope

The first implementation should stay backend-only inside `apps/api`.

V1 should include:

- Research schemas and service modules under `apps/api/src/northstar/research/`.
- Alembic migration for research runs, source snapshots, and candidates.
- Deterministic validator for required note structure and candidate metadata.
- LLM prompts for research output and critic review.
- CLI commands for city research and run inspection.
- RAG publishing that replaces chunks for refreshed note paths instead of duplicating them.
- Tests with fake search/fetch/LLM clients.

V1 should not include:

- Mobile/admin dashboard UI.
- Raw database access for the LLM.
- Auto-scheduled refresh jobs.
- Full browser automation.
- Real booking availability guarantees.

## Open Design Choices For Implementation

Start with an injectable search/fetch abstraction so tests can avoid network access. The real web provider can be added behind the same interface.

Prefer small, reviewable theme documents such as `overview.md`, `cafes.md`, `restaurants.md`, and `accommodation.md` instead of one giant city note.

Keep every published output traceable to a research run so rollback and admin review can be added later without redesigning the storage model.
