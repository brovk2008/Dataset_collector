#!/usr/bin/env python3
"""Build Windows installer EXE and portable ZIP (wrapper for build_release.py)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
  script = ROOT / "scripts" / "build_release.py"
  return subprocess.run([sys.executable, str(script)], cwd=ROOT).returncode


if __name__ == "__main__":
  raise SystemExit(main())
