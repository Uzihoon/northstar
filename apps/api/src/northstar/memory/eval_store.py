from dataclasses import dataclass

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from northstar.evals.runner import EvalSuiteResult
from northstar.memory.models import EvalCaseResultModel, EvalRunModel

@dataclass(frozen=True)
class SavedEvalRun:
  run_id: str

@dataclass(frozen=True)
class EvalRunSummary:
  run_id: str
  suite: str
  model_name: str
  passed: int
  failed: int
  total: int
  pass_rate: float
  created_at: str

@dataclass(frozen=True)
class StoredEvalRun:
  run_id: str
  suite: str
  model_name: str
  passed: int
  failed: int
  total: int
  pass_rate: float
  created_at: str
  case_results: list[dict[str, object]]

def save_eval_run(
    session: Session,
    *,
    result: EvalSuiteResult,
    model_name: str
) -> SavedEvalRun:
  run = EvalRunModel(
    suite=result.suite,
    model_name=model_name,
    passed=result.passed,
    failed=result.failed,
    total=result.total,
    pass_rate=result.pass_rate,
  )
  session.add(run)
  session.flush()

  for case_result in result.results:
    session.add(
      EvalCaseResultModel(
        eval_run_id=run.id,
        case_id=case_result.case_id,
        passed=case_result.passed,
        checks=[
          {
            "name": check.name,
            "passed": check.passed,
            "expected": check.expected,
            "actual": check.actual,
          }
          for check in case_result.checks
        ],
      )
    )
  
  session.commit()
  return SavedEvalRun(run_id=run.id)


def list_eval_runs(session: Session) -> list[EvalRunSummary]:
  rows = session.scalars(
    select(EvalRunModel).order_by(desc(EvalRunModel.created_at))
  ).all()

  return [
    EvalRunSummary(
      run_id=row.id,
      suite=row.suite,
      model_name=row.model_name,
      passed=row.passed,
      failed=row.failed,
      total=row.total,
      pass_rate=row.pass_rate,
      created_at=row.created_at.isoformat(),
    )
    for row in rows
  ]

def get_eval_run(session: Session, run_id: str) -> StoredEvalRun | None:
  row = session.scalar(select(EvalRunModel).where(EvalRunModel.id == run_id))
  if row is None:
    return None
  
  return StoredEvalRun(
    run_id=row.id,
    suite=row.suite,
    model_name=row.model_name,
    passed=row.passed,
    failed=row.failed,
    total=row.total,
    pass_rate=row.pass_rate,
    created_at=row.created_at.isoformat(),
    case_results=[
      {
        "case_id": case.case_id,
        "passed": case.passed,
        "checks": case.checks,
      }
      for case in row.case_results
    ]
  )