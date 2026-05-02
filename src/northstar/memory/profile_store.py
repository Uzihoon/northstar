from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from northstar.memory.models import PreferenceUpdateModel, User, UserPreferenceProfileModel
from northstar.memory.schemas import PreferenceUpdateCandidate, UserPreferenceProfile

DEFAULT_USER_SLUG = "local"

def get_or_create_user(session: Session, user_slug: str = DEFAULT_USER_SLUG) -> User:
  user = session.scalar(select(User).where(User.slug == user_slug))
  if user is None:
    user = User(slug=user_slug)
    session.add(user)
    session.flush()

  return user

def get_or_create_profile_row(session: Session, user: User) -> UserPreferenceProfileModel:
  profile = session.scalar(
    select(UserPreferenceProfileModel).where(
      UserPreferenceProfileModel.user_id == user.id
    )
  )
  if profile is not None:
    return profile
  profile = UserPreferenceProfileModel(user_id=user.id)  
  session.add(profile)
  session.flush()
  return profile

def orm_to_profile(row: UserPreferenceProfileModel) -> UserPreferenceProfile:
  return UserPreferenceProfile(
    pace=row.pace,
    budget_level=row.budget_level,
    interests=row.interests or [],
    food_preferences=row.food_preferences or [],
    dislikes=row.dislikes or [],
    notes=row.notes or []
  )

def merge_profile(current: UserPreferenceProfile, candidate: PreferenceUpdateCandidate) -> tuple[UserPreferenceProfile, dict[str, Any]]:
  merged = current.model_copy(deep=True)
  patch: dict[str, Any] = {"set": {}, "added": {}, "ignored_conflicts": {}}

  for field in ("pace", "budget_level"):
    incoming = getattr(candidate, field)
    existing = getattr(merged, field)

    if incoming is None:
      continue
    if existing is None:
      setattr(merged, field, incoming)
      patch["set"][field] = incoming.value
    elif existing != incoming:
      patch["ignored_conflicts"][field] = incoming.value
  
  mapping = {
    "interests_to_add": "interests",
    "food_preferences_to_add": "food_preferences",
    "dislikes_to_add": "dislikes",
    "notes_to_add": "notes",
  }

  for source_field, target_field in mapping.items():
    additions = []
    current_values = list(getattr(merged, target_field))
    seen = set(current_values)
    for item in getattr(candidate, source_field):
      if item not in seen:
        current_values.append(item)
        additions.append(item)
        seen.add(item)
    setattr(merged, target_field, current_values)
    if additions:
      patch["added"][target_field] = additions

  return merged, {k: v for k, v in patch.items() if v}


def load_profile(session: Session, user_slug: str = DEFAULT_USER_SLUG) -> UserPreferenceProfile:
  user = get_or_create_user(session, user_slug=user_slug)
  row = get_or_create_profile_row(session, user)
  session.commit()
  return orm_to_profile(row)

def apply_preference_update(
    session: Session,
    *,
    user_slug: str,
    source_kind: str,
    source_text: str,
    candidate: PreferenceUpdateCandidate
) -> tuple[UserPreferenceProfile, dict[str, Any]]:
  user = get_or_create_user(session, user_slug=user_slug)
  row = get_or_create_profile_row(session, user)
  current = orm_to_profile(row)
  merged, patch = merge_profile(current, candidate)

  row.pace = merged.pace.value if merged.pace else None
  row.budget_level = merged.budget_level.value if merged.budget_level else None
  row.interests = merged.interests
  row.food_preferences = merged.food_preferences
  row.dislikes = merged.dislikes
  row.notes = merged.notes

  event = PreferenceUpdateModel(
    user_id=user.id,
    source_kind=source_kind,
    source_text=source_text,
    candidate=candidate.model_dump(mode="json"),
    applied_patch=patch
  )
  session.add(event)
  session.commit()
  return merged, patch