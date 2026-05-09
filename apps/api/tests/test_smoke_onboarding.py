from northstar.devtools.smoke_onboarding import run_smoke_onboarding


class FakeResponse:
  def __init__(self, payload):
    self.payload = payload

  def raise_for_status(self) -> None:
    return None

  def json(self):
    return self.payload


class FakeClient:
  def __init__(self):
    self.calls = []
    self.turn = 0

  def post(self, url, *, json):
    self.calls.append(("POST", url, json))
    self.turn += 1

    if self.turn == 1:
      assert json["messages"] == []
      return FakeResponse(
        {
          "assistant_message": "Hi, I'm Nori. Ready?",
          "profile_patch": {},
          "profile": {
            "pace": None,
            "budget_level": None,
            "interests": [],
            "food_preferences": [],
            "dislikes": [],
            "notes": [],
          },
          "is_complete": False,
          "next_focus": "intro",
        }
      )

    assert json["messages"] == [
      {"role": "assistant", "content": "Hi, I'm Nori. Ready?"},
      {"role": "user", "content": "Kyoto, because it felt calm."},
    ]
    return FakeResponse(
      {
        "assistant_message": "That sounds lovely. What kind of food moments do you like?",
        "profile_patch": {
          "set": {"pace": "relaxed"},
          "added": {"interests": ["calm cities"]},
        },
        "profile": {
          "pace": "relaxed",
          "budget_level": None,
          "interests": ["calm cities"],
          "food_preferences": [],
          "dislikes": [],
          "notes": [],
        },
        "is_complete": False,
        "next_focus": "food",
      }
    )


def test_smoke_onboarding_keeps_transcript_in_memory_until_done() -> None:
  output: list[str] = []
  user_inputs = iter(["Kyoto, because it felt calm.", "/done"])
  client = FakeClient()

  result = run_smoke_onboarding(
    base_url="http://127.0.0.1:8000/",
    user="local",
    model="qwen3.6:27b",
    client=client,
    input_fn=lambda _: next(user_inputs),
    output=output.append,
  )

  assert result["messages"] == [
    {"role": "assistant", "content": "Hi, I'm Nori. Ready?"},
    {"role": "user", "content": "Kyoto, because it felt calm."},
    {
      "role": "assistant",
      "content": "That sounds lovely. What kind of food moments do you like?",
    },
  ]
  assert result["profile"]["pace"] == "relaxed"
  assert "Nori: Hi, I'm Nori. Ready?" in output
  assert "Patch: {'set': {'pace': 'relaxed'}, 'added': {'interests': ['calm cities']}}" in output
  assert "Final profile: {'pace': 'relaxed'" in output[-1]
