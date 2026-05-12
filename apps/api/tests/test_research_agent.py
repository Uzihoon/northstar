import pytest

from northstar.research.agent import OllamaResearchAgent, ResearchAgentError
from northstar.research.schemas import ResearchDraft, ResearchTarget, ResearchTheme


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


def test_ollama_research_agent_returns_validated_research_draft() -> None:
  target = ResearchTarget(
    country="Japan",
    city="Kyoto",
    themes=[ResearchTheme.cafes],
    trusted_urls=["https://kyoto.travel/en/"],
  )
  client = FakeStructuredClient(
    payload={
      "target": target.model_dump(mode="json"),
      "stable_notes": [
        {
          "theme": "cafes",
          "title": "Kyoto cafe strategy",
          "markdown": "## Cafe Areas\n\nKawaramachi is useful for flexible cafe backups.",
          "trust_rating": "medium",
          "sources": [
            {
              "title": "Kyoto Travel",
              "url": "https://kyoto.travel/en/",
            }
          ],
        }
      ],
      "candidates": [
        {
          "name": "Quiet Coffee",
          "category": "cafe",
          "country": "Japan",
          "city": "Kyoto",
          "area": "Kawaramachi",
          "description": "Central cafe option.",
          "price_level": "moderate",
          "trust_rating": "medium",
          "source_urls": ["https://example.com/quiet-coffee"],
        }
      ],
      "blocked_items": [],
    }
  )
  agent = OllamaResearchAgent(client=client, model="gemma4:e4b")

  draft = agent.research(
    target=target,
    source_texts=["Kyoto cafe source text."],
  )

  assert isinstance(draft, ResearchDraft)
  assert draft.target.city == "Kyoto"
  assert draft.stable_notes[0].theme == ResearchTheme.cafes
  assert draft.candidates[0].name == "Quiet Coffee"
  assert client.calls[0]["model"] == "gemma4:e4b"
  assert client.calls[0]["response_format"] == ResearchDraft.model_json_schema()
  user_message = client.calls[0]["messages"][1]["content"]
  assert "Kyoto" in str(user_message)
  assert "Kyoto cafe source text." in str(user_message)


def test_ollama_research_agent_wraps_invalid_structured_output() -> None:
  client = FakeStructuredClient(payload={"target": {"city": "Kyoto"}})
  agent = OllamaResearchAgent(client=client, model="gemma4:e4b")

  with pytest.raises(
      ResearchAgentError,
      match="Research agent returned invalid structured output.",
  ):
    agent.research(
      target=ResearchTarget(
        country="Japan",
        city="Kyoto",
        themes=[ResearchTheme.cafes],
      ),
      source_texts=["source"],
    )


def test_ollama_research_agent_uses_research_read_timeout() -> None:
  target = ResearchTarget(
    country="Japan",
    city="Kyoto",
    themes=[ResearchTheme.cafes],
  )
  client = FakeStructuredClient(
    payload={
      "target": target.model_dump(mode="json"),
      "stable_notes": [],
      "candidates": [],
      "blocked_items": [],
    }
  )
  agent = OllamaResearchAgent(
    client=client,
    model="gemma4:e4b",
    read_timeout_seconds=3600.0,
  )

  agent.research(target=target, source_texts=["source"])

  assert client.calls[0]["timeout"].read == 3600.0
