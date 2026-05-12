from pathlib import Path

from httpx import HTTPError
from sqlalchemy.exc import SQLAlchemyError

from northstar.config import get_settings
from northstar.db import get_session
from northstar.ollama_client import OllamaError, get_ollama_client
from northstar.research.agent import OllamaResearchAgent, ResearchAgentError
from northstar.research.critic import OllamaResearchCritic, ResearchCriticError
from northstar.research.fetcher import DiscoveryUrlFetcher, TrustedUrlFetcher
from northstar.research.publisher import publish_stable_notes
from northstar.research.schemas import ResearchTarget
from northstar.research.search_client import (
  SearchConfigurationError,
  build_source_search_client,
)
from northstar.research.service import run_existing_research_pipeline
from northstar.research.store import update_research_run_status


def run_research_job(
    *,
    run_id: str,
    target: ResearchTarget,
    model: str,
    web_search: bool = False,
    publish_notes: bool = False,
) -> None:
  try:
    settings = get_settings()
    client = get_ollama_client()

    with get_session() as session:
      fetcher = TrustedUrlFetcher()

      if web_search:
        search_client = build_source_search_client(settings)
        if search_client is None:
          raise SearchConfigurationError(
            "Set SEARCH_PROVIDER=tavily or brave and the matching API key to use web search."
          )
        fetcher = DiscoveryUrlFetcher(search_client=search_client)

      run_existing_research_pipeline(
        session=session,
        run_id=run_id,
        target=target,
        model_name=model,
        fetcher=fetcher,
        research_agent=OllamaResearchAgent(
          client=client,
          model=model,
          read_timeout_seconds=settings.research_ollama_read_timeout_seconds,
        ),
        critic=OllamaResearchCritic(
          client=client,
          model=model,
          read_timeout_seconds=settings.research_ollama_read_timeout_seconds,
        ),
        publish_notes=publish_notes,
        note_publisher=lambda session, target, notes: publish_stable_notes(
          session=session,
          target=target,
          notes=notes,
          base_dir=Path("rag_docs"),
          client=client,
          embedding_model=settings.embedding_model,
          embedding_dimensions=settings.embedding_dimensions,
        ),
      )
  except (
      OllamaError,
      ResearchAgentError,
      ResearchCriticError,
      SearchConfigurationError,
      HTTPError,
      SQLAlchemyError,
      RuntimeError,
      ValueError,
  ) as exc:
    _fail_run_safely(run_id=run_id, error_message=str(exc))


def _fail_run_safely(*, run_id: str, error_message: str) -> None:
  try:
    with get_session() as session:
      update_research_run_status(
        session,
        run_id=run_id,
        status="failed",
        report={
          "error": error_message,
        },
      )
  except SQLAlchemyError:
    return
