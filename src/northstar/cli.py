import json

import typer
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
from northstar.memory.plan_store import get_itinerary_plan, list_itinerary_plans
from northstar.evals.runner import run_eval_suite
from northstar.memory.eval_store import get_eval_run, list_eval_runs, save_eval_run
from northstar.rag.retriever import retrieve_travel_context
from northstar.rag.store import ingest_markdown_document, search_rag_chunks
from northstar.rag.metadata import build_rag_metadata

app = typer.Typer(no_args_is_help=True)

def exit_with_database_error(exc: SQLAlchemyError) -> None:
  typer.secho(
    "Database is unavailable. Check the Postgres SSH tunnel and run `uv run alembic upgrade head`.",
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