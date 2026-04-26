import httpx

from northstar.config import get_settings

class OllamaClient:
  def __init__(self, base_url: str, timeout: float = 10.0) -> None:
    self.base_url = base_url.rstrip("/")
    self.timeout = timeout

  def list_models(self) -> list[str]:
    with httpx.Client(base_url=self.base_url, timeout=self.timeout) as client:
      response = client.get("/api/tags")
      response.raise_for_status()

    payload = response.json()
    return [
      model["name"]
      for model in payload.get("models", [])
      if "name" in model
    ]
  
def get_ollama_client() -> OllamaClient:
  settings = get_settings()
  return OllamaClient(base_url=settings.ollama_base_url)