from __future__ import annotations

import argparse
import sys
import time
from collections.abc import Callable
from typing import Any

import httpx


class SmokeMobileFlowError(RuntimeError):
  """Raised when the mobile smoke flow cannot complete successfully."""


def _join_url(base_url: str, path: str) -> str:
  return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


def _print_new_events(
    events: list[dict[str, Any]],
    *,
    seen_count: int,
    output: Callable[[str], None],
) -> int:
  for event in events[seen_count:]:
    status = event.get("status", "unknown")
    message = event.get("message", "")
    output(f"{status}: {message}")

  return len(events)


def _print_summary(summary: dict[str, Any], output: Callable[[str], None]) -> None:
  output(
    f"Summary: {summary.get('title', 'Untitled plan')} "
    f"({summary.get('destination', 'unknown destination')})"
  )

  quality = summary.get("quality", {})
  if isinstance(quality, dict):
    issue_count = quality.get("issue_count", 0)
    issue_label = "issue" if issue_count == 1 else "issues"
    output(
      f"Quality: {quality.get('status', 'ok')} "
      f"({issue_count} hidden {issue_label})"
    )

  for day in summary.get("days", []):
    if not isinstance(day, dict):
      continue

    output(f"Day {day.get('day_number')}: {day.get('theme', '')}")

    for card in day.get("cards", []):
      if not isinstance(card, dict):
        continue

      tags = card.get("tags", [])
      tag_text = ", ".join(tags) if isinstance(tags, list) else ""
      output(
        f"  {card.get('time', '')} | {card.get('kind', 'activity')} | "
        f"{card.get('title', '')} [{tag_text}]"
      )

      for option in card.get("options", []):
        if not isinstance(option, dict):
          continue

        output(
          f"    option: {option.get('name', '')} "
          f"({option.get('category', 'option')})"
        )


def _run_with_client(
    *,
    client,
    prompt: str,
    base_url: str,
    user: str,
    model: str | None,
    save: bool,
    poll_interval_seconds: float,
    timeout_seconds: float,
    sleep: Callable[[float], None],
    output: Callable[[str], None],
) -> dict[str, Any]:
  start_payload = {
    "user": user,
    "prompt": prompt,
    "model": model,
    "save": save,
  }

  output("Starting mobile itinerary flow...")
  start_response = client.post(
    _join_url(base_url, "/itinerary-plan-runs"),
    json=start_payload,
  )
  start_response.raise_for_status()
  start_data = start_response.json()
  run_id = start_data["run_id"]
  output(f"Run: {run_id}")

  seen_event_count = _print_new_events(
    start_data.get("progress_events", []),
    seen_count=0,
    output=output,
  )
  deadline = time.monotonic() + timeout_seconds

  while True:
    if time.monotonic() > deadline:
      raise SmokeMobileFlowError(f"Timed out waiting for itinerary planning run {run_id}.")

    sleep(poll_interval_seconds)
    run_response = client.get(
      _join_url(base_url, f"/itinerary-plan-runs/{run_id}"),
      params={"user": user},
    )
    run_response.raise_for_status()
    run_data = run_response.json()

    seen_event_count = _print_new_events(
      run_data.get("progress_events", []),
      seen_count=seen_event_count,
      output=output,
    )

    if run_data["status"] == "failed":
      raise SmokeMobileFlowError(run_data.get("error_message") or "Itinerary planning run failed.")

    if run_data["status"] == "completed":
      plan_id = run_data.get("plan_id")
      if plan_id is None:
        raise SmokeMobileFlowError("Run completed without a saved plan.")

      summary_response = client.get(
        _join_url(base_url, f"/itinerary-plans/{plan_id}/summary"),
        params={"user": user},
      )
      summary_response.raise_for_status()
      summary_data = summary_response.json()
      _print_summary(summary_data, output)

      return {"run": run_data, "summary": summary_data}


def run_smoke_mobile_flow(
    *,
    prompt: str,
    base_url: str = "http://127.0.0.1:8000",
    user: str = "local",
    model: str | None = None,
    save: bool = True,
    poll_interval_seconds: float = 2.0,
    timeout_seconds: float = 600.0,
    client=None,
    sleep: Callable[[float], None] = time.sleep,
    output: Callable[[str], None] = print,
) -> dict[str, Any]:
  if client is not None:
    return _run_with_client(
      client=client,
      prompt=prompt,
      base_url=base_url,
      user=user,
      model=model,
      save=save,
      poll_interval_seconds=poll_interval_seconds,
      timeout_seconds=timeout_seconds,
      sleep=sleep,
      output=output,
    )

  with httpx.Client(timeout=30.0) as http_client:
    return _run_with_client(
      client=http_client,
      prompt=prompt,
      base_url=base_url,
      user=user,
      model=model,
      save=save,
      poll_interval_seconds=poll_interval_seconds,
      timeout_seconds=timeout_seconds,
      sleep=sleep,
      output=output,
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
  parser = argparse.ArgumentParser(
    description="Smoke test the Northstar mobile itinerary flow.",
  )
  parser.add_argument("prompt", help="Trip planning prompt to send to Northstar.")
  parser.add_argument("--base-url", default="http://127.0.0.1:8000")
  parser.add_argument("--user", default="local")
  parser.add_argument("--model", default=None)
  parser.add_argument("--no-save", action="store_true")
  parser.add_argument("--poll-interval", type=float, default=2.0)
  parser.add_argument("--timeout", type=float, default=600.0)
  return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
  args = parse_args(sys.argv[1:] if argv is None else argv)

  try:
    run_smoke_mobile_flow(
      prompt=args.prompt,
      base_url=args.base_url,
      user=args.user,
      model=args.model,
      save=not args.no_save,
      poll_interval_seconds=args.poll_interval,
      timeout_seconds=args.timeout,
    )
  except (SmokeMobileFlowError, httpx.HTTPError) as exc:
    print(f"Mobile smoke flow failed: {exc}", file=sys.stderr)
    return 1

  return 0


if __name__ == "__main__":
  raise SystemExit(main())
