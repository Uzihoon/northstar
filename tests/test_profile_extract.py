from northstar.agent.profile_extract import extract_preference_update
from northstar.memory.schemas import PreferenceUpdateCandidate

class FakeOllamaClient:
    def structured_chat(self, *, messages, model, response_format):
        return {
            "pace": "relaxed",
            "interests_to_add": ["cafes", "bookstores"],
            "food_preferences_to_add": ["vegetarian"],
            "dislikes_to_add": [],
            "notes_to_add": ["prefers calm neighborhoods"],
            "evidence": ["best trips were slower and walkable"],
        }

def test_extract_preference_update_returns_candidate() -> None:
    result = extract_preference_update(
        text="I usually love slower trips with cafes and bookstores.",
        model="qwen3.6:27b",
        client=FakeOllamaClient(),
    )

    assert isinstance(result, PreferenceUpdateCandidate)
    assert result.pace == "relaxed"
    assert result.interests_to_add == ["cafes", "bookstores"]
