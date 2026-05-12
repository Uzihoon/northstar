import pytest

from northstar.research.critic import OllamaResearchCritic, ResearchCriticError
from northstar.research.schemas import (
  ResearchCritique,
  ResearchDraft,
  ResearchTarget,
  ResearchTheme,
)


class FakeStructuredClient:
  def __init__(self, payload: dict[str, object]) -> None:
    self.payload = payload
    self.calls: list[dict[str, object]] = []

  def structured_chat(
      self,
      *,
      messages: list[dict[str, object]],
      model: str,
      response_format: dict[str, object],
      timeout: object | None = None,
  ) -> dict[str, object]:
    self.calls.append({
      "messages": messages,
      "model": model,
      "response_format": response_format,
      "timeout": timeout,
    })
    return self.payload


def test_ollama_research_critic_returns_validated_critique() -> None:
  target = ResearchTarget(
    country="Japan",
    city="Kyoto",
    themes=[ResearchTheme.cafes],
  )
  reviewed_draft = ResearchDraft(
    target=target,
    stable_notes=[],
    candidates=[],
    blocked_items=[],
  )
  client = FakeStructuredClient(
    payload={
      "summary": "Draft is source-aligned.",
      "issues": [
        {
          "path": "candidates.0",
          "severity": "warning",
          "action": "downgrade",
          "reason": "Only one source supports this candidate.",
          "source_urls": ["https://example.com/cafe"],
        }
      ],
      "reviewed_draft": reviewed_draft.model_dump(mode="json"),
    }
  )
  critic = OllamaResearchCritic(client=client, model="gemma4:e4b")

  critique = critic.review(
    target=target,
    draft=reviewed_draft,
    source_texts=["Source URL: https://example.com/cafe\n\nCafe source text."],
  )

  assert isinstance(critique, ResearchCritique)
  assert critique.summary == "Draft is source-aligned."
  assert critique.issues[0].action == "downgrade"
  assert critique.reviewed_draft.target.city == "Kyoto"
  assert client.calls[0]["model"] == "gemma4:e4b"
  assert client.calls[0]["response_format"] == ResearchCritique.model_json_schema()
  user_message = str(client.calls[0]["messages"][1]["content"])
  assert "Cafe source text." in user_message
  assert '"city": "Kyoto"' in user_message


def test_ollama_research_critic_wraps_invalid_structured_output() -> None:
  target = ResearchTarget(
    country="Japan",
    city="Kyoto",
    themes=[ResearchTheme.cafes],
  )
  client = FakeStructuredClient(payload={"summary": "missing reviewed draft"})
  critic = OllamaResearchCritic(client=client, model="gemma4:e4b")

  with pytest.raises(
      ResearchCriticError,
      match="Research critic returned invalid structured output.",
  ):
    critic.review(
      target=target,
      draft=ResearchDraft(target=target),
      source_texts=["source"],
    )


def test_ollama_research_critic_uses_research_read_timeout() -> None:
  target = ResearchTarget(
    country="Japan",
    city="Kyoto",
    themes=[ResearchTheme.cafes],
  )
  draft = ResearchDraft(target=target)
  client = FakeStructuredClient(
    payload={
      "summary": "Looks source-aligned.",
      "issues": [],
      "reviewed_draft": draft.model_dump(mode="json"),
    }
  )
  critic = OllamaResearchCritic(
    client=client,
    model="gemma4:e4b",
    read_timeout_seconds=3600.0,
  )

  critic.review(target=target, draft=draft, source_texts=["source"])

  assert client.calls[0]["timeout"].read == 3600.0
