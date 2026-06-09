"""Dataset library management panel."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from dataset_collector.core.models import LibraryEntry
from dataset_collector.storage.storage_manager import StorageManager


class LibraryPanel(QWidget):
  """Downloaded dataset library with disk usage tracking."""

  analyze_requested = Signal(str, str)
  refresh_requested = Signal()

  def __init__(self, storage: StorageManager, parent: QWidget | None = None) -> None:
    super().__init__(parent)
    self._storage = storage
    self._build_ui()
    self.refresh()

  def _build_ui(self) -> None:
    layout = QVBoxLayout(self)

    # Disk usage
    usage_layout = QHBoxLayout()
    self._usage_label = QLabel("Disk Usage: —")
    self._usage_label.setObjectName("statsLabel")
    self._count_label = QLabel("Datasets: 0")
    self._count_label.setObjectName("secondaryLabel")
    usage_layout.addWidget(self._usage_label)
    usage_layout.addStretch()
    usage_layout.addWidget(self._count_label)
    layout.addLayout(usage_layout)

    # Table
    self._table = QTableWidget()
    self._table.setColumnCount(6)
    self._table.setHorizontalHeaderLabels([
      "Name", "Source", "Size", "Files", "Downloaded", "Path",
    ])
    self._table.setAlternatingRowColors(True)
    self._table.horizontalHeader().setStretchLastSection(True)
    self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
    self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    layout.addWidget(self._table)

    # Buttons
    btn_layout = QHBoxLayout()
    self._refresh_btn = QPushButton("Refresh")
    self._refresh_btn.clicked.connect(self.refresh)
    btn_layout.addWidget(self._refresh_btn)

    self._analyze_btn = QPushButton("Analyze Selected")
    self._analyze_btn.clicked.connect(self._on_analyze)
    btn_layout.addWidget(self._analyze_btn)

    self._export_btn = QPushButton("Export Metadata")
    self._export_btn.clicked.connect(self._on_export)
    btn_layout.addWidget(self._export_btn)

    self._delete_btn = QPushButton("Delete Selected")
    self._delete_btn.setObjectName("dangerButton")
    self._delete_btn.clicked.connect(self._on_delete)
    btn_layout.addWidget(self._delete_btn)

    btn_layout.addStretch()
    layout.addLayout(btn_layout)

    self._entries: list[LibraryEntry] = []

  def refresh(self) -> None:
    self._entries = self._storage.get_all()
    usage = self._storage.get_disk_usage()
    self._usage_label.setText(f"Disk Usage: {usage['total_display']}")
    self._count_label.setText(f"Datasets: {usage['total_datasets']}")

    self._table.setRowCount(len(self._entries))
    for row, entry in enumerate(self._entries):
      self._table.setItem(row, 0, QTableWidgetItem(entry.name))
      self._table.setItem(row, 1, QTableWidgetItem(entry.source))
      self._table.setItem(row, 2, QTableWidgetItem(_format_bytes(entry.size_bytes)))
      self._table.setItem(row, 3, QTableWidgetItem(str(entry.file_count)))
      self._table.setItem(
        row, 4, QTableWidgetItem(entry.downloaded_at.strftime("%Y-%m-%d %H:%M"))
      )
      self._table.setItem(row, 5, QTableWidgetItem(entry.local_path))

  def add_entry(self, name: str, source: str, local_path: str) -> None:
    self._storage.add_dataset(name, source, local_path)
    self.refresh()

  def _get_selected_entry(self) -> LibraryEntry | None:
    rows = self._table.selectionModel().selectedRows()
    if not rows:
      return None
    idx = rows[0].row()
    if idx < len(self._entries):
      return self._entries[idx]
    return None

  def _on_analyze(self) -> None:
    entry = self._get_selected_entry()
    if entry:
      self.analyze_requested.emit(entry.local_path, entry.name)

  def _on_export(self) -> None:
    from PySide6.QtWidgets import QFileDialog

    path, _ = QFileDialog.getSaveFileName(
      self, "Export Metadata", "library_metadata.json", "JSON (*.json)"
    )
    if path:
      self._storage.export_metadata(path)
      QMessageBox.information(self, "Export", f"Metadata exported to:\n{path}")

  def _on_delete(self) -> None:
    entry = self._get_selected_entry()
    if not entry:
      return
    reply = QMessageBox.question(
      self,
      "Delete Dataset",
      f"Delete '{entry.name}' and remove files from disk?",
      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
    )
    if reply == QMessageBox.StandardButton.Yes:
      self._storage.delete_dataset(entry.id, remove_files=True)
      self.refresh()


def _format_bytes(size: int) -> str:
  for unit in ("B", "KB", "MB", "GB", "TB"):
    if size < 1024:
      return f"{size:.1f} {unit}" if unit != "B" else f"{size} B"
    size /= 1024
  return f"{size:.1f} PB"
