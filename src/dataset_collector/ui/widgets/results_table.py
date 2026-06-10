"""Search results table widget with pagination."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from dataset_collector.core.models import DatasetResult
from dataset_collector.search.relevance import suggest_within_budget
from dataset_collector.ui.widgets.search_explanation_dialog import SearchExplanationDialog

DATASET_ID_ROLE = Qt.ItemDataRole.UserRole
PAGE_SIZE = 25


class ResultsTable(QWidget):
  """Sortable, filterable, paginated results table with multi-select."""

  selection_changed = Signal()
  dataset_activated = Signal(object)

  COLUMNS = ["", "Dataset Name", "Rank", "Health", "Quality", "Sources", "Size", "License", "Updated"]

  def __init__(self, parent: QWidget | None = None) -> None:
    super().__init__(parent)
    self._all_results: list[DatasetResult] = []
    self._filtered_results: list[DatasetResult] = []
    self._id_map: dict[str, DatasetResult] = {}
    self._checked_ids: set[str] = set()
    self._current_page = 0
    self._filter_text = ""
    self._build_ui()

  def _build_ui(self) -> None:
    layout = QVBoxLayout(self)
    layout.setContentsMargins(0, 0, 0, 0)

    stats_layout = QHBoxLayout()
    self._total_label = QLabel("Total Datasets: 0")
    self._total_label.setObjectName("statsLabel")
    self._size_label = QLabel("Estimated Size: 0 B")
    self._size_label.setObjectName("secondaryLabel")
    self._files_label = QLabel("Selected: 0")
    self._files_label.setObjectName("secondaryLabel")
    self._suggest_label = QLabel("")
    self._suggest_label.setObjectName("secondaryLabel")
    stats_layout.addWidget(self._total_label)
    stats_layout.addStretch()
    stats_layout.addWidget(self._suggest_label)
    stats_layout.addWidget(self._size_label)
    stats_layout.addWidget(self._files_label)
    layout.addLayout(stats_layout)

    controls = QHBoxLayout()
    self._filter_input = QLineEdit()
    self._filter_input.setPlaceholderText("Filter results...")
    self._filter_input.textChanged.connect(self._on_filter_changed)
    controls.addWidget(self._filter_input)

    self._select_all_btn = QPushButton("Select All")
    self._select_all_btn.clicked.connect(self.select_all_on_page)
    controls.addWidget(self._select_all_btn)

    self._deselect_all_btn = QPushButton("Deselect All")
    self._deselect_all_btn.clicked.connect(self.deselect_all)
    controls.addWidget(self._deselect_all_btn)

    self._details_btn = QPushButton("View Details")
    self._details_btn.clicked.connect(self._open_selected_details)
    controls.addWidget(self._details_btn)

    self._score_btn = QPushButton("Score Breakdown")
    self._score_btn.clicked.connect(self._show_score_breakdown)
    controls.addWidget(self._score_btn)

    self._compare_btn = QPushButton("Compare Selected")
    self._compare_btn.clicked.connect(self._compare_selected)
    controls.addWidget(self._compare_btn)
    layout.addLayout(controls)

    self._table = QTableWidget()
    self._table.setColumnCount(len(self.COLUMNS))
    self._table.setHorizontalHeaderLabels(self.COLUMNS)
    self._table.setAlternatingRowColors(True)
    self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    self._table.setSortingEnabled(False)
    self._table.horizontalHeader().setStretchLastSection(True)
    self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
    self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
    self._table.setColumnWidth(0, 30)
    self._table.setColumnWidth(3, 72)
    self._table.itemChanged.connect(self._on_item_changed)
    self._table.cellDoubleClicked.connect(self._on_double_click)
    layout.addWidget(self._table)

    # Pagination bar
    page_layout = QHBoxLayout()
    self._prev_btn = QPushButton("◀ Prev")
    self._prev_btn.clicked.connect(self._prev_page)
    self._prev_btn.setEnabled(False)
    page_layout.addWidget(self._prev_btn)

    self._page_label = QLabel("Page 1 of 1")
    self._page_label.setObjectName("secondaryLabel")
    self._page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    page_layout.addWidget(self._page_label, stretch=1)

    self._next_btn = QPushButton("Next ▶")
    self._next_btn.clicked.connect(self._next_page)
    self._next_btn.setEnabled(False)
    page_layout.addWidget(self._next_btn)
    layout.addLayout(page_layout)

  def set_results(self, results: list[DatasetResult]) -> None:
    self._all_results = results
    self._id_map = {r.id: r for r in results}
    self._checked_ids.clear()
    self._current_page = 0
    self._filter_text = self._filter_input.text().strip().lower()
    self._apply_filter_internal()
    self._update_stats()

  def apply_budget_suggestions(self, budget_bytes: int) -> int:
    self._checked_ids.clear()
    suggested = suggest_within_budget(self._all_results, budget_bytes)
    self._checked_ids = {r.id for r in suggested}
    self._render_page()

    total_size = sum(r.estimated_size_bytes or 50 * 1024 * 1024 for r in suggested)
    self._suggest_label.setText(
      f"Suggested: {len(suggested)} datasets ({_format_bytes(total_size)})"
    )
    self._update_selected_stats()
    self.selection_changed.emit()
    return len(suggested)

  def _on_filter_changed(self, text: str) -> None:
    self._filter_text = text.strip().lower()
    self._current_page = 0
    self._apply_filter_internal()

  def _apply_filter_internal(self) -> None:
    if self._filter_text:
      self._filtered_results = [
        r for r in self._all_results
        if self._filter_text in r.name.lower()
        or self._filter_text in r.description.lower()
        or self._filter_text in r.source.value.lower()
      ]
    else:
      self._filtered_results = list(self._all_results)
    self._render_page()

  def _total_pages(self) -> int:
    if not self._filtered_results:
      return 1
    return max(1, (len(self._filtered_results) + PAGE_SIZE - 1) // PAGE_SIZE)

  def _page_slice(self) -> list[DatasetResult]:
    start = self._current_page * PAGE_SIZE
    return self._filtered_results[start : start + PAGE_SIZE]

  def _render_page(self) -> None:
    page_results = self._page_slice()
    self._table.blockSignals(True)
    self._table.setRowCount(len(page_results))

    for row, ds in enumerate(page_results):
      check = QTableWidgetItem()
      check.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
      checked = ds.id in self._checked_ids
      check.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
      check.setData(DATASET_ID_ROLE, ds.id)
      self._table.setItem(row, 0, check)

      name_item = QTableWidgetItem(ds.name)
      name_item.setData(DATASET_ID_ROLE, ds.id)
      desc = (ds.description or "")[:200]
      name_item.setToolTip(f"{ds.name}\n\n{desc}\n\nDouble-click for details")
      self._table.setItem(row, 1, name_item)
      self._table.setItem(row, 2, QTableWidgetItem(f"{ds.rank_score}/100"))

      health_item = QTableWidgetItem(f"{ds.health_score}/100")
      health_label = self._get_health_label(ds.health_score)
      health_item.setToolTip(f"Dataset health: {health_label}")
      self._table.setItem(row, 3, health_item)

      self._table.setItem(row, 4, QTableWidgetItem(f"{ds.quality_score}/10"))
      sources = ", ".join(ds.available_sources) if ds.available_sources else ds.source.value
      self._table.setItem(row, 5, QTableWidgetItem(sources))
      self._table.setItem(row, 6, QTableWidgetItem(ds.size_display))
      self._table.setItem(row, 7, QTableWidgetItem(ds.license_info))
      updated = ds.last_updated.strftime("%Y-%m-%d") if ds.last_updated else "—"
      self._table.setItem(row, 8, QTableWidgetItem(updated))

    self._table.blockSignals(False)

    total_pages = self._total_pages()
    self._page_label.setText(
      f"Page {self._current_page + 1} of {total_pages}  "
      f"({len(self._filtered_results)} datasets, {PAGE_SIZE} per page)"
    )
    self._prev_btn.setEnabled(self._current_page > 0)
    self._next_btn.setEnabled(self._current_page < total_pages - 1)

  def _prev_page(self) -> None:
    if self._current_page > 0:
      self._current_page -= 1
      self._render_page()

  def _next_page(self) -> None:
    if self._current_page < self._total_pages() - 1:
      self._current_page += 1
      self._render_page()

  def _on_item_changed(self, item: QTableWidgetItem) -> None:
    if item.column() == 0:
      ds_id = item.data(DATASET_ID_ROLE)
      if item.checkState() == Qt.CheckState.Checked:
        self._checked_ids.add(ds_id)
      else:
        self._checked_ids.discard(ds_id)
      self._update_selected_stats()
      self.selection_changed.emit()

  def _on_double_click(self, row: int, _col: int) -> None:
    ds = self._dataset_at_row(row)
    if ds:
      self.dataset_activated.emit(ds)

  def _compare_selected(self) -> None:
    selected = self.get_selected()
    if len(selected) < 2:
      from PySide6.QtWidgets import QMessageBox
      QMessageBox.information(self, "Compare", "Select at least 2 datasets to compare.")
      return
    from dataset_collector.ui.widgets.comparison_dialog import ComparisonDialog
    ComparisonDialog(selected[:5], self).exec()

  def _open_selected_details(self) -> None:
    rows = self._table.selectionModel().selectedRows()
    if rows:
      ds = self._dataset_at_row(rows[0].row())
      if ds:
        self.dataset_activated.emit(ds)

  def _dataset_at_row(self, row: int) -> DatasetResult | None:
    item = self._table.item(row, 0) or self._table.item(row, 1)
    if item:
      return self._id_map.get(item.data(DATASET_ID_ROLE))
    return None

  def _update_stats(self) -> None:
    total_size = sum(r.estimated_size_bytes or 0 for r in self._all_results)
    self._total_label.setText(f"Total Datasets: {len(self._all_results)}")
    self._size_label.setText(f"Estimated Size: {_format_bytes(total_size)}")
    self._update_selected_stats()

  def _update_selected_stats(self) -> None:
    selected = self.get_selected()
    sel_size = sum(r.estimated_size_bytes or 0 for r in selected)
    self._files_label.setText(f"Selected: {len(selected)} ({_format_bytes(sel_size)})")

  def get_selected(self) -> list[DatasetResult]:
    return [self._id_map[ds_id] for ds_id in self._checked_ids if ds_id in self._id_map]

  def select_dataset(self, dataset_id: str) -> None:
    self._checked_ids.add(dataset_id)
    self._render_page()
    self._update_selected_stats()
    self.selection_changed.emit()

  def select_all_on_page(self) -> None:
    for ds in self._page_slice():
      self._checked_ids.add(ds.id)
    self._render_page()
    self._update_selected_stats()
    self.selection_changed.emit()

  def deselect_all(self) -> None:
    self._checked_ids.clear()
    self._suggest_label.setText("")
    self._render_page()
    self._update_selected_stats()
    self.selection_changed.emit()

  def selected_count(self) -> int:
    return len(self._checked_ids)

  def _get_health_label(self, score: int) -> str:
    if score >= 80:
      return "Excellent"
    elif score >= 60:
      return "Good"
    elif score >= 40:
      return "Fair"
    else:
      return "Poor"

  def _show_score_breakdown(self) -> None:
    rows = self._table.selectionModel().selectedRows()
    if not rows:
      from PySide6.QtWidgets import QMessageBox
      QMessageBox.information(self, "Score Breakdown", "Select a dataset to view score breakdown.")
      return
    ds = self._dataset_at_row(rows[0].row())
    if ds:
      SearchExplanationDialog(ds, self).exec()


def _format_bytes(size: int) -> str:
  for unit in ("B", "KB", "MB", "GB", "TB"):
    if size < 1024:
      return f"{size:.1f} {unit}" if unit != "B" else f"{size} B"
    size /= 1024
  return f"{size:.1f} PB"
