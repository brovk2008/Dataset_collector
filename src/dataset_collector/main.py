"""Dataset_Collector application entry point."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure src is on path when running directly
_src = Path(__file__).resolve().parent.parent
if str(_src) not in sys.path:
  sys.path.insert(0, str(_src))

from PySide6.QtWidgets import QApplication

from dataset_collector.core.config_manager import ConfigManager
from dataset_collector.ui.main_window import MainWindow


def main() -> int:
  app = QApplication(sys.argv)
  app.setApplicationName("Dataset_Collector")
  app.setOrganizationName("Dataset_Collector")

  config = ConfigManager()
  window = MainWindow(config)
  window.show()

  return app.exec()


if __name__ == "__main__":
  sys.exit(main())
