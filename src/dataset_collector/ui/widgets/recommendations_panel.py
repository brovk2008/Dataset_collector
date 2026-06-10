"""Personalized dataset recommendations panel."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
  from dataset_collector.databrain import DatasetBrain


class RecommendationsPanel(QWidget):
  """Display personalized dataset recommendations."""

  def __init__(self, databrain: DatasetBrain | None = None, parent=None) -> None:
    super().__init__(parent)
    self._databrain = databrain
    self._build_ui()
    if databrain:
      self.refresh()

  def _build_ui(self) -> None:
    layout = QVBoxLayout(self)

    self._title = QLabel("Personalized Recommendations")
    self._title.setObjectName("statsLabel")
    layout.addWidget(self._title)

    self._intro = QLabel(
      "Based on your search history and downloads, here are suggested datasets:"
    )
    self._intro.setObjectName("secondaryLabel")
    self._intro.setWordWrap(True)
    layout.addWidget(self._intro)

    # Recommendations table
    self._rec_table = QTableWidget()
    self._rec_table.setColumnCount(3)
    self._rec_table.setHorizontalHeaderLabels(["Dataset", "Reason", "Score"])
    self._rec_table.horizontalHeader().setStretchLastSection(False)
    self._rec_table.setColumnWidth(0, 250)
    self._rec_table.setColumnWidth(1, 200)
    layout.addWidget(self._rec_table)

    # Refresh button
    refresh_btn = QPushButton("Refresh Recommendations")
    refresh_btn.clicked.connect(self.refresh)
    layout.addWidget(refresh_btn)

  def set_databrain(self, databrain: DatasetBrain) -> None:
    """Set DatasetBrain instance."""
    self._databrain = databrain
    self.refresh()

  def refresh(self) -> None:
    """Reload all recommendations."""
    if not self._databrain or not hasattr(self._databrain, "recommendations"):
      self._rec_table.setRowCount(0)
      return

    try:
      recommendations = self._databrain.recommendations.get_recommendations(limit=10)

      self._rec_table.setRowCount(len(recommendations))
      for row, rec in enumerate(recommendations):
        dataset_item = QTableWidgetItem(rec.dataset.name[:50])
        reason_item = QTableWidgetItem(rec.reason)
        score_item = QTableWidgetItem(f"{rec.score:.2f}")

        self._rec_table.setItem(row, 0, dataset_item)
        self._rec_table.setItem(row, 1, reason_item)
        self._rec_table.setItem(row, 2, score_item)

      if not recommendations:
        self._rec_table.setRowCount(1)
        self._rec_table.setItem(
          0, 0, QTableWidgetItem("No recommendations yet. Search and download to get personalized suggestions.")
        )
    except Exception:
      self._rec_table.setRowCount(1)
      self._rec_table.setItem(0, 0, QTableWidgetItem("Error loading recommendations."))
