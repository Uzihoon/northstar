import httpx

from northstar.config import get_settings

class OllamaUnavailableError(RuntimeError):
  """Raised when Ollama cannot be reached or returns a failing HTTP response."""

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
  
  def chat(self, prompt: str, model: str) -> str:
    payload = self._request(
      "POST",
      "/api/chat",
      json={
        "model": model,
        "messages": [
          {"role": "user", "content": prompt},
        ],
        "stream": False
      }
    )

    message = payload.get("message", {}).get("content")
    if not isinstance(message, str):
      raise RuntimeError("Ollama returned an unexpected chat response.")
    
    return message

  def _request(self, method: str, path: str, **kwargs) -> dict:
    try:
      with httpx.Client(base_url=self.base_url, timeout=self.timeout) as client:
        response = client.request(method, path, **kwargs)
        response.raise_for_status()
    except httpx.HTTPError as exc:
      raise OllamaUnavailableError(
        "Ollama is unavailable. Check that the SSH tunnel and Ollama service are running."
      ) from exc
  
    return response.json()
  
def get_ollama_client() -> OllamaClient:
  settings = get_settings()
  return OllamaClient(base_url=settings.ollama_base_url)