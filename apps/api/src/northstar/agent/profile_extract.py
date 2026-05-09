from pydantic import ValidationError

from northstar.memory.schemas import PreferenceUpdateCandidate
from northstar.ollama_client import OllamaClient

class PreferenceExtractionError(RuntimeError):
  pass

PREFERENCE_SYSTEM_PROMPT = """
Extract durable travel preference updates from the conversation snippet.

Rules:
- Return only JSON matching the schema.
- Only capture preferences likely to remain true across multiple trips.
- Ignore destination-specific requests, one-off logistics, and trip dates.
- Use *_to_add lists for list updates.
- Use short lowercase phrases.
- Only set pace or budget_level when the preference sounds stable.
""".strip()

def extract_preference_update(*, text: str, model: str, client: OllamaClient) -> PreferenceUpdateCandidate:
  try:
    payload = client.structured_chat(
      messages=[
        {"role": "system", "content": PREFERENCE_SYSTEM_PROMPT},
        {"role": "user", "content": text},
      ],
      model=model,
      response_format=PreferenceUpdateCandidate.model_json_schema(),
    )
    return PreferenceUpdateCandidate.model_validate(payload)
  except ValidationError as exc:
    raise PreferenceExtractionError("Northstar could not validate the extracted preference update.") from exc
  except RuntimeError as exc:
    raise PreferenceExtractionError(f"Northstar could not parse the model's structured preference response. {exc}")
  