import json
from dataclasses import dataclass
from typing import Any, Iterator, Literal

import httpx
from northstar.config import get_settings

class OllamaError(RuntimeError):
  """Base error for Ollama client failures."""

class OllamaUnavailableError(OllamaError):
  """Raised when Ollama cannot be reached or returns a failing HTTP response."""

class OllamaTimeoutError(OllamaError):
  """Raised when Ollama takes too long to respond."""

@dataclass(frozen=True)
class ChatStreamEvent:
  kind: Literal["thinking", "content", "tool_call", "done"]
  value: str | dict[str, Any] | None = None

class OllamaClient:
  def __init__(self, base_url: str, timeout: float = 10.0) -> None:
    self.base_url = base_url.rstrip("/")
    self.timeout = timeout

  def list_models(self) -> list[str]:
    payload = self._request("GET", "/api/tags")
    return [
      model["name"]
      for model in payload.get("models", [])
      if "name" in model
    ]
  
  def chat(self, prompt: str, model: str) -> str:
    payload = self._request(
      "POST",
      "/api/chat",
      timeout=60.0,
      json={
        "model": model,
        "messages": [
          {"role": "user", "content": prompt},
        ],
        "stream": False
      },
    )

    message = payload.get("message", {}).get("content")

    if not isinstance(message, str):
      raise RuntimeError("Ollama returned an unexpected chat response.")
    
    return message
  
  def chat_stream(
      self,
      prompt: str,
      model: str,
      think: bool = False,
  ) -> Iterator[ChatStreamEvent]:
    for payload in self._stream_request(
      "POST",
      "/api/chat",
      timeout=httpx.Timeout(connect=5.0, read=300.0, write=30.0, pool=5.0),
      json={
        "model": model,
        "messages": [
          {"role": "user", "content": prompt},
        ],
        "stream": True,
        "think": think
      },
    ):
      message = payload.get("message", {})

      thinking = message.get("thinking")
      if isinstance(thinking, str) and thinking:
        yield ChatStreamEvent(kind="thinking", value=thinking)

      content = message.get("content")
      if isinstance(content, str) and content:
        yield ChatStreamEvent(kind="content", value=content)

      for tool_call in message.get("tool_calls", []):
        yield ChatStreamEvent(kind="tool_call", value=tool_call)

      if payload.get("done"):
        done_reason = payload.get("done_reason")
        yield ChatStreamEvent(
          kind="done",
          value=done_reason if isinstance(done_reason, str) else None,
        )

  def _request(self, method: str, path: str, **kwargs) -> dict[str, Any]:
    timeout = kwargs.pop("timeout", self.timeout)

    try:
      with httpx.Client(base_url=self.base_url, timeout=timeout) as client:
        response = client.request(method, path, **kwargs)
        response.raise_for_status()
    except httpx.ReadTimeout as exc:
      raise OllamaTimeoutError("Ollama took too long to respond.") from exc
    except httpx.HTTPStatusError as exc:
      raise OllamaUnavailableError(
        f"Ollama returned HTTP {exc.response.status_code}."
      ) from exc
    except httpx.HTTPError as exc:
      raise OllamaUnavailableError(
        "Ollama is unavailable. Check that the SSH tunnel and Ollama service are running."
      ) from exc
    
    return response.json()

  def _stream_request(
      self,
      method: str,
      path: str,
      **kwargs
  ) -> Iterator[dict[str, Any]]:
    timeout = kwargs.pop(
      "timeout",
      httpx.Timeout(connect=5.0, read=300.0, write=30.0, pool=5.0),
    )

    try:
      with httpx.Client(base_url=self.base_url, timeout=timeout) as client:
        with client.stream(method, path, **kwargs) as response:
          response.raise_for_status()

          for line in response.iter_lines():
            if not line:
              continue
            yield json.loads(line)
    except httpx.ReadTimeout as exc:
      raise OllamaTimeoutError("Ollama took too long to stream a response.") from exc
    except httpx.HTTPStatusError as exc:
      raise OllamaUnavailableError(
        f"Ollama returned HTTP {exc.response.status_code}."
      ) from exc
    except httpx.HTTPError as exc:
      raise OllamaUnavailableError(
        "Ollama is unavailable. Check that the SSH tunnel and Ollama service are running."
      ) from exc
    except json.JSONDecodeError as exc:
      raise RuntimeError("Ollama returned malformed streaming JSON") from exc

  
def get_ollama_client() -> OllamaClient:
  settings = get_settings()
  return OllamaClient(base_url=settings.ollama_base_url)