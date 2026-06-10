"""Intent detection for smart filter suggestions."""

from __future__ import annotations

from dataset_collector.core.enums import FileType, SizeFilter
from dataset_collector.logging.logger import AppLogger


class IntentDetector:
  """Detect query intent and suggest appropriate filters."""

  # Intent keywords by category
  INTENT_PATTERNS = {
    "medical": ["medical", "healthcare", "clinical", "diagnostic", "health", "disease", "patient"],
    "image": ["image", "photo", "picture", "vision", "visual", "imaging", "xray", "mri", "ct"],
    "nlp": ["text", "nlp", "language", "corpus", "document", "transcript", "dialogue"],
    "audio": ["audio", "sound", "speech", "music", "voice", "wav", "mp3"],
    "video": ["video", "movie", "film", "footage", "motion", "clip"],
    "time_series": ["time series", "temporal", "timeseries", "sensor", "measurement"],
    "structured": ["table", "csv", "database", "sql", "spreadsheet", "structured"],
    "graphs": ["graph", "network", "knowledge graph", "relationship", "node", "edge"],
    "3d": ["3d", "point cloud", "mesh", "voxel", "model"],
    "geospatial": ["satellite", "geospatial", "map", "geographic", "gps", "location"],
  }

  # Filter suggestions per intent
  FILTER_SUGGESTIONS = {
    "medical": {
      "file_types": [FileType.CSV, FileType.JSON, FileType.ZIP],
      "min_size": SizeFilter.MIN_1GB,
      "licenses": ["commercial-friendly"],
    },
    "image": {
      "file_types": [FileType.ZIP, FileType.TAR],
      "min_size": SizeFilter.MIN_100MB,
      "licenses": ["any"],
    },
    "nlp": {
      "file_types": [FileType.TXT, FileType.CSV, FileType.JSON],
      "min_size": SizeFilter.ANY,
      "licenses": ["commercial-friendly"],
    },
    "audio": {
      "file_types": [FileType.ZIP, FileType.TAR],
      "min_size": SizeFilter.MIN_100MB,
      "licenses": ["any"],
    },
    "video": {
      "file_types": [FileType.ZIP, FileType.TAR],
      "min_size": SizeFilter.MIN_1GB,
      "licenses": ["any"],
    },
    "time_series": {
      "file_types": [FileType.CSV, FileType.JSON, FileType.PARQUET],
      "min_size": SizeFilter.ANY,
      "licenses": ["any"],
    },
    "structured": {
      "file_types": [FileType.CSV, FileType.JSON, FileType.PARQUET],
      "min_size": SizeFilter.ANY,
      "licenses": ["any"],
    },
    "graphs": {
      "file_types": [FileType.JSON, FileType.CSV],
      "min_size": SizeFilter.ANY,
      "licenses": ["any"],
    },
    "3d": {
      "file_types": [FileType.ZIP],
      "min_size": SizeFilter.MIN_100MB,
      "licenses": ["any"],
    },
    "geospatial": {
      "file_types": [FileType.ZIP, FileType.GeoTIFF],
      "min_size": SizeFilter.MIN_100MB,
      "licenses": ["any"],
    },
  }

  # Source recommendations per intent
  SOURCE_RECOMMENDATIONS = {
    "medical": ["Research Sources", "Government Data", "HuggingFace"],
    "image": ["Kaggle", "HuggingFace", "GitHub"],
    "nlp": ["HuggingFace", "Kaggle", "Research Sources"],
    "audio": ["Kaggle", "HuggingFace", "GitHub"],
    "video": ["Internet Archive", "GitHub"],
    "time_series": ["Kaggle", "GitHub", "Google Dataset Search"],
    "structured": ["Kaggle", "Google Dataset Search"],
    "graphs": ["GitHub", "Research Sources"],
    "3d": ["GitHub", "Kaggle"],
    "geospatial": ["Government Data", "Google Dataset Search"],
  }

  def __init__(self, logger: AppLogger | None = None) -> None:
    self._logger = logger

  def detect_intent(self, query: str) -> dict[str, list[str]]:
    """Detect intents from query and return suggestions.

    Returns:
      {
        "intents": ["medical", "image"],  # Detected intents
        "file_types": ["CSV", "ZIP"],      # Suggested file types
        "size_filter": "MIN_1GB",          # Suggested size filter
        "sources": ["Kaggle", "GitHub"],   # Recommended sources
        "licenses": ["commercial-friendly"]
      }
    """
    query_lower = query.lower()
    detected_intents = []

    # Detect intents
    for intent, keywords in self.INTENT_PATTERNS.items():
      if any(kw in query_lower for kw in keywords):
        detected_intents.append(intent)

    if not detected_intents:
      return {
        "intents": [],
        "file_types": [],
        "size_filter": None,
        "sources": [],
        "licenses": [],
      }

    # Get suggestions for top intent
    primary_intent = detected_intents[0]
    suggestions = self.FILTER_SUGGESTIONS.get(primary_intent, {})

    # Aggregate sources
    sources = []
    for intent in detected_intents:
      sources.extend(self.SOURCE_RECOMMENDATIONS.get(intent, []))
    sources = list(dict.fromkeys(sources))[:5]  # Deduplicate, limit to 5

    return {
      "intents": detected_intents,
      "file_types": [ft.value for ft in suggestions.get("file_types", [])],
      "size_filter": suggestions.get("min_size"),
      "sources": sources,
      "licenses": suggestions.get("licenses", ["any"]),
    }

  def get_intent_tags(self, query: str) -> list[str]:
    """Get human-readable intent tags for display."""
    result = self.detect_intent(query)
    return result.get("intents", [])

  def get_suggested_file_types(self, query: str) -> list[str]:
    """Get suggested file types for query."""
    result = self.detect_intent(query)
    return result.get("file_types", [])

  def get_suggested_sources(self, query: str) -> list[str]:
    """Get recommended sources for query."""
    result = self.detect_intent(query)
    return result.get("sources", [])

  def should_suggest_large_budget(self, query: str) -> bool:
    """Check if query suggests large datasets (>1GB likely)."""
    result = self.detect_intent(query)
    size_filter = result.get("size_filter")
    return size_filter == SizeFilter.MIN_1GB
