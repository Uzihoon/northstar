from pathlib import Path

def normalize_slug(value: str | None) -> str | None:
  if value is None:
    return None

  normalized = value.strip().lower().replace(" ", "-").replace("_", "-")
  return normalized or None

def infer_rag_metadata_from_path(path: Path) -> dict[str, object]:
  parts = path.with_suffix("").parts

  if "rag_docs" not in parts:
    return {}

  rag_docs_index = parts.index("rag_docs")
  relative_parts = parts[rag_docs_index + 1:]

  if len(relative_parts) < 3:
    return {}

  country, city, doc_type = relative_parts[-3:]

  return {
    "country": normalize_slug(country),
    "city": normalize_slug(city),
    "doc_type": normalize_slug(doc_type),
    "source_type": "curated_markdown",
  }

def build_rag_metadata(
    *,
    path: Path,
    country: str | None = None,
    city: str | None = None,
    doc_type: str | None = None,
) -> dict[str, object]:
  inferred = infer_rag_metadata_from_path(path)

  metadata = {
    **inferred,
    "source_type": "curated_markdown",
  }

  explicit_country = normalize_slug(country)
  explicit_city = normalize_slug(city)
  explicit_doc_type = normalize_slug(doc_type)

  if explicit_country:
    metadata["country"] = explicit_country

  if explicit_city:
    metadata["city"] = explicit_city

  if explicit_doc_type:
    metadata["doc_type"] = explicit_doc_type

  return metadata
