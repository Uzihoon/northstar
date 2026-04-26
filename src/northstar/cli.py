import json

import typer

from northstar.config import get_settings
from northstar.ollama_client import OllamaUnavailableError, get_ollama_client

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
  except OllamaUnavailableError as exc:
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
  except OllamaUnavailableError as exc:
    typer.secho(str(exc), fg=typer.colors.RED, err=True)
    raise typer.Exit(code=1) from exc
  
  typer.echo(message)

def main() -> None:
  app()

if __name__ == "__main__":
  main()