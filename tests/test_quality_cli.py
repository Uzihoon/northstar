from typer.testing import CliRunner

import northstar.cli as cli_module
from northstar.memory.plan_store import ItineraryQualityReport, RagCoverageReport


runner = CliRunner()


class FakeSession:
  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc, tb):
    return False


def test_eval_quality_prints_warning_counts(monkeypatch) -> None:
  def fake_get_itinerary_quality_report(session, *, user_slug):
    assert user_slug == "local"

    return ItineraryQualityReport(
      total_plans=3,
      plans_with_warnings=2,
      total_issues=4,
      issue_counts={
        "possible_misclassified_food_item": 3,
        "missing_area": 1,
      },
    )

  monkeypatch.setattr(cli_module, "get_session", lambda: FakeSession())
  monkeypatch.setattr(
    cli_module,
    "get_itinerary_quality_report",
    fake_get_itinerary_quality_report,
  )

  result = runner.invoke(cli_module.app, ["eval-quality"])

  assert result.exit_code == 0
  assert "plans_scanned: 3" in result.output
  assert "plans_with_warnings: 2" in result.output
  assert "total_issues: 4" in result.output
  assert "possible_misclassified_food_item: 3" in result.output
  assert "missing_area: 1" in result.output


def test_eval_rag_coverage_prints_source_counts(monkeypatch) -> None:
  def fake_get_rag_coverage_report(session, *, user_slug):
    assert user_slug == "local"

    return RagCoverageReport(
      total_plans=4,
      plans_with_rag=3,
      plans_without_rag=1,
      total_sources=5,
      source_counts={
        "rag_docs/japan/kyoto/cafes.md": 3,
        "rag_docs/japan/kyoto/restaurants.md": 2,
      },
    )

  monkeypatch.setattr(cli_module, "get_session", lambda: FakeSession())
  monkeypatch.setattr(
    cli_module,
    "get_rag_coverage_report",
    fake_get_rag_coverage_report,
  )

  result = runner.invoke(cli_module.app, ["eval-rag-coverage"])

  assert result.exit_code == 0
  assert "plans_scanned: 4" in result.output
  assert "plans_with_rag: 3" in result.output
  assert "plans_without_rag: 1" in result.output
  assert "sources_used: 5" in result.output
  assert "rag_docs/japan/kyoto/cafes.md: 3" in result.output
  assert "rag_docs/japan/kyoto/restaurants.md: 2" in result.output
