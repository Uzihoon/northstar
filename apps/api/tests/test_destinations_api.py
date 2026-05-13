from fastapi.testclient import TestClient

import northstar.api.app as app_module

client = TestClient(app_module.app)


def test_destination_endpoints_publish_response_models() -> None:
  schema = app_module.app.openapi()
  list_schema = schema["paths"]["/destinations"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
  detail_schema = schema["paths"]["/destinations/{destination_id}"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]

  assert list_schema["$ref"].endswith("/DestinationListResponse")
  assert detail_schema["$ref"].endswith("/DestinationResponse")


def test_list_destinations_returns_kyoto() -> None:
  response = client.get("/destinations")

  assert response.status_code == 200

  data = response.json()
  assert data["destinations"][0]["id"] == "japan-kyoto"
  assert data["destinations"][0]["city"] == "Kyoto"
  assert data["destinations"][0]["rag"]["namespace"] == "japan/kyoto"


def test_list_destinations_filters_by_query_and_vibe() -> None:
  response = client.get(
    "/destinations",
    params={
      "q": "walkable temples",
      "country": "Japan",
      "vibe": "quiet neighborhoods",
    },
  )

  assert response.status_code == 200

  data = response.json()
  assert [destination["id"] for destination in data["destinations"]] == ["japan-kyoto"]


def test_list_destinations_returns_seoul_when_filtering_south_korea() -> None:
  response = client.get(
    "/destinations",
    params={
      "q": "cafes neighborhoods",
      "country": "South Korea",
      "vibe": "cafes",
    },
  )

  assert response.status_code == 200

  data = response.json()
  assert [destination["id"] for destination in data["destinations"]] == ["south-korea-seoul"]
  assert data["destinations"][0]["rag"]["namespace"] == "south-korea/seoul"


def test_get_destination_returns_detail() -> None:
  response = client.get("/destinations/japan-kyoto")

  assert response.status_code == 200

  data = response.json()
  assert data["id"] == "japan-kyoto"
  assert "quiet neighborhoods" in data["vibes"]
  assert data["rag"]["doc_types"] == [
    "overview",
    "transport",
    "restaurants",
    "cafes",
    "attractions",
    "neighborhoods",
  ]


def test_get_destination_returns_seoul_detail() -> None:
  response = client.get("/destinations/south-korea-seoul")

  assert response.status_code == 200

  data = response.json()
  assert data["city"] == "Seoul"
  assert data["country"] == "South Korea"
  assert "cafes" in data["vibes"]
  assert data["rag"]["doc_types"] == [
    "overview",
    "transport",
    "restaurants",
    "cafes",
    "sightseeing",
    "neighborhoods",
    "accommodation",
  ]


def test_get_destination_returns_404_when_missing() -> None:
  response = client.get("/destinations/missing-destination")

  assert response.status_code == 404
  assert response.json()["detail"] == "Destination not found."
