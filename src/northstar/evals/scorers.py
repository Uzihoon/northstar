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

def score_expected_fields(
    *,
    case_id: str,
    actual: dict[str, Any],
    expect: dict[str, Any],
) -> EvalCaseResult:
  checks: list[EvalCheck] = []

  for field, expected_value in expect.items():
    if field.endswith("_contains"):
      target_field = field.removesuffix("_contains")
      actual_value = actual.get(target_field, [])
      passed = isinstance(actual_value, list) and _contains_all(actual_value, expected_value)
    elif field == "timeline_item_types_contains":
      actual_value = [
        item.get("type")
        for day in actual.get("days", [])
        for item in day.get("timeline_items", [])
      ]
      passed = _contains_all(actual_value, expected_value)
    elif field == "forbidden_time_sources":
      actual_value = [
        item.get("time_source")
        for day in actual.get("days", [])
        for item in day.get("timeline_items", [])
      ]
      passed = not any(value in actual_value for value in expected_value)
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
