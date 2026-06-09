# Build Instructions

## Development Build

```bash
pip install -e .
python run.py
```

## Production Package

```bash
pip install build
python -m build
```

This creates wheel and source distributions in `dist/`.

## Standalone Executable (Optional)

Use PyInstaller to create a standalone executable:

```bash
pip install pyinstaller
pyinstaller --name Dataset_Collector --windowed --onefile run.py
```

For a folder-based build with faster startup:

```bash
pyinstaller --name Dataset_Collector --windowed run.py
```

Include the config and styles directories:

```bash
pyinstaller --name Dataset_Collector --windowed \
  --add-data "config;config" \
  --add-data "src/dataset_collector/ui/styles;dataset_collector/ui/styles" \
  run.py
```

## Verify Installation

```bash
python -c "from dataset_collector import __version__; print(__version__)"
dataset-collector --help 2>/dev/null || python run.py
```
