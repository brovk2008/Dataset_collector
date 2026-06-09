#!/usr/bin/env python3
"""Capture README screenshots from the live application UI."""

from __future__ import annotations

import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from dataset_collector.core.config_manager import ConfigManager
from dataset_collector.core.enums import DataSource, DownloadStatus
from dataset_collector.core.models import DatasetResult, DownloadTask
from dataset_collector.ui.main_window import MainWindow
from dataset_collector.ui.widgets.dataset_detail_dialog import DatasetDetailDialog

OUT = ROOT / "docs" / "screenshots"


def _sample_results() -> list[DatasetResult]:
  now = datetime.now(timezone.utc)
  return [
    DatasetResult(
      id="s1",
      name="Medical Imaging Dataset (Chest X-Ray)",
      source=DataSource.KAGGLE,
      url="https://www.kaggle.com/datasets/example",
      estimated_size_bytes=1_200_000_000,
      file_count=112_000,
      license_info="CC BY 4.0",
      last_updated=now,
      description="Labeled chest radiographs for pneumonia detection research.",
      rank_score=94,
      quality_score=8.9,
      available_sources=["Kaggle", "Hugging Face"],
    ),
    DatasetResult(
      id="s2",
      name="Climate Change Satellite Imagery",
      source=DataSource.GOVERNMENT,
      url="https://data.gov/example",
      estimated_size_bytes=3_400_000_000,
      file_count=48_000,
      license_info="Public Domain",
      last_updated=now,
      rank_score=91,
      quality_score=8.4,
      available_sources=["Government Data"],
    ),
    DatasetResult(
      id="s3",
      name="Attention Is All You Need (arXiv)",
      source=DataSource.RESEARCH_PAPERS,
      url="https://arxiv.org/abs/1706.03762",
      estimated_size_bytes=2_100_000,
      file_count=1,
      license_info="arXiv License",
      last_updated=now,
      description="Foundational transformer architecture paper.",
      rank_score=88,
      quality_score=9.2,
      available_sources=["Research Papers"],
      metadata={
        "content_type": "paper",
        "authors": ["Vaswani et al."],
        "doi": "10.48550/arXiv.1706.03762",
        "provider": "arXiv",
      },
    ),
    DatasetResult(
      id="s4",
      name="IMDB Sentiment Analysis Corpus",
      source=DataSource.HUGGINGFACE,
      url="https://huggingface.co/datasets/imdb",
      estimated_size_bytes=84_000_000,
      file_count=2,
      license_info="MIT",
      last_updated=now,
      rank_score=86,
      quality_score=8.1,
      available_sources=["Hugging Face", "GitHub"],
    ),
    DatasetResult(
      id="s5",
      name="Zenodo Research Data — Genomics",
      source=DataSource.RESEARCH,
      url="https://zenodo.org/record/example",
      estimated_size_bytes=560_000_000,
      file_count=12,
      license_info="CC0",
      last_updated=now,
      rank_score=83,
      quality_score=7.8,
      available_sources=["Research Sources"],
    ),
  ]


def _save(widget, name: str) -> None:
  OUT.mkdir(parents=True, exist_ok=True)
  path = OUT / name
  widget.grab().save(str(path))
  print(f"Saved {path}")


def capture() -> None:
  app = QApplication.instance()
  window: MainWindow = app.property("_screenshot_window")  # type: ignore[assignment]
  samples = _sample_results()

  window.resize(1360, 860)
  window.show()
  app.processEvents()

  # Main search (sidebar + empty results)
  window._tabs.setCurrentIndex(0)
  window._search_panel._query_input.setPlainText("medical image dataset")
  window._results_table.set_results([])
  window._scan_status.setVisible(True)
  window._scan_status.setText("Ready to scan")
  app.processEvents()
  _save(window, "search.png")

  # Results view
  window._results_table.set_results(samples)
  window._scan_status.setText(f"Scan complete: {len(samples)} relevant datasets found")
  window._download_panel.set_download_enabled(True)
  app.processEvents()
  _save(window, "results.png")

  # Dataset details dialog
  dialog = DatasetDetailDialog(samples[0], window)
  dialog.resize(640, 580)
  dialog.show()
  app.processEvents()
  _save(dialog, "details.png")
  dialog.close()

  # Download manager (active download on search tab)
  task = DownloadTask(
    dataset=samples[1],
    status=DownloadStatus.DOWNLOADING,
    progress_percent=62.0,
    downloaded_bytes=2_100_000_000,
    total_bytes=3_400_000_000,
    speed_bps=4_500_000,
    downloaded_files=28_400,
  )
  window._download_panel.clear_log()
  window._download_panel.set_downloading(True)
  window._download_panel.update_queue_stats(3, 1, 0)
  window._download_panel.update_task(task)
  app.processEvents()
  _save(window._download_panel, "downloads.png")

  # Settings
  window._tabs.setCurrentIndex(3)
  app.processEvents()
  _save(window, "settings.png")

  # Library with sample entries
  tmp = Path(tempfile.mkdtemp(prefix="dc_lib_"))
  for sample in samples[:3]:
    entry_dir = tmp / sample.id
    entry_dir.mkdir(parents=True, exist_ok=True)
    (entry_dir / "readme.txt").write_text("sample dataset", encoding="utf-8")
    window._library_panel.add_entry(sample.name, sample.source.value, str(entry_dir))
  window._tabs.setCurrentIndex(1)
  app.processEvents()
  _save(window, "library.png")

  app.quit()


def main() -> int:
  app = QApplication(sys.argv)
  window = MainWindow(ConfigManager())
  app.setProperty("_screenshot_window", window)
  QTimer.singleShot(800, capture)
  return app.exec()


if __name__ == "__main__":
  raise SystemExit(main())
