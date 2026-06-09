# Architecture

## Overview

Dataset_Collector follows clean architecture with separated concerns:

```
┌─────────────────────────────────────────┐
│              UI Layer (PySide6)          │
│  SearchPanel │ ResultsTable │ Download   │
└────────────────────┬────────────────────┘
                     │
┌────────────────────▼────────────────────┐
│           Business Logic Layer           │
│  SearchEngine │ ManifestGenerator        │
│  StorageManager │ DatasetAnalyzer        │
└──────┬──────────────┬───────────────────┘
       │              │
┌──────▼──────┐  ┌────▼──────────────────┐
│Search Engine│  │   Download Engine       │
│ Connectors  │  │   Queue Management      │
└─────────────┘  └─────────────────────────┘
       │              │
┌──────▼──────────────▼───────────────────┐
│  ConfigManager │ AppLogger │ Core Models  │
└─────────────────────────────────────────┘
```

## Layers

### UI Layer (`ui/`)

- `MainWindow` — Application shell and workflow orchestration
- `SearchPanel` — Query, sources, filters
- `ResultsTable` — Sortable, filterable results with multi-select
- `DownloadPanel` — Progress, pause/resume/cancel controls
- `LibraryPanel` — Downloaded dataset management
- `AnalysisPanel` — Profiling report display
- `workers.py` — QThread wrappers for async operations

### Business Logic

- **SearchEngine** — Orchestrates connector plugins, deduplication, logging
- **DownloadEngine** — Concurrent downloads with pause/resume/cancel/retry
- **ManifestGenerator** — JSON and TXT manifest creation
- **DatasetAnalyzer** — CSV, image, and text profiling
- **StorageManager** — Library index, disk usage, metadata export

### Source Connectors (`search/connectors/`)

Plugin-based architecture. Each connector extends `BaseConnector`:

```python
class BaseConnector(abc.ABC):
    source: DataSource

    async def search(
        self, query, filters, max_results, progress_callback
    ) -> list[DatasetResult]:
        ...
```

Register custom connectors:

```python
engine.register_connector(DataSource.KAGGLE, MyKaggleConnector())
```

### Infrastructure

- **ConfigManager** — YAML configuration with path expansion
- **AppLogger** — Structured JSONL logs per category

## Data Flow

1. User configures search → `SearchRequest`
2. `SearchEngine` dispatches to connectors in parallel sequence
3. Results deduplicated by URL → displayed in `ResultsTable`
4. User selects datasets → `ManifestGenerator` saves manifest
5. `DownloadEngine` downloads to `~/Dataset_Collector/downloads`
6. `StorageManager` indexes completed downloads
7. `DatasetAnalyzer` profiles on demand

## Future Expansion Points

The architecture supports adding:

- AI dataset recommendation (new service layer)
- Quality scoring (post-search filter plugin)
- Duplicate detection (SearchEngine hook)
- Version tracking (StorageManager extension)
- Cloud export (DownloadEngine destination adapter)
- Dataset comparison/merging (Analyzer extensions)
- Auto-updates (scheduled connector refresh)
