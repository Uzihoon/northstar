from northstar.memory.profile_store import merge_profile
from northstar.memory.schemas import PreferenceUpdateCandidate, UserPreferenceProfile

def test_merge_profile_adds_lists_without_overwriting_existing_scalar() -> None:
    current = UserPreferenceProfile(pace="relaxed", interests=["cafes"], food_preferences=["vegetarian"])
    candidate = PreferenceUpdateCandidate(
        pace="fast",
        interests_to_add=["bookstores", "cafes"],
        food_preferences_to_add=["coffee"],
    )

    merged, patch = merge_profile(current, candidate)

    assert merged.pace == "relaxed"
    assert merged.interests == ["cafes", "bookstores"]
    assert merged.food_preferences == ["vegetarian", "coffee"]
    assert patch["ignored_conflicts"] == {"pace": "fast"}
