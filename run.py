#!/usr/bin/env python3
"""Convenience launcher for Dataset_Collector."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from dataset_collector.main import main

if __name__ == "__main__":
  sys.exit(main())
