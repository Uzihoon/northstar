from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from northstar.agent.onboarding import OnboardingMessage, run_onboarding_turn
from northstar.db import Base
from northstar.memory.models import PreferenceUpdateModel


@pytest.fixture()
def session() -> Iterator[Session]:
  engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
  Base.metadata.create_all(bind=engine)
  SessionLocal = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)

  with SessionLocal() as db_session:
    yield db_session


class FakeOllamaClient:
  def __init__(self, *, preference_payload=None, reply="Nori reply"):
    self.preference_payload = preference_payload or {
      "pace": None,
      "budget_level": None,
      "interests_to_add": [],
      "food_preferences_to_add": [],
      "dislikes_to_add": [],
      "notes_to_add": [],
      "evidence": [],
    }
    self.reply = reply
    self.chat_messages = []
    self.structured_texts = []

  def structured_chat(self, *, messages, model, response_format):
    self.structured_texts.append(messages[-1]["content"])
    return self.preference_payload

  def chat_turn(self, *, messages, model, tools=None, think=True):
    self.chat_messages.append(messages)

    class Turn:
      content = self.reply

    return Turn()


def test_onboarding_opening_generates_nori_intro_without_storing_chat(session: Session) -> None:
  client = FakeOllamaClient(
    reply=(
      "Hi, I'm Nori. I help plan trips that feel like you. "
      "I'll ask a few easy questions first. Ready?"
    )
  )

  result = run_onboarding_turn(
    session=session,
    user_slug="local",
    messages=[],
    model="qwen3.6:27b",
    client=client,
  )

  preference_events = session.scalars(select(PreferenceUpdateModel)).all()

  assert "I'm Nori" in result.assistant_message
  assert result.profile_patch == {}
  assert result.next_focus == "intro"
  assert result.is_complete is False
  assert preference_events == []
  assert client.structured_texts == []


def test_onboarding_turn_extracts_preferences_and_generates_next_question(session: Session) -> None:
  client = FakeOllamaClient(
    preference_payload={
      "pace": "relaxed",
      "budget_level": None,
      "interests_to_add": ["quiet neighborhoods", "walkable cities"],
      "food_preferences_to_add": ["coffee"],
      "dislikes_to_add": [],
      "notes_to_add": ["loved kyoto because it felt calm"],
      "evidence": ["Kyoto was calm and walkable"],
    },
    reply="That sounds lovely. Do you usually build trips around food, nature, or wandering?",
  )

  result = run_onboarding_turn(
    session=session,
    user_slug="local",
    messages=[
      OnboardingMessage(role="assistant", content="What trip do you still think about?"),
      OnboardingMessage(role="user", content="Kyoto, because it was calm and walkable."),
    ],
    model="qwen3.6:27b",
    client=client,
  )

  preference_events = session.scalars(select(PreferenceUpdateModel)).all()

  assert result.assistant_message.startswith("That sounds lovely.")
  assert result.profile.pace == "relaxed"
  assert result.profile.interests == ["quiet neighborhoods", "walkable cities"]
  assert result.profile.food_preferences == ["coffee"]
  assert result.profile_patch["set"] == {"pace": "relaxed"}
  assert result.profile_patch["added"]["interests"] == ["quiet neighborhoods", "walkable cities"]
  assert result.is_complete is False
  assert result.next_focus == "budget"
  assert len(preference_events) == 1
  assert preference_events[0].source_text == "Kyoto, because it was calm and walkable."


def test_onboarding_ignores_irrelevant_user_message_and_keeps_going(session: Session) -> None:
  client = FakeOllamaClient(
    reply="No worries. Let's keep it easy: what's a trip you still think about?",
  )

  result = run_onboarding_turn(
    session=session,
    user_slug="local",
    messages=[
      OnboardingMessage(role="assistant", content="What trip do you still think about?"),
      OnboardingMessage(role="user", content="idk lol"),
    ],
    model="qwen3.6:27b",
    client=client,
  )

  preference_events = session.scalars(select(PreferenceUpdateModel)).all()

  assert result.profile_patch == {}
  assert result.is_complete is False
  assert result.next_focus == "favorite_trip"
  assert result.assistant_message.startswith("No worries.")
  assert len(preference_events) == 1
  assert preference_events[0].applied_patch == {}
