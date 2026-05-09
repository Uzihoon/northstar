from northstar.agent.context import ActivePlanContext
from northstar.rag.retriever import build_rag_query, retrieve_travel_context
from northstar.rag.store import RagSearchResult


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

def test_retrieve_travel_context_falls_back_to_broad_search() -> None:
  calls = []

  def fake_search(**kwargs):
    calls.append(kwargs)

    if kwargs.get("country") == "japan" and kwargs.get("city") == "kyoto":
      return []

    return [
      RagSearchResult(
        chunk_id="chunk-1",
        source_path="rag_docs/japan/kyoto/cafes.md",
        text="Kyoto has quiet cafe breaks near the Philosopher's Path.",
        metadata={"country": "japan", "city": "kyoto", "doc_type": "cafes"},
        score=0.88,
      )
    ]

  context = ActivePlanContext(
    destination_city="Kyoto",
    country="Japan",
    interests=["cafes"],
  )

  rag_context = retrieve_travel_context(
    session=object(),
    context=context,
    client=object(),
    embedding_model="qwen3-embedding:0.6b",
    embedding_dimensions=1024,
    limit=3,
    search_fn=fake_search,
  )

  assert calls[0]["country"] == "japan"
  assert calls[0]["city"] == "kyoto"
  assert "country" not in calls[1]
  assert "city" not in calls[1]
  assert rag_context.notes == [
    "Kyoto has quiet cafe breaks near the Philosopher's Path."
  ]
  assert rag_context.sources[0].source_path == "rag_docs/japan/kyoto/cafes.md"
