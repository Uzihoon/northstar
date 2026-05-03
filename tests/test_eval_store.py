from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from northstar.db import Base
from northstar.evals.scorers import EvalCaseResult, EvalCheck
from northstar.evals.runner import EvalSuiteResult
from northstar.memory.eval_store import get_eval_run, list_eval_runs, save_eval_run


@pytest.fixture()
def session() -> Iterator[Session]:
  engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
  Base.metadata.create_all(bind=engine)
  SessionLocal = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)

  with SessionLocal() as db_session:
    yield db_session


def test_save_eval_run_persists_summary_and_case_results(session: Session) -> None:
  result = EvalSuiteResult(
    suite="trip_extraction",
    passed=1,
    failed=0,
    results=[
      EvalCaseResult(
        case_id="kyoto",
        passed=True,
        checks=[
          EvalCheck(
            name="destination_city",
            passed=True,
            expected="Kyoto",
            actual="Kyoto",
          )
        ],
      )
    ],
  )

  saved = save_eval_run(
    session,
    result=result,
    model_name="qwen3.6:27b",
  )

  runs = list_eval_runs(session)
  stored = get_eval_run(session, run_id=saved.run_id)

  assert len(runs) == 1
  assert runs[0].run_id == saved.run_id
  assert runs[0].pass_rate == 1.0
  assert stored is not None
  assert stored.case_results[0]["case_id"] == "kyoto"
  assert stored.case_results[0]["checks"][0]["expected"] == "Kyoto"
