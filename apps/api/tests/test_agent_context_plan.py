import copy

from northstar.agent.context import ActivePlanContext
from northstar.agent.loop import run_travel_agent
from northstar.ollama_client import ChatTurn


class FakeOllamaClient:
  def __init__(self) -> None:
    self.calls: list[dict] = []

  def chat_turn(self, *, messages, model, tools=None, think=False):
    self.calls.append(
      {
        "messages": copy.deepcopy(messages),
        "model": model,
        "tools": copy.deepcopy(tools),
        "think": think,
      }
    )
    return ChatTurn(content="Here is a personalized Kyoto plan.")


def test_run_travel_agent_uses_active_plan_context() -> None:
  client = FakeOllamaClient()
  context = ActivePlanContext(
    destination_city="Kyoto",
    country="Japan",
    duration_days=2,
    pace="relaxed",
    interests=["cafes", "bookstores"],
    food_preferences=["vegetarian"],
    profile_preferences_used=["pace", "interests", "food_preferences"],
    trip_overrides_used=[],
  )

  result = run_travel_agent(
    context=context,
    model="qwen3.6:27b",
    client=client,
  )

  user_message = client.calls[0]["messages"][1]["content"]

  assert result.answer == "Here is a personalized Kyoto plan."
  assert "Active plan context" in user_message
  assert '"destination_city": "Kyoto"' in user_message
  assert '"food_preferences": [' in user_message
  assert "Mention the key preferences used" in user_message
