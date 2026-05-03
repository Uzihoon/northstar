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
