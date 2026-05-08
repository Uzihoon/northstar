from typing import Literal

from pydantic import BaseModel
from sqlalchemy.orm import Session

from northstar.agent.profile_extract import extract_preference_update
from northstar.memory.profile_store import apply_preference_update, load_profile
from northstar.memory.schemas import UserPreferenceProfile
from northstar.ollama_client import OllamaClient

ONBOARDING_OPENING_PROMPT = """
You are Nori, a warm travel-planning assistant.

Write the first onboarding message for a new user.
Goals:
- Introduce yourself as Nori.
- Say you help plan trips that match the user's travel style.
- Explain that you'll ask a few easy questions to learn their preferences.
- Keep it friendly, casual, and low-pressure.
- End by asking if they're ready.
- Keep it under 80 words.
""".strip()

ONBOARDING_REPLY_SYSTEM_PROMPT = """
You are Nori, a warm travel-planning assistant.

Continue a short onboarding conversation that learns durable travel preferences.
Rules:
- Sound like a friendly travel buddy, not a form.
- Ask only one easy question at a time.
- If the user's latest response was vague or irrelevant, gently continue without scolding.
- Do not plan an itinerary yet.
- Keep the reply under 80 words.
""".strip()

class OnboardingMessage(BaseModel):
  role: Literal["assistant", "user"]
  content: str

class OnboardingTurnResult(BaseModel):
  assistant_message: str
  profile_patch: dict[str, object]
  profile: UserPreferenceProfile
  is_complete: bool
  next_focus: str

def _latest_user_message(messages: list[OnboardingMessage]) -> OnboardingMessage | None:
  for message in reversed(messages):
    if message.role == "user":
      return message
  return None

def _signal_count(profile: UserPreferenceProfile) -> int:
  count = 0
  if profile.pace is not None:
    count += 1
  if profile.budget_level is not None:
    count += 1
  if profile.interests:
    count += 1
  if profile.food_preferences:
    count += 1
  if profile.dislikes:
    count += 1
  if profile.notes:
    count += 1
  return count

def _is_complete(profile: UserPreferenceProfile, messages: list[OnboardingMessage]) -> bool:
  user_turns = len([message for message in messages if message.role == "user"])
  return user_turns >= 3 and _signal_count(profile) >= 3

def _next_focus(profile: UserPreferenceProfile, messages: list[OnboardingMessage]) -> str:
  if not messages:
    return "intro"
  if profile.pace is None and not profile.interests:
    return "favorite_trip"
  if profile.pace is None:
    return "pace"
  if len(profile.interests) < 2:
    return "interests"
  if not profile.food_preferences:
    return "food"
  if profile.budget_level is None:
    return "budget"
  if not profile.dislikes:
    return "dislikes"
  return "summary"

def _generate_opening_message(*, model: str, client: OllamaClient) -> str:
  turn = client.chat_turn(
    messages=[
      {"role": "user", "content": ONBOARDING_OPENING_PROMPT},
    ],
    model=model,
    think=False,
  )

  return turn.content.strip()

def _generate_reply(
    *,
    messages: list[OnboardingMessage],
    profile: UserPreferenceProfile,
    profile_patch: dict[str, object],
    next_focus: str,
    is_complete: bool,
    model: str,
    client: OllamaClient,
) -> str:
  context = {
    "current_profile": profile.model_dump(mode="json"),
    "profile_patch_from_latest_user_message": profile_patch,
    "next_focus": next_focus,
    "is_complete": is_complete,
  }
  chat_messages = [
    {"role": "system", "content": ONBOARDING_REPLY_SYSTEM_PROMPT},
    {
      "role": "user",
      "content": (
        "Use this onboarding state to guide your next reply:\n"
        f"{context}"
      ),
    },
    *[
      message.model_dump()
      for message in messages[-10:]
    ],
  ]

  turn = client.chat_turn(
    messages=chat_messages,
    model=model,
    think=False,
  )

  return turn.content.strip()

def run_onboarding_turn(
    *,
    session: Session,
    user_slug: str,
    messages: list[OnboardingMessage],
    model: str,
    client: OllamaClient,
) -> OnboardingTurnResult:
  if not messages:
    profile = load_profile(session, user_slug=user_slug)
    return OnboardingTurnResult(
      assistant_message=_generate_opening_message(model=model, client=client),
      profile_patch={},
      profile=profile,
      is_complete=False,
      next_focus="intro",
    )

  latest_user_message = _latest_user_message(messages)
  profile_patch: dict[str, object] = {}

  if latest_user_message is not None:
    candidate = extract_preference_update(
      text=latest_user_message.content,
      model=model,
      client=client,
    )
    profile, profile_patch = apply_preference_update(
      session,
      user_slug=user_slug,
      source_kind="onboarding",
      source_text=latest_user_message.content,
      candidate=candidate,
    )
  else:
    profile = load_profile(session, user_slug=user_slug)

  is_complete = _is_complete(profile, messages)
  next_focus = "summary" if is_complete else _next_focus(profile, messages)

  return OnboardingTurnResult(
    assistant_message=_generate_reply(
      messages=messages,
      profile=profile,
      profile_patch=profile_patch,
      next_focus=next_focus,
      is_complete=is_complete,
      model=model,
      client=client,
    ),
    profile_patch=profile_patch,
    profile=profile,
    is_complete=is_complete,
    next_focus=next_focus,
  )
