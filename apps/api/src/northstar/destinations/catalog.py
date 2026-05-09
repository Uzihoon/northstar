from northstar.destinations.schemas import Destination, DestinationRagConfig
from northstar.rag.metadata import normalize_slug


DESTINATIONS = [
  Destination(
    id="japan-kyoto",
    city="Kyoto",
    country="Japan",
    country_slug="japan",
    city_slug="kyoto",
    title="Kyoto, Japan",
    summary="Quiet lanes, temples, cafes, and slow days in Japan's old capital.",
    description=(
      "Kyoto works beautifully for travelers who like atmospheric neighborhoods, "
      "temples, gardens, cafes, bookstores, vegetarian-friendly meals, and a slower "
      "pace between classic sightseeing stops."
    ),
    vibes=[
      "quiet neighborhoods",
      "cafes",
      "temples",
      "walkable",
      "culture",
      "slow travel",
    ],
    best_for=[
      "first-time Japan",
      "slow travel",
      "culture",
      "cafes",
      "walkable neighborhoods",
    ],
    avoid_if=[
      "you want late-night nightlife as the main focus",
      "you prefer beach resorts",
      "you dislike temple-heavy sightseeing",
    ],
    suggested_duration_days=[2, 3, 4],
    hero_image_url=None,
    tags=[
      "japan",
      "kyoto",
      "temples",
      "cafes",
      "vegetarian",
      "quiet",
      "walkable",
      "bookstores",
    ],
    rag=DestinationRagConfig(
      namespace="japan/kyoto",
      country="japan",
      city="kyoto",
      doc_types=[
        "overview",
        "transport",
        "restaurants",
        "cafes",
        "attractions",
        "neighborhoods",
      ],
      source_queries=[
        "Kyoto quiet neighborhoods travel guide",
        "Kyoto vegetarian restaurants travel guide",
        "Kyoto cafes and bookstores itinerary",
        "Kyoto public transport tourist guide",
        "Kyoto temples first time visitor guide",
      ],
    ),
  )
]


def _matches_query(destination: Destination, query: str) -> bool:
  haystack = " ".join(
    [
      destination.id,
      destination.city,
      destination.country,
      destination.title,
      destination.summary,
      destination.description,
      *destination.vibes,
      *destination.best_for,
      *destination.tags,
    ]
  ).lower()

  return all(term in haystack for term in query.lower().split())


def search_destinations(
    *,
    q: str | None = None,
    country: str | None = None,
    vibe: str | None = None,
    limit: int = 20,
) -> list[Destination]:
  country_slug = normalize_slug(country)
  vibe_slug = normalize_slug(vibe)

  results = []
  for destination in DESTINATIONS:
    if country_slug and destination.country_slug != country_slug:
      continue

    destination_vibes = [normalize_slug(item) for item in destination.vibes]
    if vibe_slug and vibe_slug not in destination_vibes:
      continue

    if q and not _matches_query(destination, q):
      continue

    results.append(destination)

  return results[:limit]


def get_destination(destination_id: str) -> Destination | None:
  for destination in DESTINATIONS:
    if destination.id == destination_id:
      return destination

  return None
