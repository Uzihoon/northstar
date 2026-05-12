from northstar.research.job import run_research_job
from northstar.research.schemas import ResearchTarget, ResearchTheme


class FakeSession:
  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc, tb):
    return False


class FakeSettings:
  embedding_model = "embed-model"
  embedding_dimensions = 1024
  search_provider = "none"


def test_run_research_job_executes_existing_run(monkeypatch) -> None:
  captured = {}

  def fake_run_existing_research_pipeline(**kwargs):
    captured.update(kwargs)

  monkeypatch.setattr("northstar.research.job.get_settings", lambda: FakeSettings())
  monkeypatch.setattr("northstar.research.job.get_ollama_client", lambda: "ollama-client")
  monkeypatch.setattr("northstar.research.job.get_session", lambda: FakeSession())
  monkeypatch.setattr("northstar.research.job.run_existing_research_pipeline", fake_run_existing_research_pipeline)

  target = ResearchTarget(
    country="Japan",
    city="Kyoto",
    themes=[ResearchTheme.cafes],
    trusted_urls=["https://kyoto.travel/en/"],
  )

  run_research_job(
    run_id="run-1",
    target=target,
    model="test-model",
    web_search=False,
    publish_notes=False,
  )

  assert captured["run_id"] == "run-1"
  assert captured["target"] == target
  assert captured["model_name"] == "test-model"
  assert captured["fetcher"].__class__.__name__ == "TrustedUrlFetcher"
  assert captured["research_agent"].__class__.__name__ == "OllamaResearchAgent"
  assert captured["critic"].__class__.__name__ == "OllamaResearchCritic"
  assert captured["publish_notes"] is False


def test_run_research_job_marks_run_failed_on_error(monkeypatch) -> None:
  failed = {}

  def fake_run_existing_research_pipeline(**kwargs):
    raise RuntimeError("model exploded")

  def fake_update_research_run_status(session, *, run_id, status, report=None):
    failed.update({
      "run_id": run_id,
      "status": status,
      "report": report,
    })

  monkeypatch.setattr("northstar.research.job.get_settings", lambda: FakeSettings())
  monkeypatch.setattr("northstar.research.job.get_ollama_client", lambda: "ollama-client")
  monkeypatch.setattr("northstar.research.job.get_session", lambda: FakeSession())
  monkeypatch.setattr("northstar.research.job.run_existing_research_pipeline", fake_run_existing_research_pipeline)
  monkeypatch.setattr("northstar.research.job.update_research_run_status", fake_update_research_run_status)

  run_research_job(
    run_id="run-1",
    target=ResearchTarget(
      country="Japan",
      city="Kyoto",
      themes=[ResearchTheme.cafes],
    ),
    model="test-model",
  )

  assert failed == {
    "run_id": "run-1",
    "status": "failed",
    "report": {
      "error": "model exploded",
    },
  }
