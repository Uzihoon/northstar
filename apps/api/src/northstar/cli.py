import json

import typer
from httpx import HTTPError
from pathlib import Path
from sqlalchemy.exc import SQLAlchemyError

from northstar.config import get_settings
from northstar.ollama_client import OllamaError, get_ollama_client
from northstar.agent.loop import run_travel_agent
from northstar.agent.extract import TripExtractionError, extract_trip_request
from northstar.db import get_session
from northstar.agent.profile_extract import PreferenceExtractionError, extract_preference_update
from northstar.memory.profile_store import apply_preference_update, load_profile
from northstar.agent.context import build_active_plan_context
from northstar.agent.itinerary import ItineraryGenerationError, generate_itinerary_plan
from northstar.agent.planner_service import generate_and_optionally_save_itinerary
from northstar.memory.plan_store import (
  get_itinerary_quality_report,
  get_itinerary_plan,
  get_rag_coverage_report,
  list_itinerary_plans,
)
from northstar.evals.runner import run_eval_suite
from northstar.memory.eval_store import get_eval_run, list_eval_runs, save_eval_run
from northstar.rag.retriever import retrieve_travel_context
from northstar.rag.store import ingest_markdown_document, search_rag_chunks
from northstar.rag.metadata import build_rag_metadata
from northstar.research.agent import OllamaResearchAgent
from northstar.research.fetcher import TrustedUrlFetcher
from northstar.research.publisher import publish_stable_notes
from northstar.research.schemas import ResearchTarget, ResearchTheme, TrustRating
from northstar.research.store import (
  get_research_run,
  list_research_runs,
  search_candidate_options,
)
from northstar.research.service import run_research_pipeline

app = typer.Typer(no_args_is_help=True)

def exit_with_database_error(exc: SQLAlchemyError) -> None:
  typer.secho(
    "Database is unavailable. Check the Postgres SSH tunnel and run `uv run alembic upgrade head`.",
    fg=typer.colors.RED,
    err=True,
  )
  raise typer.Exit(code=1) from exc

def parse_research_themes(values: list[str]) -> list[ResearchTheme]:
  if not values:
    return list(ResearchTheme)

  themes: list[ResearchTheme] = []

  for value in values:
    try:
      themes.append(ResearchTheme(value))
    except ValueError as exc:
      allowed = ", ".join(theme.value for theme in ResearchTheme)
      typer.secho(
        f"Invalid research theme: {value}. Allowed themes: {allowed}",
        fg=typer.colors.RED,
        err=True,
      )
      raise typer.Exit(code=1) from exc

  return themes

def parse_trust_rating(value: str) -> TrustRating:
  try:
    return TrustRating(value)
  except ValueError as exc:
    allowed = ", ".join(rating.value for rating in TrustRating if rating != TrustRating.blocked)
    typer.secho(
      f"Invalid trust rating: {value}. Allowed ratings: {allowed}",
      fg=typer.colors.RED,
      err=True,
    )
    raise typer.Exit(code=1) from exc

@app.callback()
def cli() -> None:
  """Northstar CLI"""
  return None

@app.command()
def doctor() -> None:
  """Print the current application configuration"""
  settings = get_settings()
  typer.echo(json.dumps(settings.model_dump(), indent=2))

@app.command()
def models() -> None:
  """List models available in Ollama"""
  client = get_ollama_client()

  try:
    for model_name in client.list_models():
      typer.echo(model_name)
  except OllamaError as exc:
    typer.secho(str(exc), fg=typer.colors.RED, err=True)
    raise typer.Exit(code=1) from exc
  
@app.command()
def ask(
  prompt: str,
  model: str | None = typer.Option(None, "--model", "-m"),
) -> None:
  """Send a single prompt to Ollama and print the reply."""
  settings = get_settings()
  resolved_model = model or settings.default_model
  client = get_ollama_client()

  try:
    message = client.chat(prompt=prompt, model=resolved_model)
  except OllamaError as exc:
    typer.secho(str(exc), fg=typer.colors.RED, err=True)
    raise typer.Exit(code=1) from exc
  
  typer.echo(message)

@app.command("ask-stream")
def ask_stream(
  prompt: str,
  model: str | None = typer.Option(None, "--model", "-m"),
  think: bool = typer.Option(False, "--think/--no-think"),
) -> None:
  """Stream a single prompt from Ollama."""
  settings = get_settings()
  resolved_model = model or settings.default_model
  client = get_ollama_client()

  current_block: str | None = None

  try:
    for event in client.chat_stream(
      prompt=prompt,
      model=resolved_model,
      think=think
    ):
      if event.kind == "thinking":
        if current_block != "thinking":
          if current_block is not None:
            typer.echo("")
          typer.echo("[thinking]")
          current_block = "thinking"
        typer.echo(str(event.value), nl=False)
      elif event.kind == "content":
        if current_block != "content":
          if current_block is not None:
            typer.echo("")
          typer.echo("[assistant]")
          current_block = "content"
        typer.echo(str(event.value), nl=False)
      elif event.kind == "tool_call":
        if current_block is not None:
          typer.echo("")
          current_block = None
        
        tool_call = event.value or {}
        function = tool_call.get("function", {})
        name = function.get("name", "unknown_tool")
        arguments = function.get("arguments", {})
        typer.echo(
          f"[tool_call] {name} {json.dumps(arguments)}"
        )
      elif event.kind == "done":
        if current_block is not None:
          typer.echo("")
          current_block = None
  except OllamaError as exc:
    typer.secho(str(exc), fg=typer.colors.RED, err=True)
    raise typer.Exit(code=1) from exc
  
@app.command("plan")
def plan(
  prompt: str,
  user: str = typer.Option("local", "--user"),
  model: str | None = typer.Option(None, "--model", "-m"),
) -> None:
  """Run the personalized travel planner loop."""
  settings = get_settings()
  resolved_model = model or settings.default_model
  client = get_ollama_client()

  try:
    trip_request = extract_trip_request(
      prompt=prompt,
      model=resolved_model,
      client=client,
    )
    with get_session() as session:
      profile = load_profile(session, user_slug=user)
    context = build_active_plan_context(
      profile=profile,
      trip_request=trip_request,
    )
    result = run_travel_agent(
      context=context,
      model=resolved_model,
      client=client,
    )
  except (OllamaError, TripExtractionError) as exc:
    typer.secho(str(exc), fg=typer.colors.RED, err=True)
    raise typer.Exit(code=1) from exc
  except SQLAlchemyError as exc:
    exit_with_database_error(exc)

  typer.echo("[active_context]")
  typer.echo(json.dumps(context.model_dump(mode="json"), indent=2))
  typer.echo("")

  for tool_call in result.tool_results:
    typer.echo(f"[tool] {tool_call.name} {json.dumps(tool_call.arguments)}")
    typer.echo(f"[tool_result] {json.dumps(tool_call.result)}")

  typer.echo("")
  typer.echo(result.answer)

@app.command("plan-json")
def plan_json(
    prompt: str,
    user: str = typer.Option("local", "--user"),
    model: str | None = typer.Option(None, "--model", "-m"),
) -> None:
  """Generate and save a structured itinerary plan."""
  settings = get_settings()
  resolved_model = model or settings.default_model
  client = get_ollama_client()

  try:
    with get_session() as session:
      def rag_retriever(session, active_context):
        return retrieve_travel_context(
          session=session,
          context=active_context,
          client=client,
          embedding_model=settings.embedding_model,
          embedding_dimensions=settings.embedding_dimensions,
          limit=3,
        )

      result = generate_and_optionally_save_itinerary(
        prompt=prompt,
        user_slug=user,
        model=resolved_model,
        client=client,
        session=session,
        save=True,
        rag_retriever=rag_retriever,
      )
  except (OllamaError, TripExtractionError, ItineraryGenerationError) as exc:
    typer.secho(str(exc), fg=typer.colors.RED, err=True)
    raise typer.Exit(code=1) from exc
  except SQLAlchemyError as exc:
    exit_with_database_error(exc)

  typer.echo(json.dumps({
    "plan_id": result.saved.plan_id if result.saved else None,
    "trip_request_id": result.saved.trip_request_id if result.saved else None,
    "trip_request": result.trip_request.model_dump(mode="json"),
    "active_context": result.active_context.model_dump(mode="json"),
    "itinerary": result.itinerary.model_dump(mode="json"),
    "itinerary_diagnostics": {
      "repair_attempted": result.itinerary_diagnostics.repair_attempted,
      "repair_succeeded": result.itinerary_diagnostics.repair_succeeded,
      "initial_validation_error": result.itinerary_diagnostics.initial_validation_error,
    },
    "rag_context": result.rag_context.model_dump(mode="json") if result.rag_context else None,
  }, indent=2))



@app.command("extract-trip")
def extract_trip(
  prompt: str,
  model: str | None = typer.Option(None, "--model", "-m"),
) -> None:
  """Extract a structured trip request from free-form text."""
  settings = get_settings()
  resolved_model = model or settings.default_model
  client = get_ollama_client()

  try:
    trip_request = extract_trip_request(
      prompt=prompt,
      model=resolved_model,
      client=client,
    )
  except (OllamaError, TripExtractionError) as exc:
    typer.secho(str(exc), fg=typer.colors.RED, err=True)
    raise typer.Exit(code=1) from exc
  
  typer.echo(
    json.dumps(
      trip_request.model_dump(),
      indent=2,
    )
  )

@app.command("show-profile")
def show_profile(user: str = typer.Option("local", "--user")) -> None:
  try:
    with get_session() as session:
      profile = load_profile(session, user_slug=user)
  except SQLAlchemyError as exc:
    exit_with_database_error(exc)

  typer.echo(json.dumps(profile.model_dump(mode="json"), indent=2))

@app.command("learn-profile")
def learn_profile(
    text: str,
    user: str = typer.Option("local", "--user"),
    source_kind: str = typer.Option("onboarding", "--source-kind"),
    model: str | None = typer.Option(None, "--model", "-m"),
) -> None:
    settings = get_settings()
    resolved_model = model or settings.default_model
    client = get_ollama_client()

    try:
        candidate = extract_preference_update(text=text, model=resolved_model, client=client)
        with get_session() as session:
            profile, patch = apply_preference_update(
                session,
                user_slug=user,
                source_kind=source_kind,
                source_text=text,
                candidate=candidate,
            )
    except (OllamaError, PreferenceExtractionError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc
    except SQLAlchemyError as exc:
        exit_with_database_error(exc)

    typer.echo("[candidate]")
    typer.echo(json.dumps(candidate.model_dump(mode="json"), indent=2))
    typer.echo("[applied]")
    typer.echo(json.dumps(patch, indent=2))
    typer.echo("[profile]")
    typer.echo(json.dumps(profile.model_dump(mode="json"), indent=2))

@app.command("build-context")
def build_context(
    prompt: str,
    user: str = typer.Option("local", "--user"),
    model: str | None = typer.Option(None, "--model", "-m"),
) -> None:
  """Extract a trip request and merge it with saved profile preferences."""
  settings = get_settings()
  resolved_model = model or settings.default_model
  client = get_ollama_client()

  try:
    trip_request = extract_trip_request(
      prompt=prompt,
      model=resolved_model,
      client=client,
    )
    with get_session() as session:
      profile = load_profile(session, user_slug=user)
  except (OllamaError, TripExtractionError) as exc:
    typer.secho(str(exc), fg=typer.colors.RED, err=True)
    raise typer.Exit(code=1) from exc
  except SQLAlchemyError as exc:
    exit_with_database_error(exc)

  context = build_active_plan_context(
    profile=profile,
    trip_request=trip_request,
  )

  typer.echo(json.dumps(context.model_dump(mode="json"), indent=2))

@app.command("research-city")
def research_city(
    city: str,
    country: str = typer.Option(..., "--country"),
    theme: list[str] = typer.Option([], "--theme"),
    trusted_url: list[str] = typer.Option([], "--trusted-url"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    model: str | None = typer.Option(None, "--model", "-m"),
    publish_notes: bool = typer.Option(False, "--publish-notes/--no-publish-notes"),
) -> None:
  """Research a city and store stable notes plus candidate options."""
  target = ResearchTarget(
    country=country,
    city=city,
    themes=parse_research_themes(theme),
    trusted_urls=trusted_url,
  )

  if dry_run:
    typer.echo(json.dumps(target.model_dump(mode="json"), indent=2))
    return

  settings = get_settings()
  resolved_model = model or settings.default_model
  client = get_ollama_client()

  try:
    with get_session() as session:
      result = run_research_pipeline(
        session=session,
        target=target,
        model_name=resolved_model,
        fetcher=TrustedUrlFetcher(),
        research_agent=OllamaResearchAgent(
          client=client,
          model=resolved_model,
        ),
        publish_notes=publish_notes,
        note_publisher=lambda session, target, notes: publish_stable_notes(
          session=session,
          target=target,
          notes=notes,
          base_dir=Path("rag_docs"),
          client=client,
          embedding_model=settings.embedding_model,
          embedding_dimensions=settings.embedding_dimensions,
        ),
      )
  except (OllamaError, RuntimeError, ValueError, HTTPError) as exc:
    typer.secho(str(exc), fg=typer.colors.RED, err=True)
    raise typer.Exit(code=1) from exc
  except SQLAlchemyError as exc:
    exit_with_database_error(exc)

  typer.echo(json.dumps({
    "run_id": result.run.run_id,
    "status": result.run.status,
    "target": result.run.target,
    "model_name": result.run.model_name,
    "report": result.run.report,
    "validation": result.validation.model_dump(mode="json"),
  }, indent=2))

@app.command("list-research-runs")
def list_research_runs_command() -> None:
  """List saved research pipeline runs."""
  try:
    with get_session() as session:
      runs = list_research_runs(session)
  except SQLAlchemyError as exc:
    exit_with_database_error(exc)

  typer.echo(json.dumps([
    {
      "run_id": run.run_id,
      "target": run.target,
      "model_name": run.model_name,
      "status": run.status,
      "report": run.report,
      "created_at": run.created_at,
      "updated_at": run.updated_at,
    }
    for run in runs
  ], indent=2))

@app.command("show-research-run")
def show_research_run(run_id: str) -> None:
  """Show a saved research pipeline run."""
  try:
    with get_session() as session:
      run = get_research_run(session, run_id=run_id)
  except SQLAlchemyError as exc:
    exit_with_database_error(exc)

  if run is None:
    typer.secho("Research run not found.", fg=typer.colors.RED, err=True)
    raise typer.Exit(code=1)

  typer.echo(json.dumps({
    "run_id": run.run_id,
    "target": run.target,
    "model_name": run.model_name,
    "status": run.status,
    "report": run.report,
    "created_at": run.created_at,
    "updated_at": run.updated_at,
  }, indent=2))

@app.command("search-candidates")
def search_candidates_command(
    country: str = typer.Option(..., "--country"),
    city: str = typer.Option(..., "--city"),
    category: str | None = typer.Option(None, "--category"),
    min_trust: str = typer.Option("medium", "--min-trust"),
    limit: int = typer.Option(10, "--limit"),
) -> None:
  """Search stored researched travel candidate options."""
  trust = parse_trust_rating(min_trust)

  try:
    with get_session() as session:
      candidates = search_candidate_options(
        session=session,
        country=country,
        city=city,
        category=category,
        min_trust=trust,
        limit=limit,
      )
  except SQLAlchemyError as exc:
    exit_with_database_error(exc)

  typer.echo(json.dumps({
    "candidates": [
      {
        "candidate_id": candidate.candidate_id,
        "run_id": candidate.run_id,
        "name": candidate.name,
        "category": candidate.category,
        "country": candidate.country,
        "city": candidate.city,
        "area": candidate.area,
        "description": candidate.description,
        "price_level": candidate.price_level,
        "trust_rating": candidate.trust_rating,
        "source_urls": candidate.source_urls,
        "last_checked_at": candidate.last_checked_at,
        "metadata": candidate.metadata,
      }
      for candidate in candidates
    ]
  }, indent=2))

@app.command("list-plans")
def list_plans(user: str = typer.Option("local", "--user")) -> None:
  """List saved itinerary plans."""
  try:
    with get_session() as session:
      plans = list_itinerary_plans(session, user_slug=user)
  except SQLAlchemyError as exc:
    exit_with_database_error(exc)

  typer.echo(json.dumps([
    {
      "plan_id": plan.plan_id,
      "trip_request_id": plan.trip_request_id,
      "original_prompt": plan.original_prompt,
      "title": plan.title,
      "destination": plan.destination,
      "created_at": plan.created_at,
    }
    for plan in plans
  ], indent=2))


@app.command("show-plan")
def show_plan(
    plan_id: str,
    user: str = typer.Option("local", "--user"),
) -> None:
  """Show a saved itinerary plan."""
  try:
    with get_session() as session:
      plan = get_itinerary_plan(session, user_slug=user, plan_id=plan_id)
  except SQLAlchemyError as exc:
    exit_with_database_error(exc)

  if plan is None:
    typer.secho("Itinerary plan not found.", fg=typer.colors.RED, err=True)
    raise typer.Exit(code=1)

  typer.echo(json.dumps({
    "plan_id": plan.plan_id,
    "trip_request_id": plan.trip_request_id,
    "original_prompt": plan.original_prompt,
    "trip_request": plan.trip_request,
    "active_context": plan.active_context,
    "itinerary": plan.itinerary,
    "rag_context": plan.rag_context,
    "itinerary_diagnostics": plan.itinerary_diagnostics,
    "model_name": plan.model_name,
    "created_at": plan.created_at,
  }, indent=2))

@app.command("eval")
def eval_suite(
    suite: str,
    model: str | None = typer.Option(None, "--model", "-m"),
    save: bool = typer.Option(True, "--save/--no-save"),
) -> None:
  """Run an offline eval suite."""
  settings = get_settings()
  resolved_model = model or settings.default_model
  client = get_ollama_client()

  try:
    result = run_eval_suite(
      suite=suite,
      model=resolved_model,
      client=client,
    )
    saved_run_id = None
    if save:
      try:
        with get_session() as session:
          saved = save_eval_run(
            session,
            result=result,
            model_name=resolved_model,
          )
          saved_run_id = saved.run_id
      except SQLAlchemyError as exc:
        exit_with_database_error(exc)
  except (OllamaError, TripExtractionError, PreferenceExtractionError, ItineraryGenerationError, ValueError) as exc:
    typer.secho(str(exc), fg=typer.colors.RED, err=True)
    raise typer.Exit(code=1) from exc

  typer.echo(
    json.dumps(
      {
        "suite": result.suite,
        "run_id": saved_run_id,
        "passed": result.passed,
        "failed": result.failed,
        "total": result.total,
        "pass_rate": result.pass_rate,
        "results": [
          {
            "case_id": case_result.case_id,
            "passed": case_result.passed,
            "checks": [
              {
                "name": check.name,
                "passed": check.passed,
                "expected": check.expected,
                "actual": check.actual,
              }
              for check in case_result.checks
            ],
          }
          for case_result in result.results
        ],
      },
      indent=2,
    )
  )

@app.command("eval-quality")
def eval_quality(user: str = typer.Option("local", "--user")) -> None:
  """Summarize saved itinerary quality warnings."""
  try:
    with get_session() as session:
      report = get_itinerary_quality_report(session, user_slug=user)
  except SQLAlchemyError as exc:
    exit_with_database_error(exc)

  typer.echo(f"plans_scanned: {report.total_plans}")
  typer.echo(f"plans_with_warnings: {report.plans_with_warnings}")
  typer.echo(f"total_issues: {report.total_issues}")

  if not report.issue_counts:
    typer.echo("No quality warnings found.")
    return

  typer.echo("")
  typer.echo("warning_counts:")

  for code, count in sorted(
      report.issue_counts.items(),
      key=lambda item: (-item[1], item[0]),
  ):
    typer.echo(f"{code}: {count}")

@app.command("eval-rag-coverage")
def eval_rag_coverage(user: str = typer.Option("local", "--user")) -> None:
  """Summarize saved itinerary RAG source coverage."""
  try:
    with get_session() as session:
      report = get_rag_coverage_report(session, user_slug=user)
  except SQLAlchemyError as exc:
    exit_with_database_error(exc)

  typer.echo(f"plans_scanned: {report.total_plans}")
  typer.echo(f"plans_with_rag: {report.plans_with_rag}")
  typer.echo(f"plans_without_rag: {report.plans_without_rag}")
  typer.echo(f"sources_used: {report.total_sources}")

  if not report.source_counts:
    typer.echo("No RAG sources found.")
    return

  typer.echo("")
  typer.echo("source_counts:")

  for source_path, count in sorted(
      report.source_counts.items(),
      key=lambda item: (-item[1], item[0]),
  ):
    typer.echo(f"{source_path}: {count}")

@app.command("list-eval-runs")
def list_eval_runs_command() -> None:
  try:
    with get_session() as session:
      runs = list_eval_runs(session)
  except SQLAlchemyError as exc:
    exit_with_database_error(exc)

  typer.echo(json.dumps([
    {
      "run_id": run.run_id,
      "suite": run.suite,
      "model_name": run.model_name,
      "passed": run.passed,
      "failed": run.failed,
      "total": run.total,
      "pass_rate": run.pass_rate,
      "created_at": run.created_at,
    }
    for run in runs
  ], indent=2))


@app.command("show-eval-run")
def show_eval_run(run_id: str) -> None:
  try:
    with get_session() as session:
      run = get_eval_run(session, run_id=run_id)
  except SQLAlchemyError as exc:
    exit_with_database_error(exc)

  if run is None:
    typer.secho("Eval run not found.", fg=typer.colors.RED, err=True)
    raise typer.Exit(code=1)

  typer.echo(json.dumps({
    "run_id": run.run_id,
    "suite": run.suite,
    "model_name": run.model_name,
    "passed": run.passed,
    "failed": run.failed,
    "total": run.total,
    "pass_rate": run.pass_rate,
    "created_at": run.created_at,
    "case_results": run.case_results,
  }, indent=2))

@app.command("rag-ingest")
def rag_ingest(
    path: Path,
    city: str | None = typer.Option(None, "--city"),
    country: str | None = typer.Option(None, "--country"),
    doc_type: str | None = typer.Option(None, "--doc-type"),
) -> None:
  """Ingest a curated Markdown document into RAG storage."""
  settings = get_settings()
  client = get_ollama_client()

  try:
    with get_session() as session:
      count = ingest_markdown_document(
        session=session,
        path=path,
        metadata=build_rag_metadata(
          path=path,
          city=city,
          country=country,
          doc_type=doc_type,
        ),
        client=client,
        embedding_model=settings.embedding_model,
        embedding_dimensions=settings.embedding_dimensions,
      )

  except (OllamaError, RuntimeError) as exc:
    typer.secho(str(exc), fg=typer.colors.RED, err=True)
    raise typer.Exit(code=1) from exc
  except SQLAlchemyError as exc:
    exit_with_database_error(exc)

  typer.echo(f"Ingested {count} chunks.")


@app.command("rag-search")
def rag_search(
    query: str,
    limit: int = typer.Option(5, "--limit"),
) -> None:
  """Search curated RAG chunks."""
  settings = get_settings()
  client = get_ollama_client()

  try:
    with get_session() as session:
      results = search_rag_chunks(
        session=session,
        query=query,
        client=client,
        embedding_model=settings.embedding_model,
        embedding_dimensions=settings.embedding_dimensions,
        limit=limit,
      )
  except (OllamaError, RuntimeError) as exc:
    typer.secho(str(exc), fg=typer.colors.RED, err=True)
    raise typer.Exit(code=1) from exc
  except SQLAlchemyError as exc:
    exit_with_database_error(exc)

  typer.echo(json.dumps([
    {
      "chunk_id": result.chunk_id,
      "source_path": result.source_path,
      "metadata": result.metadata,
      "score": result.score,
      "text": result.text,
    }
    for result in results
  ], indent=2))

def main() -> None:
  app()

if __name__ == "__main__":
  main()
