from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from northstar.config import get_settings
from northstar.ollama_client import OllamaUnavailableError, get_ollama_client

app = FastAPI(title="Northstar API")

class ChatRequest(BaseModel):
  prompt: str
  model: str | None = None

class ChatResponse(BaseModel):
  model: str
  message: str

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
  
  try:
    return {"models": client.list_models()}
  except OllamaUnavailableError as exc:
    raise HTTPException(status_code=503, detail=str(exc)) from exc
  
@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
  settings = get_settings()
  resolved_model = request.model or settings.default_model
  client = get_ollama_client()

  try:
    message = client.chat(prompt=request.prompt, model=resolved_model)
  except OllamaUnavailableError as exc:
    raise HTTPException(status_code=503, detail=str(exc)) from exc
  
  return ChatResponse(model=resolved_model, message=message)