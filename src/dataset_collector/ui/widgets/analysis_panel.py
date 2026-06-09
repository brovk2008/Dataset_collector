"""Dataset analysis report panel."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QGroupBox,
    QLabel,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from dataset_collector.core.models import DatasetProfile


class AnalysisPanel(QWidget):
  """Displays dataset profiling results."""

  def __init__(self, parent: QWidget | None = None) -> None:
    super().__init__(parent)
    self._build_ui()

  def _build_ui(self) -> None:
    layout = QVBoxLayout(self)

    header = QLabel("Dataset Analysis")
    header.setStyleSheet("font-size: 16px; font-weight: 600;")
    layout.addWidget(header)

    self._info_label = QLabel("Select a dataset from the Library tab and click Analyze.")
    self._info_label.setObjectName("secondaryLabel")
    layout.addWidget(self._info_label)

    report_group = QGroupBox("Analysis Report")
    report_layout = QVBoxLayout(report_group)
    self._report_text = QPlainTextEdit()
    self._report_text.setReadOnly(True)
    report_layout.addWidget(self._report_text)
    layout.addWidget(report_group)

  def set_analyzing(self) -> None:
    self._info_label.setText("Analyzing dataset...")
    self._report_text.clear()

  def show_profile(self, profile: DatasetProfile, report: str) -> None:
    self._info_label.setText(f"Analysis complete: {profile.dataset_name}")
    self._report_text.setPlainText(report)

  def show_error(self, message: str) -> None:
    self._info_label.setText("Analysis failed")
    self._report_text.setPlainText(f"Error: {message}")
