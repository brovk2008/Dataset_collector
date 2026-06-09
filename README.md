# Dataset_Collector

**Dataset_Collector** is an open-source desktop application for discovering, previewing, downloading, and analyzing datasets from multiple sources. Built for AI engineers, researchers, students, and data scientists.

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![PySide6](https://img.shields.io/badge/UI-PySide6-green)
![License MIT](https://img.shields.io/badge/license-MIT-lightgrey)

---

## Features

| Feature | Description |
|---------|-------------|
| **Multi-source search** | Kaggle, GitHub, Hugging Face, Government portals, Research repos, Internet Archive, Google Dataset catalogs |
| **Relevance ranking** | Results scored and sorted by how well they match your query |
| **Paginated results** | 25 datasets per page with Prev/Next navigation |
| **Size budget auto-select** | Set a total download budget (MB or GB) — best datasets auto-ticked after scan |
| **Custom file types** | Type anything: `stickers`, `icons pack`, `FIR records`, etc. |
| **Dataset detail view** | Double-click any result — copy URLs and download links |
| **Direct downloads** | Kaggle, HuggingFace, GitHub, Government portals |
| **Manifest generation** | Auto-save JSON + TXT manifests before downloading |
| **Dataset profiling** | CSV, image, and text analysis after download |
| **Library management** | Track downloads, disk usage, export metadata |

---

## Supported Sources

| Source | Search | Direct Download | Notes |
|--------|--------|-----------------|-------|
| Kaggle | ✅ | ✅ | API keys recommended for reliable search |
| GitHub | ✅ | ✅ | Optional `GITHUB_TOKEN` for higher rate limits |
| Hugging Face | ✅ | ✅ | Downloads all files from dataset repo |
| Government Data | ✅ | ✅ | US (Socrata), UK, Canada, EU, **India (data.gov.in)** |
| Research (Zenodo) | ✅ | ✅ | Academic datasets with DOI |
| Internet Archive | ✅ | Partial | Large media archives |
| Google Dataset Search | ✅ | Via source URL | Datacite + OpenAIRE + Harvard Dataverse |

### India Government Data (FIR, crime, census, etc.)

Set **Country → India** and search e.g. `FIR crime data`, `NCRB`, `census India`.

For best results, register a free API key at [data.gov.in](https://data.gov.in) and add to config:

```yaml
api_keys:
  india_data_api_key: "your_key_here"
```

Or set environment variable: `DATA_GOV_IN_API_KEY`

---

## Quick Start

### 1. Install

```bash
git clone https://github.com/brovk2008/Dataset_collector.git
cd Dataset_collector

python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
pip install -e .
```

### 2. Run

```bash
python run.py
```

### 3. Search workflow

1. **Enter query** — e.g. `medical image dataset`, `FIR data India`, `sticker pack icons`
2. **Select sources** — check the portals you want
3. **Set filters** — file types, custom type, country, budget, license
4. **Start Scan** — results appear ranked by relevance
5. **Review pages** — use ◀ Prev / Next ▶ (25 per page)
6. **Double-click** a row for full details and copy links
7. **Generate Manifest** → **Download Selected**

---

## Configuration

Edit `config/default_config.yaml`:

```yaml
paths:
  download_dir: ~/Dataset_Collector/downloads
  manifest_dir: ~/Dataset_Collector/manifests
  library_dir: ~/Dataset_Collector/library
  logs_dir: ~/Dataset_Collector/logs

download:
  max_concurrent: 4
  retry_attempts: 3
  timeout_seconds: 300

api_keys:
  kaggle_username: ""       # https://www.kaggle.com/settings
  kaggle_key: ""
  github_token: ""          # Optional — higher GitHub rate limits
  huggingface_token: ""     # Optional — private HF datasets
  india_data_api_key: ""    # https://data.gov.in — India govt data
```

Environment variables override config values:

| Variable | Service |
|----------|---------|
| `KAGGLE_USERNAME` / `KAGGLE_KEY` | Kaggle |
| `GITHUB_TOKEN` | GitHub |
| `HF_TOKEN` | Hugging Face |
| `DATA_GOV_IN_API_KEY` | India data.gov.in |

---

## Filters Guide

### File Types
Check standard types (CSV, Images, Audio, ZIP, etc.) or leave **Any** checked.

### Custom Type
Type comma-separated keywords for anything not in the list:
```
stickers, icons pack, FIR records, emoji, subtitles
```
Matches dataset name, description, and file extensions.

### Total Budget
- Set to **Maximum Size**
- Enter amount + choose **MB** or **GB**
- After scan, the app auto-selects the highest-relevance datasets that fit within your total budget

---

## Architecture

```
src/dataset_collector/
├── core/           # Models, enums, configuration
├── search/
│   ├── connectors/ # Plugin-based source connectors
│   ├── relevance.py
│   └── search_engine.py
├── download/       # Multi-threaded download engine
├── manifest/       # JSON + TXT manifest generator
├── analyzer/       # Dataset profiling (CSV, images, text)
├── storage/        # Library index + disk tracking
├── logging/        # Structured JSONL logs
└── ui/             # PySide6 desktop interface
```

Each source connector implements `BaseConnector`. Register custom connectors:

```python
from dataset_collector.search.search_engine import SearchEngine
from dataset_collector.core.enums import DataSource

engine.register_connector(DataSource.KAGGLE, MyCustomKaggleConnector())
```

---

## Download Locations

Created automatically on first launch:

| Path | Contents |
|------|----------|
| `~/Dataset_Collector/downloads/` | Downloaded dataset files |
| `~/Dataset_Collector/manifests/` | Generated manifest files |
| `~/Dataset_Collector/library/` | Library index (JSON) |
| `~/Dataset_Collector/logs/` | Application logs |

---

## Logs

Structured logs in `~/Dataset_Collector/logs/`:

- `app.log` — general log
- `search.jsonl` — search events
- `download.jsonl` — download events
- `error.jsonl` — errors
- `analysis.jsonl` — profiling results
- `manifest.jsonl` — manifest generation

---

## Building a Standalone Executable

```bash
pip install pyinstaller
pyinstaller --name Dataset_Collector --windowed run.py
```

See [docs/build.md](docs/build.md) for full instructions.

---

## Example Manifest

```json
[
  {
    "dataset_name": "Medical MNIST",
    "source": "Kaggle",
    "url": "https://www.kaggle.com/datasets/andrewmvd/medical-mnist",
    "size": "2.4 GB",
    "files": ["images.zip", "labels.csv"],
    "license": "MIT",
    "timestamp": "2026-06-09T12:00:00+00:00"
  }
]
```

See [examples/manifest_example.json](examples/manifest_example.json).

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Kaggle returns 0 results | Add API keys to config; Kaggle blocks unauthenticated scraping intermittently |
| India govt data empty | Add `india_data_api_key`; set Country → India |
| Download fails | Check URL in dataset detail dialog; retry with Retry Failed |
| Slow search | Uncheck unused sources; reduce max results in config |

---

## Contributing

1. Fork the repository
2. Create a feature branch
3. Implement your connector in `src/dataset_collector/search/connectors/`
4. Register it in `search_engine.py`
5. Open a pull request

---

## License

MIT — see LICENSE file.

---

## Links

- Repository: [github.com/brovk2008/Dataset_collector](https://github.com/brovk2008/Dataset_collector)
- India Open Data: [data.gov.in](https://data.gov.in)
- Kaggle API: [kaggle.com/docs/api](https://www.kaggle.com/docs/api)
