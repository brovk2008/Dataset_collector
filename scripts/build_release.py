#!/usr/bin/env python3
"""Cross-platform PyInstaller build for Dataset_Collector."""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
SRC = ROOT / "src" / "dataset_collector"
SEP = ";" if sys.platform == "win32" else ":"


def _common_args() -> list[str]:
  return [
    str(ROOT / "run.py"),
    "--noconfirm",
    "--clean",
    "--windowed",
    f"--paths={ROOT / 'src'}",
    f"--add-data={SRC / 'config'}{SEP}dataset_collector/config",
    f"--add-data={SRC / 'ui' / 'styles'}{SEP}dataset_collector/ui/styles",
    "--hidden-import=kaggle",
    "--hidden-import=kaggle.api.kaggle_api_extended",
    "--hidden-import=cryptography.fernet",
    "--hidden-import=langdetect",
    "--hidden-import=PIL.Image",
    "--collect-submodules=PySide6",
  ]


def run_pyinstaller(args: list[str]) -> int:
  cmd = [sys.executable, "-m", "PyInstaller", *args]
  print(">", " ".join(cmd))
  return subprocess.run(cmd, cwd=ROOT).returncode


def build_windows() -> int:
  if run_pyinstaller([*_common_args(), "--onefile", "--name=Dataset_Collector_Setup"]) != 0:
    return 1
  if run_pyinstaller([*_common_args(), "--onedir", "--name=Dataset_Collector_Portable"]) != 0:
    return 1

  portable_dir = DIST / "Dataset_Collector_Portable"
  zip_path = DIST / "Dataset_Collector_Portable.zip"
  if portable_dir.exists():
    if zip_path.exists():
      zip_path.unlink()
    shutil.make_archive(str(zip_path.with_suffix("")), "zip", portable_dir)
    print(f"Portable ZIP: {zip_path}")
  print(f"Setup EXE: {DIST / 'Dataset_Collector_Setup.exe'}")
  return 0


def build_macos() -> int:
  if run_pyinstaller([*_common_args(), "--onedir", "--name=Dataset_Collector"]) != 0:
    return 1

  app_path = DIST / "Dataset_Collector.app"
  zip_path = DIST / "Dataset_Collector-macOS.zip"
  if app_path.exists():
    if zip_path.exists():
      zip_path.unlink()
    shutil.make_archive(str(zip_path.with_suffix("")), "zip", DIST, "Dataset_Collector.app")
    print(f"macOS ZIP: {zip_path}")
  return 0


def build_linux() -> int:
  if run_pyinstaller([*_common_args(), "--onefile", "--name=Dataset_Collector"]) != 0:
    return 1

  binary = DIST / "Dataset_Collector"
  archive_base = DIST / "Dataset_Collector-Linux"
  archive_path = Path(f"{archive_base}.tar.gz")
  if binary.exists():
    if archive_path.exists():
      archive_path.unlink()
    shutil.make_archive(str(archive_base), "gztar", DIST, "Dataset_Collector")
    print(f"Linux archive: {archive_path}")
  return 0


def main() -> int:
  system = platform.system()
  print(f"Building Dataset_Collector for {system}...")
  if system == "Windows":
    return build_windows()
  if system == "Darwin":
    return build_macos()
  return build_linux()


if __name__ == "__main__":
  raise SystemExit(main())
