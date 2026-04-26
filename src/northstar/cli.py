import json

import typer

from northstar.config import get_settings
from northstar.ollama_client import get_ollama_client

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
  for model_name in client.list_models():
    typer.echo(model_name)

def main() -> None:
  app()

if __name__ == "__main__":
  main()