import json
from pathlib import Path

from northstar.evals.runner import run_eval_suite


class FakeOllamaClient:
  def structured_chat(self, *, messages, model, response_format):
    schema_title = response_format.get("title")

    if schema_title == "TripRequest":
      return {
        "destination_city": "Kyoto",
        "country": "Japan",
        "start_date": None,
        "end_date": None,
        "duration_days": 2,
        "budget_level": None,
        "pace": "relaxed",
        "interests": ["cafes", "bookstores"],
        "food_preferences": ["vegetarian"],
        "constraints": [],
        "missing_info": ["exact_travel_dates"],
      }

    raise AssertionError(f"Unexpected schema: {schema_title}")


def test_run_eval_suite_scores_trip_extraction(tmp_path: Path) -> None:
  cases_dir = tmp_path / "cases"
  cases_dir.mkdir()
  (cases_dir / "trip_extraction.jsonl").write_text(
    json.dumps({
      "id": "kyoto",
      "input": "Plan 2 quiet days in Kyoto.",
      "expect": {
        "destination_city": "Kyoto",
        "interests_contains": ["cafes"],
      },
    }) + "\n"
  )


  result = run_eval_suite(
    suite="trip_extraction",
    model="qwen3.6:27b",
    client=FakeOllamaClient(),
    cases_dir=cases_dir,
  )

  assert result.passed == 1
  assert result.failed == 0
  assert result.pass_rate == 1.0
