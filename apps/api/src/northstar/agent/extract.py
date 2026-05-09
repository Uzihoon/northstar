import json

from pydantic import ValidationError

from northstar.agent.schemas import TripRequest
from northstar.ollama_client import OllamaClient

class TripExtractionError(RuntimeError):
  """Raised when trip extraction fails or returns invalid structured data."""

EXTRACTION_SYSTEM_PROMPT = f"""
You extract structured trip planning information from a user request.

Rules:
- Return only a JSON object that matches the provided schema.
- Use null for unknown scalar fields.
- Normalize tags to short lowercase phrases.
- interests should contain activities, places, neighborhoods, and vibes.
- food_preferences should contain dietary preferences, cuisines, restaurant styles, and food-related interests.
- If something is clearly food-related, place it in food_preferences instead of interests.
- You may infer the country when the city is widely and unambiguously associated with one country.
  Example: Kyoto -> Japan.
- Do not invent exact dates.
- Only include missing_info codes that materially block a reasonably tailored first draft.
- Do not add every possible missing detail.

Schema:
{json.dumps(TripRequest.model_json_schema(), indent=2)}
""".strip()

def extract_trip_request(
    *,
    prompt: str,
    model: str,
    client: OllamaClient
) -> TripRequest:
  try:
    payload = client.structured_chat(
      messages=[
        {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
      ],
      model=model,
      response_format=TripRequest.model_json_schema()
    )
    return TripRequest.model_validate(payload)
  except ValidationError as exc:
    raise TripExtractionError(
      "Northstar could not validate the extracted trip request."
    ) from exc
  except RuntimeError as exc:
    raise TripExtractionError(
        f"Northstar could not parse the model's structured trip response. {exc}"
    ) from exc