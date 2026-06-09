"""Search configuration panel."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from dataset_collector.core.enums import DataSource, FileType, LicenseFilter, SizeFilter
from dataset_collector.core.models import SearchFilters, SearchRequest


class SearchPanel(QWidget):
  """Query input, source selection, and filter controls."""

  def __init__(self, parent: QWidget | None = None) -> None:
    super().__init__(parent)
    self._build_ui()

  def _build_ui(self) -> None:
    outer = QVBoxLayout(self)
    outer.setContentsMargins(0, 0, 0, 0)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setFrameShape(QScrollArea.Shape.NoFrame)

    content = QWidget()
    layout = QVBoxLayout(content)
    layout.setContentsMargins(4, 4, 8, 4)
    layout.setSpacing(10)

    # Query — multi-line so long queries are fully visible
    query_group = QGroupBox("Dataset Query")
    query_layout = QVBoxLayout(query_group)
    query_layout.setContentsMargins(10, 14, 10, 10)
    self._query_input = QTextEdit()
    self._query_input.setPlaceholderText(
      "Enter your search topic...\n\n"
      "Examples:\n"
      "• medical image dataset\n"
      "• FIR crime data India\n"
      "• sticker pack icons"
    )
    self._query_input.setMinimumHeight(90)
    self._query_input.setMaximumHeight(120)
    query_layout.addWidget(self._query_input)
    layout.addWidget(query_group)

    # Sources
    sources_group = QGroupBox("Search Sources")
    sources_layout = QVBoxLayout(sources_group)
    sources_layout.setSpacing(4)
    self._source_checks: dict[DataSource, QCheckBox] = {}
    for source in DataSource:
      cb = QCheckBox(source.value)
      cb.setChecked(True)
      self._source_checks[source] = cb
      sources_layout.addWidget(cb)
    self._search_all = QCheckBox("Search All Sources")
    self._search_all.setChecked(True)
    self._search_all.toggled.connect(self._on_search_all_toggled)
    sources_layout.addWidget(self._search_all)
    layout.addWidget(sources_group)

    # Filters
    filters_group = QGroupBox("Filters")
    filters_layout = QGridLayout(filters_group)
    filters_layout.setHorizontalSpacing(10)
    filters_layout.setVerticalSpacing(8)
    filters_layout.setColumnStretch(1, 1)

    filters_layout.addWidget(QLabel("File Types:"), 0, 0, Qt.AlignmentFlag.AlignTop)
    file_widget = QWidget()
    file_grid = QGridLayout(file_widget)
    file_grid.setContentsMargins(0, 0, 0, 0)
    file_grid.setHorizontalSpacing(8)
    file_grid.setVerticalSpacing(4)
    self._file_type_checks: dict[FileType, QCheckBox] = {}
    file_types = [ft for ft in FileType if ft != FileType.ANY]
    for i, ft in enumerate(file_types):
      cb = QCheckBox(ft.value)
      self._file_type_checks[ft] = cb
      file_grid.addWidget(cb, i // 2, i % 2)
    self._any_type = QCheckBox("Any")
    self._any_type.setChecked(True)
    self._any_type.toggled.connect(self._on_any_type_toggled)
    file_grid.addWidget(self._any_type, (len(file_types) + 1) // 2, 0, 1, 2)
    filters_layout.addWidget(file_widget, 0, 1)

    filters_layout.addWidget(QLabel("Custom Type:"), 1, 0, Qt.AlignmentFlag.AlignTop)
    custom_col = QVBoxLayout()
    self._custom_type_input = QLineEdit()
    self._custom_type_input.setPlaceholderText("e.g. stickers, icons pack, FIR records")
    custom_col.addWidget(self._custom_type_input)
    custom_hint = QLabel("Comma-separated — matches name, description, or extension")
    custom_hint.setObjectName("secondaryLabel")
    custom_hint.setWordWrap(True)
    custom_col.addWidget(custom_hint)
    filters_layout.addLayout(custom_col, 1, 1)

    filters_layout.addWidget(QLabel("Country:"), 2, 0)
    self._country_combo = QComboBox()
    self._country_combo.addItems([
      "Worldwide", "India", "United States", "United Kingdom", "Australia", "Canada",
    ])
    filters_layout.addWidget(self._country_combo, 2, 1)

    filters_layout.addWidget(QLabel("Total Budget:"), 3, 0)
    budget_col = QVBoxLayout()
    budget_row = QHBoxLayout()
    self._size_combo = QComboBox()
    self._size_combo.addItems([s.value for s in SizeFilter])
    budget_row.addWidget(self._size_combo)
    self._max_size_spin = QSpinBox()
    self._max_size_spin.setRange(1, 10000)
    self._max_size_spin.setValue(500)
    self._max_size_spin.setEnabled(False)
    budget_row.addWidget(self._max_size_spin)
    self._size_unit_combo = QComboBox()
    self._size_unit_combo.addItems(["MB", "GB"])
    self._size_unit_combo.setEnabled(False)
    self._size_unit_combo.setFixedWidth(56)
    budget_row.addWidget(self._size_unit_combo)
    budget_col.addLayout(budget_row)
    self._budget_hint = QLabel("Auto-selects best datasets within budget after scan")
    self._budget_hint.setObjectName("secondaryLabel")
    self._budget_hint.setWordWrap(True)
    self._budget_hint.setVisible(False)
    budget_col.addWidget(self._budget_hint)
    self._size_combo.currentTextChanged.connect(self._on_size_filter_changed)
    filters_layout.addLayout(budget_col, 3, 1)

    filters_layout.addWidget(QLabel("License:"), 4, 0)
    self._license_combo = QComboBox()
    self._license_combo.addItems([lf.value for lf in LicenseFilter])
    filters_layout.addWidget(self._license_combo, 4, 1)

    layout.addWidget(filters_group)

    btn_layout = QHBoxLayout()
    btn_layout.addStretch()
    self._scan_btn = QPushButton("Start Scan")
    self._scan_btn.setObjectName("primaryButton")
    self._scan_btn.setMinimumWidth(140)
    self._scan_btn.setMinimumHeight(32)
    btn_layout.addWidget(self._scan_btn)
    layout.addLayout(btn_layout)

    layout.addStretch()
    scroll.setWidget(content)
    outer.addWidget(scroll)

  def _on_search_all_toggled(self, checked: bool) -> None:
    for cb in self._source_checks.values():
      cb.setChecked(checked)

  def _on_any_type_toggled(self, checked: bool) -> None:
    if checked:
      for cb in self._file_type_checks.values():
        cb.setChecked(False)

  def _on_size_filter_changed(self, text: str) -> None:
    is_budget = text == SizeFilter.MAX_SIZE.value
    self._max_size_spin.setEnabled(is_budget)
    self._size_unit_combo.setEnabled(is_budget)
    self._budget_hint.setVisible(is_budget)

  def _parse_custom_types(self) -> list[str]:
    raw = self._custom_type_input.text().strip()
    if not raw:
      return []
    return [t.strip() for t in raw.split(",") if t.strip()]

  def get_search_request(self) -> SearchRequest | None:
    query = self._query_input.toPlainText().strip()
    if not query:
      return None

    sources = [s for s, cb in self._source_checks.items() if cb.isChecked()]
    if not sources:
      return None

    custom_types = self._parse_custom_types()
    if self._any_type.isChecked() and not custom_types:
      file_types = [FileType.ANY]
    else:
      file_types = [ft for ft, cb in self._file_type_checks.items() if cb.isChecked()]
      if not file_types and not custom_types:
        file_types = [FileType.ANY]

    size_filter = SizeFilter(self._size_combo.currentText())
    max_size = None
    if size_filter == SizeFilter.MAX_SIZE:
      multiplier = 1024 * 1024 if self._size_unit_combo.currentText() == "MB" else 1024 * 1024 * 1024
      max_size = self._max_size_spin.value() * multiplier

    filters = SearchFilters(
      file_types=file_types,
      custom_types=custom_types,
      country=self._country_combo.currentText(),
      size_filter=size_filter,
      max_size_bytes=max_size,
      license_filter=LicenseFilter(self._license_combo.currentText()),
    )
    return SearchRequest(query=query, sources=sources, filters=filters)

  def get_budget_bytes(self) -> int | None:
    if self._size_combo.currentText() == SizeFilter.MAX_SIZE.value:
      multiplier = 1024 * 1024 if self._size_unit_combo.currentText() == "MB" else 1024 * 1024 * 1024
      return self._max_size_spin.value() * multiplier
    return None

  @property
  def scan_button(self) -> QPushButton:
    return self._scan_btn

  def set_scanning(self, scanning: bool) -> None:
    self._scan_btn.setEnabled(not scanning)
    self._query_input.setEnabled(not scanning)
