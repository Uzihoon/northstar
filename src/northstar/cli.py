import json

import typer

from northstar.config import get_settings

app = typer.Typer(no_args_is_help=True)

@app.command()
def doctor() -> None:
  """Print the current application configuration"""