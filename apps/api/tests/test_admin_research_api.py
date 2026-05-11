from types import SimpleNamespace

from fastapi.testclient import TestClient

import northstar.api.admin as admin_module
import northstar.api.app as app_module


client = TestClient(app_module.app)


class FakeSession:
  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc, tb):
    return False


def test_admin_research_routes_publish_response_models() -> None:
  schema = app_module.app.openapi()

  list_schema = schema["paths"]["/admin/research/runs"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
  detail_schema = schema["paths"]["/admin/research/runs/{run_id}"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
  sources_schema = schema["paths"]["/admin/research/runs/{run_id}/sources"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]

  assert list_schema["$ref"].endswith("/AdminResearchRunListResponse")
  assert detail_schema["$ref"].endswith("/AdminResearchRunResponse")
  assert sources_schema["$ref"].endswith("/AdminResearchSourceSnapshotListResponse")


def test_admin_list_research_runs_returns_saved_runs(monkeypatch) -> None:
  monkeypatch.setattr(admin_module, "get_session", lambda: FakeSession())
  monkeypatch.setattr(
    admin_module,
    "list_research_runs",
    lambda session, *, limit: [
      SimpleNamespace(
        run_id="run-1",
        target={"country": "Japan", "city": "Kyoto"},
        model_name="test-model",
        status="completed",
        report={"source_snapshots": 1},
        created_at="2026-05-10T10:00:00+00:00",
        updated_at="2026-05-10T10:01:00+00:00",
      )
    ],
  )

  response = client.get("/admin/research/runs?limit=5")

  assert response.status_code == 200
  assert response.json() == {
    "runs": [
      {
        "run_id": "run-1",
        "target": {"country": "Japan", "city": "Kyoto"},
        "model_name": "test-model",
        "status": "completed",
        "report": {"source_snapshots": 1},
        "created_at": "2026-05-10T10:00:00+00:00",
        "updated_at": "2026-05-10T10:01:00+00:00",
      }
    ]
  }


def test_admin_get_research_run_sources_returns_preview(monkeypatch) -> None:
  monkeypatch.setattr(admin_module, "get_session", lambda: FakeSession())
  monkeypatch.setattr(
    admin_module,
    "get_research_run",
    lambda session, *, run_id: SimpleNamespace(
      run_id=run_id,
      target={"country": "Japan", "city": "Kyoto"},
      model_name="test-model",
      status="completed",
      report={},
      created_at="2026-05-10T10:00:00+00:00",
      updated_at="2026-05-10T10:01:00+00:00",
    ),
  )
  monkeypatch.setattr(
    admin_module,
    "list_source_snapshots",
    lambda session, *, run_id: [
      SimpleNamespace(
        snapshot_id="source-1",
        run_id=run_id,
        url="https://example.com/cafes",
        title="Kyoto Cafes",
        content_hash="abc123",
        extracted_text="Kyoto cafe source text is useful for planning.",
        fetched_at="2026-05-10T10:00:00+00:00",
        metadata={
          "query": "Kyoto Japan cafes guide",
          "source_kind": "search_result",
          "trust_hint": "low",
          "snippet": "Cafe guide.",
        },
      )
    ],
  )

  response = client.get("/admin/research/runs/run-1/sources?preview_chars=18")

  assert response.status_code == 200
  assert response.json() == {
    "run_id": "run-1",
    "sources": [
      {
        "snapshot_id": "source-1",
        "run_id": "run-1",
        "url": "https://example.com/cafes",
        "title": "Kyoto Cafes",
        "content_hash": "abc123",
        "fetched_at": "2026-05-10T10:00:00+00:00",
        "query": "Kyoto Japan cafes guide",
        "source_kind": "search_result",
        "trust_hint": "low",
        "snippet": "Cafe guide.",
        "text_length": 46,
        "text_preview": "Kyoto cafe source ",
      }
    ],
  }
