from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from typing import Any

import httpx


def _join_url(base_url: str, path: str) -> str:
  return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


def _call_onboarding(
    *,
    client,
    base_url: str,
    user: str,
    model: str | None,
    messages: list[dict[str, str]],
) -> dict[str, Any]:
  response = client.post(
    _join_url(base_url, "/onboarding/messages"),
    json={
      "user": user,
      "model": model,
      "messages": messages,
    },
  )
  response.raise_for_status()
  return response.json()


def _run_with_client(
    *,
    client,
    base_url: str,
    user: str,
    model: str | None,
    input_fn: Callable[[str], str],
    output: Callable[[str], None],
) -> dict[str, Any]:
  messages: list[dict[str, str]] = []
  profile: dict[str, Any] = {}

  output("Starting onboarding with Nori. Type /done to stop.")
  while True:
    data = _call_onboarding(
      client=client,
      base_url=base_url,
      user=user,
      model=model,
      messages=messages[-10:],
    )

    assistant_message = data["assistant_message"]
    profile = data["profile"]
    messages.append({"role": "assistant", "content": assistant_message})
    output(f"Nori: {assistant_message}")

    if data["profile_patch"]:
      output(f"Patch: {data['profile_patch']}")

    if data["is_complete"]:
      output("Onboarding complete.")
      break

    user_message = input_fn("You: ").strip()
    if user_message == "/done":
      break
    if not user_message:
      continue

    messages.append({"role": "user", "content": user_message})

  output(f"Final profile: {profile}")
  return {
    "messages": messages,
    "profile": profile,
  }


def run_smoke_onboarding(
    *,
    base_url: str = "http://127.0.0.1:8000",
    user: str = "local",
    model: str | None = None,
    client=None,
    input_fn: Callable[[str], str] = input,
    output: Callable[[str], None] = print,
) -> dict[str, Any]:
  if client is not None:
    return _run_with_client(
      client=client,
      base_url=base_url,
      user=user,
      model=model,
      input_fn=input_fn,
      output=output,
    )

  with httpx.Client(timeout=60.0) as http_client:
    return _run_with_client(
      client=http_client,
      base_url=base_url,
      user=user,
      model=model,
      input_fn=input_fn,
      output=output,
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
  parser = argparse.ArgumentParser(
    description="Smoke test the Northstar onboarding chat flow.",
  )
  parser.add_argument("--base-url", default="http://127.0.0.1:8000")
  parser.add_argument("--user", default="local")
  parser.add_argument("--model", default=None)
  return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
  args = parse_args(sys.argv[1:] if argv is None else argv)

  try:
    run_smoke_onboarding(
      base_url=args.base_url,
      user=args.user,
      model=args.model,
    )
  except httpx.HTTPError as exc:
    print(f"Onboarding smoke run failed: {exc}", file=sys.stderr)
    return 1

  return 0


if __name__ == "__main__":
  raise SystemExit(main())
