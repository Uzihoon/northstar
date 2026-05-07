from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class EvalCheck:
  name: str
  passed: bool
  expected: object
  actual: object

@dataclass(frozen=True)
class EvalCaseResult:
  case_id: str
  passed: bool
  checks: list[EvalCheck]

def _contains_all(actual: list[object], expected: list[object]) -> bool:
  return set(expected).issubset(set(actual))

def _timeline_items(actual: dict[str, Any]) -> list[dict[str, Any]]:
  return [
    item
    for day in actual.get("days", [])
    for item in day.get("timeline_items", [])
  ]

def _all_transport_items_have_required_metadata(items: list[dict[str, Any]]) -> bool:
  required_fields = [
    "transport_mode",
    "from_location",
    "to_location",
    "duration_minutes",
  ]

  return all(
    all(item.get(field) is not None for field in required_fields)
    for item in items
    if item.get("type") == "transport"
  )

def _count_items_with_non_empty_list(
    items: list[dict[str, Any]],
    field: str,
) -> int:
  return sum(
    1
    for item in items
    if isinstance(item.get(field), list) and len(item[field]) > 0
  )

def score_expected_fields(
    *,
    case_id: str,
    actual: dict[str, Any],
    expect: dict[str, Any],
) -> EvalCaseResult:
  checks: list[EvalCheck] = []

  for field, expected_value in expect.items():
    timeline_items = _timeline_items(actual)

    if field.endswith("_contains"):
      target_field = field.removesuffix("_contains")
      actual_value = actual.get(target_field, [])
      passed = isinstance(actual_value, list) and _contains_all(actual_value, expected_value)
    elif field == "timeline_item_types_contains":
      actual_value = [item.get("type") for item in timeline_items]
      passed = _contains_all(actual_value, expected_value)
    elif field == "forbidden_time_sources":
      actual_value = [item.get("time_source") for item in timeline_items]
      passed = not any(value in actual_value for value in expected_value)
    elif field == "all_transport_items_have_required_metadata":
      actual_value = _all_transport_items_have_required_metadata(timeline_items)
      passed = actual_value == expected_value
    elif field == "min_items_with_source_notes":
      actual_value = _count_items_with_non_empty_list(timeline_items, "source_notes")
      passed = actual_value >= expected_value
    elif field == "min_items_with_preference_match":
      actual_value = _count_items_with_non_empty_list(timeline_items, "preference_match")
      passed = actual_value >= expected_value
    else:
      actual_value = actual.get(field)
      passed = actual_value == expected_value

    checks.append(
      EvalCheck(
        name=field,
        passed=passed,
        expected=expected_value,
        actual=actual_value,
      )
    )

  return EvalCaseResult(
    case_id=case_id,
    passed=all(check.passed for check in checks),
    checks=checks,
  )
