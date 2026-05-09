import json
from dataclasses import dataclass
from typing import Any, Callable

from northstar.tools.weather import get_weather

ToolHandler = Callable[..., dict[str, Any]]

@dataclass(frozen=True)
class ToolDefinition:
  name: str
  schema: dict[str, Any]
  handler: ToolHandler

WEATHER_TOOL = ToolDefinition(
  name="get_weather",
  schema={
    "type": "function",
    "function": {
      "name": "get_weather",
      "description": "Get a weather summary for a city and optional travel date.",
      "parameters": {
        "type": "object",
        "required": ["city"],
        "properties": {
          "city": {
            "type": "string",
            "description": "The city the traveler is visiting",
          },
          "date": {
            "type": "string",
            "description": "Optional travel date in YYYY-MM-DD format."
          },
        },
      },
    },
  },
  handler=get_weather
)

TOOLS_BY_NAME = {
  WEATHER_TOOL.name: WEATHER_TOOL,
}

TOOL_SCHEMAS = [WEATHER_TOOL.schema]

def run_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
  tool = TOOLS_BY_NAME.get(name)
  if tool is None:
    raise ValueError(f"Unknown tool: {name}")
  
  return tool.handler(**arguments)

def format_tool_result(result: dict[str, Any]) -> str:
  return json.dumps(result, sort_keys=True)