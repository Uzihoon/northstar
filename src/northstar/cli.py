import json

import typer

from northstar.config import get_settings

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

def main() -> None:
  app()

if __name__ == "__main__":
  main()