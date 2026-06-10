"""Side-by-side dataset comparison dialog."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QHeaderView,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from dataset_collector.core.models import DatasetResult


class ComparisonDialog(QDialog):
  """Compare multiple datasets side-by-side."""

  FIELDS = ["Name", "Rank", "Quality", "Source(s)", "Size", "Files", "License", "Updated", "URL"]

  def __init__(self, datasets: list[DatasetResult], parent=None) -> None:
    super().__init__(parent)
    self.setWindowTitle("Compare Datasets")
    self.setMinimumSize(700, 300)
    self._datasets = datasets
    self._build_ui()

  def _build_ui(self) -> None:
    layout = QVBoxLayout(self)
    table = QTableWidget()
    table.setColumnCount(len(self._datasets))
    table.setRowCount(len(self.FIELDS))
    table.setVerticalHeaderLabels(self.FIELDS)
    table.setHorizontalHeaderLabels([f"#{i+1}" for i in range(len(self._datasets))])
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

    for col, ds in enumerate(self._datasets):
      sources = ", ".join(ds.available_sources) if ds.available_sources else ds.source.value
      updated = ds.last_updated.strftime("%Y-%m-%d") if ds.last_updated else "—"
      values = [
        ds.name,
        f"{ds.rank_score}/100",
        f"{ds.quality_score}/10",
        sources,
        ds.size_display,
        str(ds.file_count) if ds.file_count else "—",
        ds.license_info,
        updated,
        ds.url,
      ]
      for row, val in enumerate(values):
        table.setItem(row, col, QTableWidgetItem(val))

    layout.addWidget(table)
    close_btn = QPushButton("Close")
    close_btn.clicked.connect(self.accept)
    layout.addWidget(close_btn)
