import re

from northstar.research.schemas import (
  ResearchDraft,
  ResearchValidationIssue,
  ResearchValidationReport,
  TrustRating,
)

EXACT_PRICE_PATTERN = re.compile(
  r"(\$|€|£|¥|\bUSD\b|\bEUR\b|\bJPY\b|\byen\b|\bdollars?\b)\s?\d+|\d+\s?(yen|dollars?|usd|eur|jpy)",
  re.IGNORECASE,
)


def _issue(*, code: str, path: str, message: str) -> ResearchValidationIssue:
  return ResearchValidationIssue(code=code, path=path, message=message)


def validate_research_draft(draft: ResearchDraft) -> ResearchValidationReport:
  issues: list[ResearchValidationIssue] = []

  for index, note in enumerate(draft.stable_notes):
    path = f"stable_notes.{index}"

    if note.trust_rating == TrustRating.blocked:
      issues.append(
        _issue(
          code="blocked_note_in_publishable_draft",
          path=path,
          message="Blocked stable notes must stay in blocked_items.",
        )
      )

    if not note.sources:
      issues.append(
        _issue(
          code="missing_sources",
          path=f"{path}.sources",
          message="Stable notes must include source references.",
        )
      )

    if EXACT_PRICE_PATTERN.search(note.markdown):
      issues.append(
        _issue(
          code="exact_price_in_stable_note",
          path=f"{path}.markdown",
          message="Stable notes should use price levels instead of exact prices.",
        )
      )

  for index, candidate in enumerate(draft.candidates):
    path = f"candidates.{index}"

    if not candidate.source_urls:
      issues.append(
        _issue(
          code="missing_candidate_sources",
          path=f"{path}.source_urls",
          message="Candidates must include at least one source URL.",
        )
      )

  return ResearchValidationReport(passed=not issues, issues=issues)
