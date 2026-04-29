import pytest

from northstar.agent.extract import TripExtractionError, extract_trip_request
from northstar.agent.schemas import MissingInfoCode, TripRequest


class FakeOllamaClient:
    def structured_chat(self, *, messages, model, response_format):
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

class BrokenStructuredClient:
    def structured_chat(self, *, messages, model, response_format):
        raise RuntimeError("bad structured output")


def test_extract_trip_request_returns_validated_schema() -> None:
    client = FakeOllamaClient()

    result = extract_trip_request(
        prompt="Plan 2 quiet days in Kyoto next weekend. I like cafes, bookstores, and vegetarian food.",
        model="qwen3.6:27b",
        client=client,
    )

    assert isinstance(result, TripRequest)
    assert result.destination_city == "Kyoto"
    assert result.country == "Japan"
    assert result.duration_days == 2
    assert result.pace == "relaxed"
    assert result.interests == ["cafes", "bookstores"]
    assert result.food_preferences == ["vegetarian"]
    assert result.missing_info == [MissingInfoCode.exact_travel_dates]

def test_extract_trip_request_raises_clean_error_on_bad_output() -> None:
    client = BrokenStructuredClient()

    with pytest.raises(TripExtractionError):
        extract_trip_request(
            prompt="Plan 2 days in Kyoto.",
            model="qwen3.6:27b",
            client=client,
        )
