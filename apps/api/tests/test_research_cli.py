import json
from dataclasses import dataclass

from typer.testing import CliRunner

import northstar.cli as cli_module


runner = CliRunner()


class FakeSession:
  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc, tb):
    return False


@dataclass(frozen=True)
class FakeResearchRun:
  run_id: str
  target: dict[str, object]
  model_name: str
  status: str
  report: dict[str, object] | None
  created_at: str
  updated_at: str


def test_research_city_dry_run_prints_target() -> None:
  result = runner.invoke(
    cli_module.app,
    [
      "research-city",
      "Kyoto",
      "--country",
      "Japan",
      "--theme",
      "cafes",
      "--trusted-url",
      "https://kyoto.travel/en/",
      "--dry-run",
    ],
  )

  assert result.exit_code == 0
  payload = json.loads(result.output)
  assert payload == {
    "country": "Japan",
    "city": "Kyoto",
    "themes": ["cafes"],
    "trusted_urls": ["https://kyoto.travel/en/"],
  }


def test_research_city_rejects_invalid_theme() -> None:
  result = runner.invoke(
    cli_module.app,
    [
      "research-city",
      "Kyoto",
      "--country",
      "Japan",
      "--theme",
      "nightlife",
      "--dry-run",
    ],
  )

  assert result.exit_code == 1
  assert "Invalid research theme: nightlife" in result.stderr


def test_list_research_runs_prints_saved_runs(monkeypatch) -> None:
  def fake_list_research_runs(session):
    return [
      FakeResearchRun(
        run_id="run-1",
        target={"country": "Japan", "city": "Kyoto", "themes": ["cafes"]},
        model_name="test-model",
        status="completed",
        report={"candidates": 3},
        created_at="2026-05-09T10:00:00+00:00",
        updated_at="2026-05-09T10:01:00+00:00",
      )
    ]

  monkeypatch.setattr(cli_module, "get_session", lambda: FakeSession())
  monkeypatch.setattr(cli_module, "list_research_runs", fake_list_research_runs)

  result = runner.invoke(cli_module.app, ["list-research-runs"])

  assert result.exit_code == 0
  payload = json.loads(result.output)
  assert payload == [
    {
      "run_id": "run-1",
      "target": {"country": "Japan", "city": "Kyoto", "themes": ["cafes"]},
      "model_name": "test-model",
      "status": "completed",
      "report": {"candidates": 3},
      "created_at": "2026-05-09T10:00:00+00:00",
      "updated_at": "2026-05-09T10:01:00+00:00",
    }
  ]
