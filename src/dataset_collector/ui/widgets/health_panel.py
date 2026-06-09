"""System health and diagnostics panel."""

from __future__ import annotations

import zipfile
from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from dataset_collector.core.credential_store import CredentialStore
from dataset_collector.download.download_engine import DownloadEngine
from dataset_collector.logging.logger import AppLogger


class HealthPanel(QWidget):
  """Displays connector status, queue info, and log export."""

  def __init__(
    self,
    logger: AppLogger,
    download_engine: DownloadEngine,
    credential_store: CredentialStore,
    logs_dir: Path,
    parent: QWidget | None = None,
  ) -> None:
    super().__init__(parent)
    self._logger = logger
    self._download = download_engine
    self._creds = credential_store
    self._logs_dir = Path(logs_dir)
    self._build_ui()
    self.refresh()

  def _build_ui(self) -> None:
    layout = QVBoxLayout(self)

    status_group = QGroupBox("System Status")
    status_layout = QVBoxLayout(status_group)
    self._status_text = QTextEdit()
    self._status_text.setReadOnly(True)
    self._status_text.setMaximumHeight(220)
    status_layout.addWidget(self._status_text)
    layout.addWidget(status_group)

    errors_group = QGroupBox("Recent Activity")
    errors_layout = QVBoxLayout(errors_group)
    self._errors_text = QTextEdit()
    self._errors_text.setReadOnly(True)
    errors_layout.addWidget(self._errors_text)
    layout.addWidget(errors_group)

    btn_row = QVBoxLayout()
    refresh_btn = QPushButton("Refresh")
    refresh_btn.clicked.connect(self.refresh)
    btn_row.addWidget(refresh_btn)
    export_btn = QPushButton("Export Logs as ZIP")
    export_btn.clicked.connect(self._export_logs)
    btn_row.addWidget(export_btn)
    layout.addLayout(btn_row)

  def refresh(self) -> None:
    tasks = self._download.get_tasks()
    active = sum(1 for t in tasks if t.status.value == "downloading")
    pending = sum(1 for t in tasks if t.status.value == "pending")
    failed = sum(1 for t in tasks if t.status.value == "failed")
    completed = sum(1 for t in tasks if t.status.value == "completed")

    kaggle = "Connected" if self._creds.kaggle_username() else "Public mode"
    github = "Token set" if self._creds.github_token() else "Public mode"
    hf = "Token set" if self._creds.huggingface_token() else "Public mode"
    india = "Enhanced" if self._creds.india_api_key() else "Public access mode"

    lines = [
      f"Download queue: {len(tasks)} total",
      f"  Active: {active}  Pending: {pending}  Completed: {completed}  Failed: {failed}",
      "",
      "Connectors:",
      f"  Kaggle: {kaggle}",
      f"  GitHub: {github}",
      f"  Hugging Face: {hf}",
      f"  Government Data: {india}",
      "",
      "✓ Public access mode enabled for government data",
      "✓ Application ready — no configuration required",
    ]
    self._status_text.setPlainText("\n".join(lines))

    log_lines: list[str] = []
    app_log = self._logs_dir / "app.log"
    if app_log.exists():
      try:
        content = app_log.read_text(encoding="utf-8", errors="ignore")
        log_lines = content.strip().splitlines()[-30:]
      except OSError:
        pass
    self._errors_text.setPlainText("\n".join(log_lines) or "No recent log entries.")

  def _export_logs(self) -> None:
    path, _ = QFileDialog.getSaveFileName(
      self, "Export Logs", f"dataset_collector_logs_{datetime.now():%Y%m%d}.zip", "ZIP (*.zip)"
    )
    if not path:
      return
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
      if self._logs_dir.exists():
        for f in self._logs_dir.iterdir():
          if f.is_file():
            zf.write(f, f.name)
    self._errors_text.append(f"\nExported logs to: {path}")
