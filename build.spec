# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Dataset_Collector Windows builds."""

import sys
from pathlib import Path

block_cipher = None
root = Path(SPECPATH)
src = root / "src" / "dataset_collector"

datas = [
  (str(src / "config"), "dataset_collector/config"),
  (str(src / "ui" / "styles"), "dataset_collector/ui/styles"),
]

hiddenimports = [
  "kaggle",
  "kaggle.api.kaggle_api_extended",
  "cryptography",
  "cryptography.fernet",
  "langdetect",
  "PIL",
  "PIL.Image",
  "pandas",
  "yaml",
  "aiofiles",
  "httpx",
  "aiohttp",
]

a = Analysis(
  [str(root / "run.py")],
  pathex=[str(root / "src")],
  binaries=[],
  datas=datas,
  hiddenimports=hiddenimports,
  hookspath=[],
  hooksconfig={},
  runtime_hooks=[],
  excludes=[],
  win_no_prefer_redirects=False,
  win_private_assemblies=False,
  cipher=block_cipher,
  noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Portable (onedir) — default COLLECT target
exe_portable = EXE(
  pyz,
  a.scripts,
  [],
  exclude_binaries=True,
  name="Dataset_Collector",
  debug=False,
  bootloader_ignore_signals=False,
  strip=False,
  upx=True,
  console=False,
  disable_windowed_traceback=False,
  argv_emulation=False,
  target_arch=None,
  codesign_identity=None,
  entitlements_file=None,
)

coll = COLLECT(
  exe_portable,
  a.binaries,
  a.zipfiles,
  a.datas,
  strip=False,
  upx=True,
  upx_exclude=[],
  name="Dataset_Collector_Portable",
)

# One-file installer-style EXE
exe_setup = EXE(
  pyz,
  a.scripts,
  a.binaries,
  a.zipfiles,
  a.datas,
  [],
  name="Dataset_Collector_Setup",
  debug=False,
  bootloader_ignore_signals=False,
  strip=False,
  upx=True,
  upx_exclude=[],
  runtime_tmpdir=None,
  console=False,
  disable_windowed_traceback=False,
  argv_emulation=False,
  target_arch=None,
  codesign_identity=None,
  entitlements_file=None,
)
