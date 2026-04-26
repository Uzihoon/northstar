from fastapi import FastAPI

from northstar.config import get_settings
from northstar.ollama_client import get_ollama_client

app = FastAPI(title="Northstar API")

@app.get("/health")
def health() -> dict[str, str]:
  settings = get_settings()
  return {
    "status": "ok",
    "app": settings.app_name,
    "environment": settings.environment,
    "ollama_base_url": settings.ollama_base_url,
    "default_model": settings.default_model,
  }

@app.get("/models")
def models() -> dict[str, list[str]]:
  client = get_ollama_client()
  return {"models": client.list_models()}