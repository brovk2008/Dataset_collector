"""Dataset library management panel."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
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
  """Downloaded dataset library with search, sort, and folder access."""

  analyze_requested = Signal(str, str)

  def __init__(self, storage: StorageManager, parent: QWidget | None = None) -> None:
    super().__init__(parent)
    self._storage = storage
    self._entries: list[LibraryEntry] = []
    self._build_ui()
    self.refresh()

  def _build_ui(self) -> None:
    layout = QVBoxLayout(self)

    usage_layout = QHBoxLayout()
    self._usage_label = QLabel("Disk Usage: —")
    self._usage_label.setObjectName("statsLabel")
    self._count_label = QLabel("Datasets: 0")
    self._count_label.setObjectName("secondaryLabel")
    usage_layout.addWidget(self._usage_label)
    usage_layout.addStretch()
    usage_layout.addWidget(self._count_label)
    layout.addLayout(usage_layout)

    filter_row = QHBoxLayout()
    self._search_input = QLineEdit()
    self._search_input.setPlaceholderText("Search local datasets...")
    self._search_input.textChanged.connect(self._apply_filter)
    filter_row.addWidget(self._search_input)
    self._sort_combo = QComboBox()
    self._sort_combo.addItems(["Sort by Date", "Sort by Name", "Sort by Size"])
    self._sort_combo.currentIndexChanged.connect(self._apply_filter)
    filter_row.addWidget(self._sort_combo)
    layout.addLayout(filter_row)

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

    btn_layout = QHBoxLayout()
    for text, slot in [
      ("Refresh", self.refresh),
      ("Open Folder", self._open_folder),
      ("Analyze", self._on_analyze),
      ("Export Metadata", self._on_export),
    ]:
      btn = QPushButton(text)
      btn.clicked.connect(slot)
      btn_layout.addWidget(btn)
    self._delete_btn = QPushButton("Delete Selected")
    self._delete_btn.setObjectName("dangerButton")
    self._delete_btn.clicked.connect(self._on_delete)
    btn_layout.addWidget(self._delete_btn)
    btn_layout.addStretch()
    layout.addLayout(btn_layout)

  def refresh(self) -> None:
    self._entries = self._storage.get_all()
    self._apply_filter()

  def _apply_filter(self) -> None:
    text = self._search_input.text().lower()
    entries = [
      e for e in self._entries
      if not text or text in e.name.lower() or text in e.source.lower()
    ]
    sort_mode = self._sort_combo.currentText()
    if sort_mode == "Sort by Name":
      entries.sort(key=lambda e: e.name.lower())
    elif sort_mode == "Sort by Size":
      entries.sort(key=lambda e: e.size_bytes, reverse=True)
    else:
      entries.sort(key=lambda e: e.downloaded_at, reverse=True)

    usage = self._storage.get_disk_usage()
    self._usage_label.setText(f"Disk Usage: {usage['total_display']}")
    self._count_label.setText(f"Datasets: {usage['total_datasets']}")

    self._displayed = entries
    self._table.setRowCount(len(entries))
    for row, entry in enumerate(entries):
      self._table.setItem(row, 0, QTableWidgetItem(entry.name))
      self._table.setItem(row, 1, QTableWidgetItem(entry.source))
      self._table.setItem(row, 2, QTableWidgetItem(_format_bytes(entry.size_bytes)))
      self._table.setItem(row, 3, QTableWidgetItem(str(entry.file_count)))
      self._table.setItem(row, 4, QTableWidgetItem(entry.downloaded_at.strftime("%Y-%m-%d %H:%M")))
      self._table.setItem(row, 5, QTableWidgetItem(entry.local_path))

  def add_entry(self, name: str, source: str, local_path: str) -> None:
    self._storage.add_dataset(name, source, local_path)
    self.refresh()

  def _get_selected_entry(self) -> LibraryEntry | None:
    rows = self._table.selectionModel().selectedRows()
    if not rows:
      return None
    idx = rows[0].row()
    displayed = getattr(self, "_displayed", self._entries)
    if idx < len(displayed):
      return displayed[idx]
    return None

  def _open_folder(self) -> None:
    entry = self._get_selected_entry()
    if not entry:
      QMessageBox.information(self, "Open Folder", "Select a dataset first.")
      return
    path = Path(entry.local_path)
    folder = path if path.is_dir() else path.parent
    if not folder.exists():
      QMessageBox.warning(self, "Open Folder", "Folder no longer exists.")
      return
    if sys.platform == "win32":
      os.startfile(str(folder))
    elif sys.platform == "darwin":
      subprocess.run(["open", str(folder)], check=False)
    else:
      subprocess.run(["xdg-open", str(folder)], check=False)

  def _on_analyze(self) -> None:
    entry = self._get_selected_entry()
    if entry:
      self.analyze_requested.emit(entry.local_path, entry.name)

  def _on_export(self) -> None:
    from PySide6.QtWidgets import QFileDialog
    path, _ = QFileDialog.getSaveFileName(self, "Export Metadata", "library_metadata.json", "JSON (*.json)")
    if path:
      self._storage.export_metadata(path)
      QMessageBox.information(self, "Export", f"Metadata exported to:\n{path}")

  def _on_delete(self) -> None:
    entry = self._get_selected_entry()
    if not entry:
      return
    reply = QMessageBox.question(
      self, "Delete Dataset",
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
