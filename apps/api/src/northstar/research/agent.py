from typing import Protocol

import httpx
from pydantic import ValidationError

from northstar.research.schemas import ResearchDraft, ResearchTarget


class StructuredChatClient(Protocol):
  def structured_chat(
      self,
      *,
      messages: list[dict[str, object]],
      model: str,
      response_format: dict[str, object],
      timeout: object | None = None,
  ) -> dict[str, object]:
    ...


class ResearchAgentError(RuntimeError):
  """Raised when the research agent returns malformed structured output."""


class OllamaResearchAgent:
  def __init__(
      self,
      *,
      client: StructuredChatClient,
      model: str,
      read_timeout_seconds: float | None = None,
  ) -> None:
    self.client = client
    self.model = model
    self.read_timeout_seconds = read_timeout_seconds

  def research(self, *, target: ResearchTarget, source_texts: list[str]) -> ResearchDraft:
    request_kwargs = {
      "model": self.model,
      "messages": [
        {
          "role": "system",
          "content": RESEARCH_SYSTEM_PROMPT,
        },
        {
          "role": "user",
          "content": _format_research_prompt(
            target=target,
            source_texts=source_texts,
          ),
        },
      ],
      "response_format": ResearchDraft.model_json_schema(),
    }
    timeout = _structured_chat_timeout(self.read_timeout_seconds)
    if timeout is not None:
      request_kwargs["timeout"] = timeout

    payload = self.client.structured_chat(**request_kwargs)

    try:
      return ResearchDraft.model_validate(payload)
    except ValidationError as exc:
      raise ResearchAgentError(
        "Research agent returned invalid structured output."
      ) from exc


def _structured_chat_timeout(read_timeout_seconds: float | None) -> httpx.Timeout | None:
  if read_timeout_seconds is None:
    return None

  return httpx.Timeout(
    connect=5.0,
    read=read_timeout_seconds,
    write=30.0,
    pool=5.0,
  )


RESEARCH_SYSTEM_PROMPT = """
You are Northstar's travel research agent.
Use only the provided source text as evidence.
Produce stable planning notes and specific candidate options for the requested target.
Use trust_rating="blocked" for unsupported, suspicious, stale, or low-quality items.
Use price levels instead of exact prices.
Do not make exact opening-hour, availability, closure, or event-schedule claims.
Keep source URLs attached to notes and candidates whenever possible.
""".strip()


def _format_research_prompt(
    *,
    target: ResearchTarget,
    source_texts: list[str],
) -> str:
  source_sections = [
    f"Source {index + 1}:\n{text}"
    for index, text in enumerate(source_texts)
  ]

  return f"""
Research target:
{target.model_dump_json(indent=2)}

Source texts:
{chr(10).join(source_sections)}

Return a ResearchDraft JSON object matching the provided schema.
""".strip()
