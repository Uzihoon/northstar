import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from northstar.agent.context import ActivePlanContext
from northstar.agent.extract import extract_trip_request
from northstar.agent.itinerary import generate_itinerary_plan
from northstar.agent.profile_extract import extract_preference_update
from northstar.evals.scorers import EvalCaseResult, score_expected_fields
from northstar.ollama_client import OllamaClient

@dataclass(frozen=True)
class EvalSuiteResult:
  suite: str
  passed: int
  failed: int
  results: list[EvalCaseResult]

  @property
  def total(self) -> int:
    return self.passed + self.failed
  
  @property
  def pass_rate(self) -> float:
    if self.total == 0:
      return 0.0
    return self.passed / self.total
  
def load_jsonl(path: Path) -> list[dict[str, Any]]:
  cases: list[dict[str, Any]] = []

  for line in path.read_text().splitlines():
    line = line.strip()
    if not line:
      continue
    cases.append(json.loads(line))

  return cases

def run_eval_suite(
    *,
    suite: str,
    model: str,
    client: OllamaClient,
    cases_dir: Path = Path("evals/cases"),
) -> EvalSuiteResult:
  cases = load_jsonl(cases_dir / f"{suite}.jsonl")
  results: list[EvalCaseResult] = []

  for case in cases:
    if suite == "trip_extraction":
      output = extract_trip_request(
        prompt=case["input"],
        model=model,
        client=client,
      ).model_dump(mode="json")
    elif suite == "preference_extraction":
      output = extract_preference_update(
        text=case["input"],
        model=model,
        client=client,
      ).model_dump(mode="json")
    elif suite == "itinerary_structure":
      context = ActivePlanContext.model_validate(case["context"])
      output = generate_itinerary_plan(
        context=context,
        model=model,
        client=client,
      ).itinerary.model_dump(mode="json")
    else:
      raise ValueError(f"Unknown eval suite: {suite}")
    
    results.append(
      score_expected_fields(
        case_id=case["id"],
        actual=output,
        expect=case["expect"],
      )
    )
  
  passed = sum(1 for result in results if result.passed)
  failed = len(results) - passed

  return EvalSuiteResult(
    suite=suite,
    passed=passed,
    failed=failed,
    results=results,
  )
