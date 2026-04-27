from dataclasses import dataclass
from typing import Any

from northstar.ollama_client import ChatTurn, OllamaClient
from northstar.tools.registry import TOOL_SCHEMAS, format_tool_result, run_tool

SYSTEM_PROMPT = """
You are Nori, a practical travel planner.
Use tools when they help you answer accurately.
If you call a tool, wait for the tool result before giving the final answer.
Keep answers concise and useful.
""".strip()

@dataclass(frozen=True)
class ExecutedToolCall:
  name: str
  arguments: dict[str, Any]
  result: dict[str, Any]

@dataclass(frozen=True)
class AgentResult:
  answer: str
  tool_results: list[ExecutedToolCall]

def _assistant_message_from_turn(turn: ChatTurn) -> dict[str, Any]:
  message: dict[str, Any] = {"role": "assistant"}

  if turn.thinking:
    message["thinking"] = turn.thinking

  if turn.content:
    message["content"] = turn.content

  if turn.tool_calls:
    message["tool_calls"] = [
      {
        "type": tool_call.type,
        "function": {
          "name": tool_call.function.name,
          "arguments": tool_call.function.arguments
        }
      }
      for tool_call in turn.tool_calls
    ]

  return message

def run_travel_agent(
    *,
    prompt: str,
    model: str,
    client: OllamaClient,
    max_rounds: int = 3,
) -> AgentResult:
  messages: list[dict[str, Any]] = [
    {"role": "system", "content": SYSTEM_PROMPT},
    {"role": "user", "content": prompt},
  ]
  executed_tools: list[ExecutedToolCall] = []

  for _ in range(max_rounds):
    turn = client.chat_turn(
      messages=messages,
      model=model,
      tools=TOOL_SCHEMAS,
      think=True,
    )

    messages.append(_assistant_message_from_turn(turn))

    if turn.tool_calls:
      for tool_call in turn.tool_calls:
        result = run_tool(
          tool_call.function.name,
          tool_call.function.arguments,
        )
        executed_tools.append(
          ExecutedToolCall(
            name=tool_call.function.name,
            arguments=tool_call.function.arguments,
            result=result
          )
        )
        messages.append(
          {
            "role": "tool",
            "tool_name": tool_call.function.name,
            "content": format_tool_result(result),
          }
        )
      continue
    if turn.content:
      return AgentResult(
        answer=turn.content,
        tool_results=executed_tools,
      )
    
    raise RuntimeError("Agent returned neither content nor tool calls.")
  
  raise RuntimeError(f"Agent exceeded max rounds ({max_rounds})")