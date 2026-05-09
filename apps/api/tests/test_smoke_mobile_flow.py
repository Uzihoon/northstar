from northstar.devtools.smoke_mobile_flow import run_smoke_mobile_flow


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

    if url.endswith("/itinerary-plans/plan-123/summary"):
      return FakeResponse(
        {
          "plan_id": "plan-123",
          "title": "A relaxed Kyoto plan",
          "destination": "Kyoto, Japan",
          "duration_days": 2,
          "status": "ready_with_warnings",
          "highlights": ["quiet cafes", "bookstores"],
          "quality": {
            "status": "warning",
            "visible_to_user": False,
            "issue_count": 1,
          },
          "days": [
            {
              "day_number": 1,
              "theme": "Downtown Kyoto",
              "cards": [
                {
                  "kind": "place",
                  "time": "12:00-14:30",
                  "title": "Bookstore and Quiet Cafe Break",
                  "area": "Downtown Kyoto",
                  "tags": ["place", "Bookstore", "Cafe"],
                  "options": [
                    {
                      "name": "Quiet Cafe near Bookstore",
                      "category": "cafe",
                    }
                  ],
                }
              ],
            }
          ],
        }
      )

    raise AssertionError(f"Unexpected URL: {url}")


def test_smoke_mobile_flow_fetches_summary_and_prints_compact_cards() -> None:
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

  result = run_smoke_mobile_flow(
    prompt="Plan 2 quiet days in Kyoto.",
    base_url="http://127.0.0.1:8000/",
    user="local",
    model="qwen3.6:27b",
    client=client,
    sleep=lambda _: None,
    output=output.append,
  )

  assert result["run"]["status"] == "completed"
  assert result["summary"]["plan_id"] == "plan-123"
  assert ("GET", "http://127.0.0.1:8000/itinerary-plans/plan-123/summary", {"user": "local"}) in client.calls
  assert "Summary: A relaxed Kyoto plan (Kyoto, Japan)" in output
  assert "Quality: warning (1 hidden issue)" in output
  assert "Day 1: Downtown Kyoto" in output
  assert "  12:00-14:30 | place | Bookstore and Quiet Cafe Break [place, Bookstore, Cafe]" in output
  assert "    option: Quiet Cafe near Bookstore (cafe)" in output
