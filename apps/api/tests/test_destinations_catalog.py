from northstar.destinations.catalog import get_destination, search_destinations


def test_search_destinations_returns_kyoto_by_default() -> None:
  destinations = search_destinations()

  assert destinations[0].id == "japan-kyoto"
  assert destinations[0].rag.namespace == "japan/kyoto"
  assert "cafes" in destinations[0].rag.doc_types


def test_search_destinations_filters_by_query_country_and_vibe() -> None:
  destinations = search_destinations(
    q="walkable temples",
    country="Japan",
    vibe="quiet neighborhoods",
  )

  assert [destination.id for destination in destinations] == ["japan-kyoto"]


def test_get_destination_returns_none_for_missing_id() -> None:
  destination = get_destination("missing-destination")

  assert destination is None
