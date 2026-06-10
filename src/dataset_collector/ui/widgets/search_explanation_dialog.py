"""Dialog showing score breakdown for search results."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QGroupBox,
)

from dataset_collector.core.models import DatasetResult


class SearchExplanationDialog(QDialog):
  """Show ranking score breakdown with component visualization."""

  def __init__(self, result: DatasetResult, parent=None) -> None:
    super().__init__(parent)
    self._result = result
    self.setWindowTitle(f"Score Breakdown — {result.name}")
    self.setMinimumWidth(500)
    self._build_ui()

  def _build_ui(self) -> None:
    layout = QVBoxLayout(self)

    # Title
    title = QLabel(f"Dataset: {self._result.name}")
    title.setStyleSheet("font-weight: bold; font-size: 12pt;")
    layout.addWidget(title)

    # Ranking components
    components = QGroupBox("Ranking Components")
    form = QFormLayout(components)

    # Helper to create score row
    def add_score_row(
      label: str, score: float, weight: float | None = None
    ) -> None:
      """Add a score row with progress bar."""
      h_layout = QHBoxLayout()

      # Score label
      score_text = f"{int(score * 100)}/100" if score <= 1 else f"{int(score)}/100"
      score_label = QLabel(score_text)
      score_label.setMinimumWidth(50)
      h_layout.addWidget(score_label)

      # Progress bar
      progress = QProgressBar()
      progress.setValue(int(score * 100) if score <= 1 else int(score))
      progress.setMaximum(100)
      h_layout.addWidget(progress)

      # Weight label
      if weight:
        weight_label = QLabel(f"{int(weight * 100)}%")
        weight_label.setMinimumWidth(40)
        h_layout.addWidget(weight_label)

      form.addRow(label, h_layout)

    # Add component rows
    add_score_row("Keyword Match", self._result.relevance_score, 0.40)
    add_score_row("Semantic Similarity", self._result.semantic_score, 0.40)

    # Popularity
    popularity = 0.0
    downloads = self._result.metadata.get("downloads", 0)
    stars = self._result.metadata.get("stars", 0)
    if isinstance(downloads, int):
      popularity += min(downloads / 10000, 1.0)
    if isinstance(stars, int):
      popularity += min(stars / 500, 1.0)
    popularity = min(popularity, 1.0)
    add_score_row("Popularity", popularity, 0.10)

    # Freshness
    freshness = 0.0
    if self._result.last_updated:
      from datetime import datetime, timezone

      days = max(
        (datetime.now(timezone.utc) - self._result.last_updated.replace(tzinfo=timezone.utc)).days,
        0,
      )
      freshness = max(0, 1 - days / 365)
    add_score_row("Freshness", freshness, 0.05)

    # User clicks
    add_score_row("User Clicks", self._result.click_score, 0.05)

    # Separator
    separator = QLabel("─" * 60)
    form.addRow(separator)

    # Final score
    final_label = QLabel("Final Score")
    final_label.setStyleSheet("font-weight: bold;")
    final_score_label = QLabel(f"{self._result.rank_score}/100")
    final_score_label.setStyleSheet("font-weight: bold; font-size: 14pt;")
    form.addRow(final_label, final_score_label)

    # Score label (quality)
    quality = "Highly Relevant"
    if self._result.rank_score >= 80:
      quality = "Excellent"
    elif self._result.rank_score >= 60:
      quality = "Good"
    elif self._result.rank_score >= 40:
      quality = "Fair"
    else:
      quality = "Poor"
    quality_label = QLabel(quality)
    quality_label.setStyleSheet("color: #4F8CFF; font-weight: bold;")
    form.addRow("Quality", quality_label)

    layout.addWidget(components)
    layout.addStretch()
