from northstar.research.schemas import (
  CandidateOption,
  PriceLevel,
  ResearchDraft,
  ResearchTarget,
  ResearchTheme,
  SourceReference,
  StableNoteDraft,
  TrustRating,
)
from northstar.research.validator import validate_research_draft


def test_validate_research_draft_accepts_sourced_notes_and_candidates() -> None:
  source = SourceReference(
    title="Kyoto Travel",
    url="https://kyoto.travel/en/",
  )
  draft = ResearchDraft(
    target=ResearchTarget(
      country="Japan",
      city="Kyoto",
      themes=[ResearchTheme.cafes],
    ),
    stable_notes=[
      StableNoteDraft(
        theme=ResearchTheme.cafes,
        title="Kyoto cafe strategy",
        markdown="## Cafe Areas\n\nHigashiyama works well for scenic breaks.",
        trust_rating=TrustRating.high,
        sources=[source],
      )
    ],
    candidates=[
      CandidateOption(
        name="Example Coffee",
        category="cafe",
        country="Japan",
        city="Kyoto",
        area="Kawaramachi",
        description="Central coffee stop.",
        price_level=PriceLevel.moderate,
        trust_rating=TrustRating.medium,
        source_urls=["https://example.com/cafe"],
      )
    ],
  )

  report = validate_research_draft(draft)

  assert report.passed is True
  assert report.issues == []


def test_validate_research_draft_blocks_missing_sources() -> None:
  draft = ResearchDraft(
    target=ResearchTarget(
      country="Japan",
      city="Kyoto",
      themes=[ResearchTheme.cafes],
    ),
    stable_notes=[
      StableNoteDraft(
        theme=ResearchTheme.cafes,
        title="Unsourced note",
        markdown="## Cafe Areas\n\nTrust me.",
        trust_rating=TrustRating.medium,
        sources=[],
      )
    ],
  )

  report = validate_research_draft(draft)

  assert report.passed is False
  assert report.issues[0].code == "missing_sources"


def test_validate_research_draft_rejects_exact_prices_in_stable_notes() -> None:
  draft = ResearchDraft(
    target=ResearchTarget(
      country="Japan",
      city="Kyoto",
      themes=[ResearchTheme.overview],
    ),
    stable_notes=[
      StableNoteDraft(
        theme=ResearchTheme.overview,
        title="Budget note",
        markdown="Temple entry is 600 yen.",
        trust_rating=TrustRating.high,
        sources=[SourceReference(title="Source", url="https://example.com")],
      )
    ],
  )

  report = validate_research_draft(draft)

  assert report.passed is False
  assert report.issues[0].code == "exact_price_in_stable_note"
