from typing import Protocol

from northstar.research.schemas import ResearchDraft, ResearchTarget


class ResearchFetcher(Protocol):
  def fetch_texts(self, *, target: ResearchTarget) -> list[str]:
    ...


class ResearchAgent(Protocol):
  def research(self, *, target: ResearchTarget, source_texts: list[str]) -> ResearchDraft:
    ...
