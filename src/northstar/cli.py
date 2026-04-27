import json

import typer

from northstar.config import get_settings
from northstar.ollama_client import OllamaError, get_ollama_client
from northstar.agent.loop import run_travel_agent

app = typer.Typer(no_args_is_help=True)

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
  
@app.command()
def plan(
  prompt: str,
  model: str | None = typer.Option(None, "--model", "-m"),
) -> None:
  """Run the first tool-using travel planner loop."""
  settings = get_settings()
  resolved_model = model or settings.default_model
  client = get_ollama_client()

  try:
    result = run_travel_agent(
      prompt=prompt,
      model=resolved_model,
      client=client
    )
  except OllamaError as exc:
    typer.secho(str(exc), fg=typer.colors.RED, err=True)
    raise typer.Exit(code=1) from exc
  
  for tool_call in result.tool_results:
    typer.echo(f"[tool] {tool_call.name} {json.dumps(tool_call.arguments)}")
    typer.echo(f"[tool_result] {json.dumps(tool_call.result)}")

  typer.echo("")
  typer.echo(result.answer)

def main() -> None:
  app()

if __name__ == "__main__":
  main()