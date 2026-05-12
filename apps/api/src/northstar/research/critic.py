from typing import Protocol

import httpx
from pydantic import ValidationError

from northstar.research.schemas import ResearchCritique, ResearchDraft, ResearchTarget


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


class ResearchCriticError(RuntimeError):
  """Raised when the research critic returns malformed structured output."""


class OllamaResearchCritic:
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

  def review(
      self,
      *,
      target: ResearchTarget,
      draft: ResearchDraft,
      source_texts: list[str],
  ) -> ResearchCritique:
    request_kwargs = {
      "model": self.model,
      "messages": [
        {
          "role": "system",
          "content": RESEARCH_CRITIC_SYSTEM_PROMPT,
        },
        {
          "role": "user",
          "content": _format_critic_prompt(
            target=target,
            draft=draft,
            source_texts=source_texts,
          ),
        },
      ],
      "response_format": ResearchCritique.model_json_schema(),
    }
    timeout = _structured_chat_timeout(self.read_timeout_seconds)
    if timeout is not None:
      request_kwargs["timeout"] = timeout

    payload = self.client.structured_chat(**request_kwargs)

    try:
      return ResearchCritique.model_validate(payload)
    except ValidationError as exc:
      raise ResearchCriticError(
        "Research critic returned invalid structured output."
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


RESEARCH_CRITIC_SYSTEM_PROMPT = """
You are Northstar's critical travel research reviewer.
Review the draft strictly against the provided source text.
Block unsupported, contradicted, suspicious, stale, or unsafe recommendations.
Downgrade weakly supported items instead of over-trusting them.
Keep useful approved content, but remove or mark blocked content before storage.
Do not introduce new facts that are not supported by the source text.
Return a ResearchCritique JSON object matching the provided schema.
""".strip()


def _format_critic_prompt(
    *,
    target: ResearchTarget,
    draft: ResearchDraft,
    source_texts: list[str],
) -> str:
  source_sections = [
    f"Source {index + 1}:\n{text}"
    for index, text in enumerate(source_texts)
  ]

  return f"""
Research target:
{target.model_dump_json(indent=2)}

Draft to review:
{draft.model_dump_json(indent=2)}

Source texts:
{chr(10).join(source_sections)}

Return a ResearchCritique JSON object. The reviewed_draft is the only draft Northstar will store or publish.
""".strip()
