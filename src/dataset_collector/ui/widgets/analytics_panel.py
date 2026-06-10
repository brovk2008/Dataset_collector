"""Search analytics display panel."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
  from dataset_collector.databrain import DatasetBrain


class AnalyticsPanel(QWidget):
  """Display search analytics: top searches, clicked datasets, etc."""

  def __init__(self, databrain: DatasetBrain | None = None, parent=None) -> None:
    super().__init__(parent)
    self._databrain = databrain
    self._build_ui()
    if databrain:
      self.refresh()

  def _build_ui(self) -> None:
    layout = QVBoxLayout(self)

    # Tabs for different analytics
    tabs = QTabWidget()

    # Tab 1: Top Searches
    self._searches_table = QTableWidget()
    self._searches_table.setColumnCount(2)
    self._searches_table.setHorizontalHeaderLabels(["Query", "Count"])
    self._searches_table.horizontalHeader().setStretchLastSection(False)
    self._searches_table.setColumnWidth(0, 300)
    tabs.addTab(self._searches_table, "Top Searches (30 days)")

    # Tab 2: Top Clicked Datasets
    self._clicked_table = QTableWidget()
    self._clicked_table.setColumnCount(2)
    self._clicked_table.setHorizontalHeaderLabels(["Dataset", "Clicks"])
    self._clicked_table.horizontalHeader().setStretchLastSection(True)
    tabs.addTab(self._clicked_table, "Top Clicked Datasets")

    # Tab 3: Search Effectiveness
    self._effectiveness_widget = QWidget()
    effectiveness_layout = QVBoxLayout(self._effectiveness_widget)
    self._success_rate_label = QLabel("Search success rate: —%")
    self._success_rate_label.setObjectName("statsLabel")
    effectiveness_layout.addWidget(self._success_rate_label)
    effectiveness_layout.addStretch()
    tabs.addTab(self._effectiveness_widget, "Effectiveness")

    # Tab 4: Model Info
    self._model_widget = QWidget()
    model_layout = QVBoxLayout(self._model_widget)
    self._model_label = QLabel("")
    self._model_label.setObjectName("secondaryLabel")
    model_layout.addWidget(self._model_label)
    model_layout.addStretch()
    tabs.addTab(self._model_widget, "Model")

    layout.addWidget(tabs)

    # Refresh button
    refresh_btn = QPushButton("Refresh Analytics")
    refresh_btn.clicked.connect(self.refresh)
    layout.addWidget(refresh_btn)

  def set_databrain(self, databrain: DatasetBrain) -> None:
    """Set DatasetBrain instance."""
    self._databrain = databrain
    self.refresh()

  def refresh(self) -> None:
    """Reload all analytics data."""
    if not self._databrain:
      return

    try:
      analytics = self._databrain.analytics

      # Top searches
      top_searches = analytics.get_top_searches(limit=20, days_back=30)
      self._searches_table.setRowCount(len(top_searches))
      for row, (query, count) in enumerate(top_searches):
        self._searches_table.setItem(row, 0, QTableWidgetItem(query))
        self._searches_table.setItem(row, 1, QTableWidgetItem(str(count)))

      # Top clicked datasets
      top_clicked = analytics.get_top_clicked_datasets(limit=20, days_back=30)
      self._clicked_table.setRowCount(len(top_clicked))
      for row, (dataset_id, count) in enumerate(top_clicked):
        self._clicked_table.setItem(row, 0, QTableWidgetItem(dataset_id[:50]))
        self._clicked_table.setItem(row, 1, QTableWidgetItem(str(count)))

      # Success rate
      success_rate = analytics.get_search_success_rate(days_back=30)
      rate_pct = int(success_rate * 100)
      self._success_rate_label.setText(
        f"Searches with clicks: {rate_pct}% (of last 30 days)"
      )

      # Model stats
      model_stats = analytics.get_model_stats()
      self._model_label.setText(
        f"Embeddings cached: {model_stats.get('embeddings_cached', 0)}\n"
        f"Cache size: {model_stats.get('cache_size_mb', 0):.1f} MB"
      )
    except Exception as e:
      self._searches_table.setRowCount(0)
      self._clicked_table.setRowCount(0)
      self._success_rate_label.setText(f"Error: {e}")
