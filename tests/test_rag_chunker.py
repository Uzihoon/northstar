from northstar.rag.chunker import chunk_markdown


def test_chunk_markdown_groups_paragraphs() -> None:
  chunks = chunk_markdown(
    "First paragraph.\n\nSecond paragraph.\n\nThird paragraph.",
    max_chars=40,
  )

  assert len(chunks) == 2
  assert chunks[0].index == 0
  assert "First paragraph." in chunks[0].text
  assert chunks[1].index == 1
