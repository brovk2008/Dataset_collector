"""Search statistics and logging."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from dataset_collector.core.models import DatasetResult


@dataclass
class SearchStats:
  """Track search pipeline statistics."""

  # Stage counts
  raw_count: int = 0
  deduplicated_count: int = 0
  final_count: int = 0

  # Source breakdown
  source_counts: dict[str, int] = field(default_factory=dict)

  # Removal tracking
  removed_datasets: list[dict] = field(default_factory=list)
  duplicates_removed: int = 0
  invalid_urls_removed: int = 0
  corrupted_removed: int = 0

  # Search mode
  search_mode: str = "balanced"  # balanced or aggressive

  # Timing
  started_at: Optional[datetime] = None
  completed_at: Optional[datetime] = None

  def log_removal(self, dataset: DatasetResult, reason: str):
    """Log a removed dataset."""
    self.removed_datasets.append({
      "id": dataset.id,
      "name": dataset.name,
      "source": dataset.source.value,
      "reason": reason,
      "timestamp": datetime.now().isoformat(),
    })

  def get_summary(self) -> dict:
    """Get summary of search stats."""
    elapsed = None
    if self.started_at and self.completed_at:
      elapsed = (self.completed_at - self.started_at).total_seconds()

    return {
      "raw_results": self.raw_count,
      "deduplicated": self.deduplicated_count,
      "final_results": self.final_count,
      "sources": self.source_counts,
      "removed": {
        "duplicates": self.duplicates_removed,
        "invalid_urls": self.invalid_urls_removed,
        "corrupted": self.corrupted_removed,
        "total_removed": len(self.removed_datasets),
      },
      "search_mode": self.search_mode,
      "elapsed_seconds": elapsed,
      "removal_details": self.removed_datasets,
    }

  def format_display(self) -> str:
    """Format for UI display."""
    lines = [
      f"Raw Results: {self.raw_count}",
      f"Duplicates Removed: {self.duplicates_removed}",
      f"Invalid/Corrupted Removed: {self.invalid_urls_removed + self.corrupted_removed}",
      f"Final Results: {self.final_count}",
      f"Search Mode: {self.search_mode.upper()}",
    ]

    if self.source_counts:
      lines.append("\nBreakdown by Source:")
      for source, count in sorted(self.source_counts.items()):
        lines.append(f"  {source}: {count}")

    return "\n".join(lines)
