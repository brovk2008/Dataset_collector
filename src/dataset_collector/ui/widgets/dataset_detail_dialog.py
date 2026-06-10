"""Dataset detail dialog with related datasets."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
)

from dataset_collector.core.models import DatasetResult

if TYPE_CHECKING:
  from dataset_collector.databrain import DatasetBrain


class DatasetDetailDialog(QDialog):
  """Shows full dataset details with similar datasets and co-downloads."""

  def __init__(self, dataset: DatasetResult, parent=None, databrain: DatasetBrain | None = None) -> None:
    super().__init__(parent)
    self._dataset = dataset
    self._databrain = databrain
    self.setWindowTitle(f"Dataset Details — {dataset.name}")
    self.setMinimumSize(700, 700)
    self._build_ui()

  def _build_ui(self) -> None:
    layout = QVBoxLayout(self)
    ds = self._dataset
    sources = ", ".join(ds.available_sources) if ds.available_sources else ds.source.value

    form = QFormLayout()
    form.addRow("Name:", QLabel(ds.name))
    form.addRow("Rank Score:", QLabel(f"{ds.rank_score}/100"))
    form.addRow("Quality:", QLabel(f"{ds.quality_score}/10"))
    form.addRow("Available Sources:", QLabel(sources))
    form.addRow("Primary Source:", QLabel(ds.source.value))
    if ds.metadata.get("content_type") == "paper":
      authors = ds.metadata.get("authors") or []
      if authors:
        form.addRow("Authors:", QLabel(", ".join(authors[:8]) + ("..." if len(authors) > 8 else "")))
      doi = ds.metadata.get("doi")
      if doi:
        form.addRow("DOI:", QLabel(doi))
      provider = ds.metadata.get("provider")
      if provider:
        form.addRow("Provider:", QLabel(provider))
      citations = ds.metadata.get("citation_count")
      if citations:
        form.addRow("Citations:", QLabel(str(citations)))
    form.addRow("Size:", QLabel(ds.size_display))
    form.addRow("Files:", QLabel(str(ds.file_count) if ds.file_count else "—"))
    form.addRow("License:", QLabel(ds.license_info))
    form.addRow(
      "Last Updated:",
      QLabel(ds.last_updated.strftime("%Y-%m-%d %H:%M") if ds.last_updated else "—"),
    )
    layout.addLayout(form)

    if ds.requires_auth and ds.auth_message:
      auth_label = QLabel(ds.auth_message)
      auth_label.setWordWrap(True)
      auth_label.setStyleSheet("color: #FFB84D; padding: 8px; background: #2A2210; border-radius: 4px;")
      layout.addWidget(auth_label)

    layout.addWidget(QLabel("Description:"))
    desc = QTextEdit()
    desc.setReadOnly(True)
    desc.setPlainText(ds.description or "No description available.")
    desc.setMaximumHeight(100)
    layout.addWidget(desc)

    layout.addWidget(QLabel("Page URL:"))
    url_row = QHBoxLayout()
    url_field = QTextEdit()
    url_field.setReadOnly(True)
    url_field.setPlainText(ds.url)
    url_field.setMaximumHeight(36)
    url_row.addWidget(url_field)
    copy_url_btn = QPushButton("Copy")
    copy_url_btn.clicked.connect(lambda: self._copy(ds.url))
    url_row.addWidget(copy_url_btn)
    layout.addLayout(url_row)

    download_links = [u for u in ds.download_urls if u] or (
      [ds.metadata.get("download_url")] if ds.metadata.get("download_url") else []
    )
    if download_links:
      layout.addWidget(QLabel("Download URLs:"))
      links_field = QTextEdit()
      links_field.setReadOnly(True)
      links_field.setPlainText("\n".join(download_links))
      layout.addWidget(links_field)
      copy_links_btn = QPushButton("Copy All Download Links")
      copy_links_btn.clicked.connect(lambda: self._copy("\n".join(download_links)))
      layout.addWidget(copy_links_btn)

    if ds.files:
      layout.addWidget(QLabel("Files:"))
      files_field = QTextEdit()
      files_field.setReadOnly(True)
      files_field.setPlainText("\n".join(f"• {f}" for f in ds.files))
      files_field.setMaximumHeight(80)
      layout.addWidget(files_field)

    # Similar Datasets
    if self._databrain and hasattr(self._databrain, "similar_datasets"):
      try:
        similar = self._databrain.similar_datasets.find_similar(ds.id, limit=5)
        if similar:
          layout.addWidget(QLabel("Related Datasets:"))
          similar_table = QTableWidget()
          similar_table.setColumnCount(2)
          similar_table.setHorizontalHeaderLabels(["Dataset", "Similarity"])
          similar_table.setMaximumHeight(120)
          similar_table.setRowCount(len(similar))
          for row, sim_ds in enumerate(similar):
            similar_table.setItem(row, 0, QTableWidgetItem(sim_ds.name[:50]))
            similarity_score = getattr(sim_ds, "semantic_score", 0)
            similar_table.setItem(row, 1, QTableWidgetItem(f"{similarity_score:.2f}"))
          similar_table.resizeColumnsToContents()
          layout.addWidget(similar_table)
      except Exception:
        pass

    # People Also Downloaded
    if self._databrain and hasattr(self._databrain, "co_downloads_tracker"):
      try:
        co_downloads = self._databrain.co_downloads_tracker.get_co_downloads(ds.id, limit=5)
        if co_downloads:
          layout.addWidget(QLabel("People Also Downloaded:"))
          codownload_text = "\n".join(
            [f"• Dataset (downloaded {count}x)" for _, count in co_downloads[:5]]
          )
          codownload_label = QLabel(codownload_text)
          layout.addWidget(codownload_label)
      except Exception:
        pass

    layout.addStretch()
    btn_row = QHBoxLayout()
    btn_row.addStretch()
    select_btn = QPushButton("Select This Dataset")
    select_btn.setObjectName("primaryButton")
    select_btn.clicked.connect(self.accept)
    close_btn = QPushButton("Close")
    close_btn.clicked.connect(self.reject)
    btn_row.addWidget(select_btn)
    btn_row.addWidget(close_btn)
    layout.addLayout(btn_row)

  def _copy(self, text: str) -> None:
    QGuiApplication.clipboard().setText(text)
    QMessageBox.information(self, "Copied", "Copied to clipboard.")
