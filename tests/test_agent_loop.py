import copy

from northstar.agent.loop import run_travel_agent
from northstar.ollama_client import ChatTurn, ToolCall, ToolFunctionCall

class FakeOllamaClient:
  def __init__(self) -> None:
    self.calls: list[dict] = []
    self.responses = [
      ChatTurn(
        thinking="I should check the weather first.",
        tool_calls=[
          ToolCall(
            function=ToolFunctionCall(
              name="get_weather",
              arguments={
                "city": "Kyoto",
                "date": "2026-05-10",
              },
            )
          )
        ],
      ),
      ChatTurn(
        content="Kyoto looks cool with light rain. Pack a light jacket and plan a museum stop on day 1."
      ),
    ]
  
  def chat_turn(self, *, messages, model, tools=None, think=False):
    self.calls.append(
      {
        "messages": copy.deepcopy(messages),
        "model": model,
        "tools": copy.deepcopy(tools),
        "think": think
      }
    )
    return self.responses.pop(0)
  
def test_run_travel_agent_executes_weather_tool_and_returns_answer() -> None:
  client = FakeOllamaClient()

  result = run_travel_agent(
    prompt="Plan 2 days in Kyoto next weekend.",
    model="qwen3.6:37b",
    client=client,
  )

  assert result.answer == (
    "Kyoto looks cool with light rain. Pack a light jacket and plan a museum stop on day 1."
  )
  assert len(result.tool_results) == 1
  assert result.tool_results[0].name == "get_weather"
  assert result.tool_results[0].arguments == {
    "city": "Kyoto",
    "date": "2026-05-10"
  }
  assert result.tool_results[0].result["forecast"] == "Light rain"

  second_call_messages = client.calls[1]["messages"]
  assert second_call_messages[-1]["role"] == "tool"
  assert second_call_messages[-1]["tool_name"] == "get_weather"
  assert '"forecast": "Light rain"' in second_call_messages[-1]["content"]
