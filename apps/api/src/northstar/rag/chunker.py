from dataclasses import dataclass

@dataclass(frozen=True)
class TextChunk:
  index: int
  text: str

def chunk_markdown(text: str, max_chars: int = 1200) -> list[TextChunk]:
  paragraphs = [part.strip() for part in text.split("\n\n") if part.strip()]
  chunks: list[TextChunk] = []
  current: list[str] = []
  current_size = 0

  for paragraph in paragraphs:
    paragraph_size = len(paragraph)

    if current and current_size + paragraph_size + 2 > max_chars:
      chunks.append(TextChunk(index=len(chunks), text="\n\n".join(current)))
      current = []
      current_size = 0

    current.append(paragraph)
    current_size += paragraph_size + 2

  if current:
    chunks.append(TextChunk(index=len(chunks), text="\n\n".join(current)))

  return chunks

