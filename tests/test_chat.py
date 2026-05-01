from fastapi.testclient import TestClient

import northstar.api.app as app_module
from northstar.ollama_client import OllamaUnavailableError, OllamaTimeoutError

client = TestClient(app_module.app)

error_message = "Ollama is unavailable. Check that the SSH tunnel and Ollama service are running."

class FakeOllamaClient:
  def chat(self, prompt: str, model: str) -> str:
    return f"{model}: {prompt}"
  
class UnavailableOllamaClient:
  def chat(self, prompt: str, model: str) -> str:
    raise OllamaUnavailableError(error_message)
  
def test_chat_uses_default_model(monkeypatch) -> None:
  monkeypatch.setattr(
    app_module,
    "get_ollama_client",
    lambda: FakeOllamaClient(),
  )

  response = client.post(
    "/chat",
    json={"prompt": "Plan 2 days in Kyoto"},
  )

  assert response.status_code == 200
  assert response.json() == {
    "model": "qwen3.6:27b",
    "message": "qwen3.6:27b: Plan 2 days in Kyoto",
  }

def test_chat_returns_503_when_ollama_is_unavailable(monkeypatch) -> None:
  monkeypatch.setattr(
    app_module,
    "get_ollama_client",
    lambda: UnavailableOllamaClient(),
  )

  response = client.post(
    "/chat",
    json={"prompt": "hello"},
  )

  assert response.status_code == 503
  assert response.json() == {
    "detail": error_message
  }


class TimeoutOllamaClient:
    def chat(self, prompt: str, model: str) -> str:
        raise OllamaTimeoutError("Ollama took too long to respond.")

def test_chat_returns_503_when_ollama_times_out(monkeypatch) -> None:
    monkeypatch.setattr(app_module, "get_ollama_client", lambda: TimeoutOllamaClient())

    response = client.post("/chat", json={"prompt": "hello"})

    assert response.status_code == 503
    assert response.json() == {"detail": "Ollama took too long to respond."}
