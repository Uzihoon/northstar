from fastapi.testclient import TestClient

import northstar.api.app as app_module

client = TestClient(app_module.app)

class FakeOllamaClient:
  def list_models(self) -> list[str]:
    return ["qwen3.6:27b", "gemma4:31b"]
  
def test_models() -> None:
  app_module.get_ollama_client = lambda: FakeOllamaClient()

  response = client.get("/models")

  assert response.status_code == 200
  assert response.json() == {
    "models": ["qwen3.6:27b", "gemma4:31b"]
  }