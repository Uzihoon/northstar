import hashlib
import html
import re
from typing import Callable, Protocol

import httpx

from northstar.research.schemas import ResearchTarget


class FetchResponse(Protocol):
  text: str

  def raise_for_status(self) -> None:
    ...


FetchGet = Callable[..., FetchResponse]


def hash_text(text: str) -> str:
  return hashlib.sha256(text.encode("utf-8")).hexdigest()


def html_to_text(raw_html: str) -> str:
  without_scripts = re.sub(
    r"<(script|style)\b[^>]*>.*?</\1>",
    " ",
    raw_html,
    flags=re.DOTALL | re.IGNORECASE,
  )
  without_tags = re.sub(r"<[^>]+>", " ", without_scripts)
  unescaped = html.unescape(without_tags)
  return re.sub(r"\s+", " ", unescaped).strip()


class TrustedUrlFetcher:
  def __init__(
      self,
      *,
      timeout: float = 20.0,
      get: FetchGet | None = None,
  ) -> None:
    self.timeout = timeout
    self.get = get or httpx.get

  def fetch_texts(self, *, target: ResearchTarget) -> list[str]:
    texts: list[str] = []

    for url in target.trusted_urls:
      response = self.get(
        url,
        timeout=self.timeout,
        follow_redirects=True,
      )
      response.raise_for_status()
      texts.append(html_to_text(response.text))

    return texts
