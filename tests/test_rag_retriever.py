from northstar.agent.context import ActivePlanContext
from northstar.rag.retriever import build_rag_query


def test_build_rag_query_uses_destination_and_preferences() -> None:
  query = build_rag_query(
    ActivePlanContext(
      destination_city="Kyoto",
      country="Japan",
      pace="relaxed",
      interests=["cafes", "bookstores"],
      food_preferences=["vegetarian"],
    )
  )

  assert "Kyoto" in query
  assert "Japan" in query
  assert "relaxed travel pace" in query
  assert "cafes" in query
  assert "vegetarian" in query
