from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError

from northstar.agent.extract import TripExtractionError
from northstar.agent.itinerary import ItineraryGenerationError
from northstar.agent.planner_service import generate_and_optionally_save_itinerary
from northstar.db import get_session
from northstar.config import get_settings
from northstar.ollama_client import OllamaError, get_ollama_client

app = FastAPI(title="Northstar API")

class ChatRequest(BaseModel):
  prompt: str
  model: str | None = None

class ChatResponse(BaseModel):
  model: str
  message: str

class ItineraryPlanRequest(BaseModel):
  prompt: str
  user: str = "local"
  model: str | None = None
  save: bool = True

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
  except OllamaError as exc:
    raise HTTPException(status_code=503, detail=str(exc)) from exc
  
@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
  settings = get_settings()
  resolved_model = request.model or settings.default_model
  client = get_ollama_client()

  try:
    message = client.chat(prompt=request.prompt, model=resolved_model)
  except OllamaError as exc:
    raise HTTPException(status_code=503, detail=str(exc)) from exc
  
  return ChatResponse(model=resolved_model, message=message)

@app.post("/itinerary-plans")
def create_itinerary_plan(request: ItineraryPlanRequest) -> dict:
  settings = get_settings()
  resolved_model = request.model or settings.default_model
  client = get_ollama_client()

  try:
    with get_session() as session:
      result = generate_and_optionally_save_itinerary(
        prompt=request.prompt,
        user_slug=request.user,
        model=resolved_model,
        client=client,
        session=session,
        save=request.save
      )
  except (OllamaError, TripExtractionError, ItineraryGenerationError) as exc:
    raise HTTPException(status_code=503, detail=str(exc)) from exc
  except SQLAlchemyError as exc:
    raise HTTPException(status_code=503, detail="Database is unavailable.") from exc
  
  return {
    "plan_id": result.saved.plan_id if result.saved else None,
    "trip_request_id": result.saved.trip_request_id if result.saved else None,
    "trip_request": result.trip_request.model_dump(mode="json"),
    "active_context": result.active_context.model_dump(mode="json"),
    "itinerary": result.itinerary.model_dump(mode="json")
  }