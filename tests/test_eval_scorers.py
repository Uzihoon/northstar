from northstar.evals.scorers import score_expected_fields


def test_score_expected_fields_checks_exact_and_contains_fields() -> None:
  result = score_expected_fields(
    case_id="case-1",
    actual={
      "destination_city": "Kyoto",
      "interests": ["cafes", "bookstores", "quiet vibes"],
    },
    expect={
      "destination_city": "Kyoto",
      "interests_contains": ["cafes", "bookstores"],
    },
  )

  assert result.passed is True
  assert all(check.passed for check in result.checks)


def test_score_expected_fields_detects_missing_contains_value() -> None:
  result = score_expected_fields(
    case_id="case-1",
    actual={"interests": ["cafes"]},
    expect={"interests_contains": ["cafes", "bookstores"]},
  )

  assert result.passed is False


def test_score_expected_fields_checks_transport_metadata() -> None:
  result = score_expected_fields(
    case_id="case-1",
    actual={
      "days": [
        {
          "timeline_items": [
            {
              "type": "transport",
              "title": "Move to Gion",
              "transport_mode": "bus",
              "from_location": "Philosopher's Path",
              "to_location": "Gion",
              "duration_minutes": 25,
            }
          ]
        }
      ]
    },
    expect={"all_transport_items_have_required_metadata": True},
  )

  assert result.passed is True


def test_score_expected_fields_detects_incomplete_transport_metadata() -> None:
  result = score_expected_fields(
    case_id="case-1",
    actual={
      "days": [
        {
          "timeline_items": [
            {
              "type": "transport",
              "title": "Move to Gion",
              "transport_mode": None,
              "duration_minutes": None,
            }
          ]
        }
      ]
    },
    expect={"all_transport_items_have_required_metadata": True},
  )

  assert result.passed is False


def test_score_expected_fields_checks_minimum_rag_sourced_items() -> None:
  result = score_expected_fields(
    case_id="case-1",
    actual={
      "days": [
        {
          "timeline_items": [
            {"type": "cafe", "source_notes": ["Curated cafe note."]},
            {"type": "place", "source_notes": ["Curated neighborhood note."]},
          ]
        }
      ]
    },
    expect={"min_items_with_source_notes": 2},
  )

  assert result.passed is True


def test_score_expected_fields_checks_minimum_preference_matched_items() -> None:
  result = score_expected_fields(
    case_id="case-1",
    actual={
      "days": [
        {
          "timeline_items": [
            {"type": "cafe", "preference_match": ["cafes"]},
            {"type": "meal", "preference_match": ["vegetarian"]},
            {"type": "place", "preference_match": []},
          ]
        }
      ]
    },
    expect={"min_items_with_preference_match": 2},
  )

  assert result.passed is True
