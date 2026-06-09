#!/usr/bin/env python3
"""Build Windows installer EXE and portable ZIP via PyInstaller."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
SRC = ROOT / "src" / "dataset_collector"

COMMON = [
  str(ROOT / "run.py"),
  "--noconfirm",
  "--clean",
  "--windowed",
  f"--paths={ROOT / 'src'}",
  f"--add-data={SRC / 'config'}{';' if sys.platform == 'win32' else ':'}dataset_collector/config",
  f"--add-data={SRC / 'ui' / 'styles'}{';' if sys.platform == 'win32' else ':'}dataset_collector/ui/styles",
  "--hidden-import=kaggle",
  "--hidden-import=kaggle.api.kaggle_api_extended",
  "--hidden-import=cryptography.fernet",
  "--hidden-import=langdetect",
  "--hidden-import=PIL.Image",
  "--collect-submodules=PySide6",
]


def run(args: list[str]) -> int:
  cmd = [sys.executable, "-m", "PyInstaller", *args]
  print(">", " ".join(cmd))
  return subprocess.run(cmd, cwd=ROOT).returncode


def main() -> int:
  print("Building Dataset_Collector (this may take several minutes)...")

  if run([*COMMON, "--onefile", "--name=Dataset_Collector_Setup"]) != 0:
    return 1

  if run([*COMMON, "--onedir", "--name=Dataset_Collector_Portable"]) != 0:
    return 1

  portable_dir = DIST / "Dataset_Collector_Portable"
  zip_path = DIST / "Dataset_Collector_Portable.zip"
  if portable_dir.exists():
    if zip_path.exists():
      zip_path.unlink()
    shutil.make_archive(str(zip_path.with_suffix("")), "zip", portable_dir)
    print(f"Portable ZIP: {zip_path}")

  setup_exe = DIST / "Dataset_Collector_Setup.exe"
  if setup_exe.exists():
    print(f"Setup EXE: {setup_exe}")

  print("Build complete.")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
