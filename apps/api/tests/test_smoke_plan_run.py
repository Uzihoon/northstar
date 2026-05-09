import pytest

from northstar.devtools.smoke_plan_run import SmokeRunError, run_smoke_plan_run


class FakeResponse:
  def __init__(self, payload):
    self.payload = payload

  def raise_for_status(self) -> None:
    return None

  def json(self):
    return self.payload


class FakeClient:
  def __init__(self, run_payloads):
    self.run_payloads = list(run_payloads)
    self.calls = []

  def post(self, url, *, json):
    self.calls.append(("POST", url, json))
    return FakeResponse(
      {
        "run_id": "run-123",
        "status": "queued",
        "poll_url": "/itinerary-plan-runs/run-123?user=local",
        "progress_events": [
          {
            "status": "queued",
            "message": "Itinerary planning run queued.",
          }
        ],
        "created_at": "2026-05-07T10:00:00",
        "updated_at": "2026-05-07T10:00:00",
      }
    )

  def get(self, url, *, params=None):
    self.calls.append(("GET", url, params))

    if url.endswith("/itinerary-plan-runs/run-123"):
      return FakeResponse(self.run_payloads.pop(0))

    if url.endswith("/itinerary-plans/plan-123"):
      return FakeResponse(
        {
          "plan_id": "plan-123",
          "itinerary": {
            "title": "A relaxed Kyoto plan",
            "destination": "Kyoto, Japan",
          },
        }
      )

    raise AssertionError(f"Unexpected URL: {url}")


def test_smoke_plan_run_polls_until_completed_and_fetches_plan() -> None:
  output: list[str] = []
  client = FakeClient(
    run_payloads=[
      {
        "run_id": "run-123",
        "status": "running",
        "progress_events": [
          {
            "status": "queued",
            "message": "Itinerary planning run queued.",
          },
          {
            "status": "running",
            "message": "Itinerary planning run started.",
          },
        ],
        "plan_id": None,
        "trip_request_id": None,
        "error_message": None,
      },
      {
        "run_id": "run-123",
        "status": "completed",
        "progress_events": [
          {
            "status": "queued",
            "message": "Itinerary planning run queued.",
          },
          {
            "status": "running",
            "message": "Itinerary planning run started.",
          },
          {
            "status": "completed",
            "message": "Itinerary plan completed.",
          },
        ],
        "plan_id": "plan-123",
        "trip_request_id": "trip-123",
        "error_message": None,
      },
    ],
  )

  result = run_smoke_plan_run(
    prompt="Plan 2 quiet days in Kyoto.",
    base_url="http://127.0.0.1:8000/",
    user="local",
    model="qwen3.6:27b",
    client=client,
    sleep=lambda _: None,
    output=output.append,
  )

  assert result["run"]["status"] == "completed"
  assert result["plan"]["itinerary"]["title"] == "A relaxed Kyoto plan"
  assert ("POST", "http://127.0.0.1:8000/itinerary-plan-runs", {
    "user": "local",
    "prompt": "Plan 2 quiet days in Kyoto.",
    "model": "qwen3.6:27b",
    "save": True,
  }) in client.calls
  assert ("GET", "http://127.0.0.1:8000/itinerary-plans/plan-123", {"user": "local"}) in client.calls
  assert "completed: Itinerary plan completed." in output
  assert "Plan: A relaxed Kyoto plan (Kyoto, Japan)" in output


def test_smoke_plan_run_raises_when_run_fails() -> None:
  client = FakeClient(
    run_payloads=[
      {
        "run_id": "run-123",
        "status": "failed",
        "progress_events": [
          {
            "status": "failed",
            "message": "Ollama took too long to respond.",
          }
        ],
        "plan_id": None,
        "trip_request_id": None,
        "error_message": "Ollama took too long to respond.",
      },
    ],
  )

  with pytest.raises(SmokeRunError, match="Ollama took too long"):
    run_smoke_plan_run(
      prompt="Plan 2 quiet days in Kyoto.",
      client=client,
      sleep=lambda _: None,
      output=lambda _: None,
    )
