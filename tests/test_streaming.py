from typer.testing import CliRunner

import northstar.cli as cli_module
from northstar.ollama_client import ChatStreamEvent, OllamaClient

runner = CliRunner()

def test_chat_stream_fields_events(monkeypatch) -> None:
  client = OllamaClient(base_url="http://localhost:11434")

  def fake_stream_request(method: str, path: str, **kwargs):
    assert method == "POST"
    assert path == "/api/chat"
    assert kwargs["json"]["model"] == "qwen3.6:27b"
    assert kwargs["json"]["stream"] is True
    assert kwargs["json"]["think"] is True

    yield {"message": {"thinking": "Planning..."}, "done": False}
    yield {"message": {"content": "Day 1 in Kyoto"}, "done": False}
    yield {
      "message": {
        "tool_calls": [
          {
            "function": {
              "name": "get_weather",
              "arguments": {"city": "Kyoto"}
            }
          }
        ]
      },
      "done": False
    }
    yield {"done": True, "done_reason": "stop"}
  
  monkeypatch.setattr(client, "_stream_request", fake_stream_request)

  events = list(
    client.chat_stream(
      prompt = "Plan 2 days in Kyoto",
      model= "qwen3.6:27b",
      think= True,
    )
  )

  assert events == [
    ChatStreamEvent(kind="thinking", value="Planning..."),
    ChatStreamEvent(kind="content", value="Day 1 in Kyoto"),
    ChatStreamEvent(
      kind="tool_call",
      value={
        "function": {
          "name": "get_weather",
          "arguments": {"city": "Kyoto"},
        }
      },
    ),
    ChatStreamEvent(kind="done", value="stop"),
  ]

class FakeStreamingClient:
  def chat_stream(self, prompt: str, model: str, think: bool = False):
    yield ChatStreamEvent(kind="thinking", value="Thinking...")
    yield ChatStreamEvent(kind="content", value="Hello from Nori.")
    yield ChatStreamEvent(
      kind="tool_call",
      value={
        "function": {
          "name": "get_weather",
          "arguments": {"city": "Kyoto"},
        }
      },
    )
    yield ChatStreamEvent(kind="done", value="stop")

def test_ask_stream_prints_events(monkeypatch) -> None:
  monkeypatch.setattr(
    cli_module,
    "get_ollama_client",
    lambda: FakeStreamingClient(),
  )

  result = runner.invoke(
    cli_module.app,
    ["ask-stream", "hello", "--think"],
  )

  assert result.exit_code == 0
  assert "[thinking]" in result.output
  assert "[assistant]" in result.output
  assert "Hello from Nori." in result.output
  assert "[tool_call] get_weather" in result.output