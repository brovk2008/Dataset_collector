# Dataset_Collector v2.1+ Implementation Plan

## Executive Summary
This plan addresses architectural improvements, new data sources, real-time search, and enhanced UX/UI across 4 implementation phases prioritized by user impact and development complexity.

---

## Phase 1: Data Sources Expansion & Real-Time Search (Weeks 1-2)

### 1.1 Add Preprint Servers
**Files to modify:** `src/dataset_collector/search/connectors/`

**New Connectors:**
```
├── arxiv_connector.py       (arXiv, physics/math/CS)
├── biorxiv_connector.py     (bioRxiv + medRxiv)
├── ssrn_connector.py        (Social sciences)
├── chemrxiv_connector.py    (Chemistry)
├── psyarxiv_connector.py    (Psychology)
├── techrxiv_connector.py    (IEEE tech/engineering)
├── osf_preprints_connector.py (Open Science Framework)
├── zenodo_connector.py      (CERN multidisciplinary - UPDATE existing)
├── dryad_connector.py       (Scientific datasets)
├── figshare_connector.py    (Multidisciplinary data)
├── harvard_dataverse_connector.py
├── mendeley_data_connector.py
└── icpsr_connector.py       (Social science data)
```

**Implementation Strategy:**
- Use existing BaseConnector interface
- Each connector searches via API or web scraping with fallbacks:
  - Primary: Official API (arXiv, SSRN use public APIs)
  - Fallback: `requests + BeautifulSoup` for HTML parsing
  - Fallback 2: Google Scholar integration for metadata enrichment
- Implement exponential backoff for rate limiting
- Cache metadata for 24 hours

**Error Handling Pattern:**
```python
async def search(self, query):
    try:
        # Primary: Official API
        return await self._search_api(query)
    except (ConnectionError, TimeoutError, HTTPError):
        try:
            # Fallback: Web scraping
            return await self._search_scrape(query)
        except:
            # Fallback 2: Metadata from Google Scholar
            return await self._search_scholar_fallback(query)
```

### 1.2 Real-Time Result Streaming
**Files to modify:** `search_engine.py`, `ui/main_window.py`, `ui/widgets/results_table.py`

**Changes:**
```python
# OLD: Block until all sources return
results = await search(request)
self._results_table.set_results(results)

# NEW: Stream results as they arrive
async def search_streaming(request, on_result_callback):
    tasks = [
        self._connector_search(conn, query, on_result_callback)
        for conn in connectors
    ]
    # Gather with return_exceptions=True to prevent one failure blocking others
    await asyncio.gather(*tasks, return_exceptions=True)
```

**UI Updates:**
- Add placeholder rows while waiting for data
- Update row counts in real-time
- Animate new rows as they appear
- Show source badge on each result

### 1.3 Search Cancellation Button
**Files to modify:** `ui/widgets/search_panel.py`, `ui/workers.py`, `search_engine.py`

**Implementation:**
```python
class SearchWorker(QThread):
    def __init__(self, engine, request):
        self._cancel_event = asyncio.Event()  # NEW
    
    def cancel(self):
        self._cancel_event.set()
    
    async def search(self):
        # Check cancellation before each connector
        if self._cancel_event.is_set():
            raise CancelledError()
```

**UI:**
- Change "Start Scan" to "Start Scan" / "Stop Scan" toggle
- Disable when no search active
- Show "Cancelled" status message

---

## Phase 2: Architectural Improvements (Weeks 3-4)

### 2.1 Parallel Search Execution
**File:** `src/dataset_collector/search/search_engine.py`

**Current (Sequential):**
```python
for source in sources:
    results = await connector.search(query)  # Wait for each to finish
    await asyncio.sleep(rate_delay)
```

**Improved (Parallel):**
```python
tasks = [
    self._search_source_with_delay(connector, query, i, len(sources))
    for i, connector in enumerate(sources)
]
results = await asyncio.gather(*tasks, return_exceptions=True)
```

**Expected Improvement:** 5-8x faster search (parallel I/O vs sequential)

### 2.2 Strategy Pattern for Downloads
**Files to modify:** 
- `download/download_engine.py`
- All connector files

**Current (Anti-pattern):**
```python
if dataset.source == DataSource.KAGGLE:
    await self._download_kaggle(...)
elif dataset.source == DataSource.HUGGINGFACE:
    await self._download_huggingface(...)
# 10+ more elif chains
```

**Improved (Strategy Pattern):**
```python
# In BaseConnector
async def download(self, dataset, target_dir, progress_cb):
    """Abstract method each connector implements"""
    raise NotImplementedError

# In DownloadEngine
async def _download_one(self, task):
    connector = self._get_connector(task.dataset.source)
    await connector.download(task.dataset, task.target_dir, self._on_progress)
```

**Benefits:**
- Add new sources without modifying DownloadEngine
- Each connector owns its download logic
- Testable in isolation

### 2.3 Consolidate Utility Functions
**File:** Create `src/dataset_collector/core/utils.py`

**Functions to consolidate:**
```python
def format_bytes(size_bytes: int) -> str
def sanitize_filename(name: str) -> str
def validate_url(url: str) -> bool
def extract_doi(text: str) -> str
def is_valid_json(text: str) -> bool
def safe_requests_get(url, timeout=30, retries=3) -> requests.Response
```

**Refactor:** Update 6+ files to import from `utils.py` instead of duplicating

---

## Phase 3: Enhanced Features (Weeks 5-6)

### 3.1 Automated ML Framework Export
**File:** `src/dataset_collector/loader_generator.py` (NEW)

**Functionality:**
- After download, detect file types: CSV → pandas, images → PIL/torchvision, JSON → json
- Generate `loader.py` with boilerplate:
  ```python
  # For CSV
  import pandas as pd
  df = pd.read_csv('data.csv')
  
  # For images (PyTorch)
  from torchvision import datasets, transforms
  dataset = datasets.ImageFolder('images/', transform=transforms.ToTensor())
  ```

**Integration:**
- Triggered after download completes
- Optional checkbox in download settings
- Files saved in dataset directory

### 3.2 Format Standardization (CSV → Parquet)
**File:** `src/dataset_collector/format_converter.py` (NEW)

**Functionality:**
- After CSV download, offer: "Compress to Parquet? (save 50-80% disk space)"
- Use pandas + pyarrow
- Progress callback for large files (>500MB)

**Code:**
```python
async def convert_csv_to_parquet(csv_path, target_path, progress_cb):
    df = pd.read_csv(csv_path, chunksize=10000)
    df.to_parquet(target_path, compression='snappy')
    # Show 50-80% size reduction
```

### 3.3 Scheduled Sync & Dataset Versioning
**File:** `src/dataset_collector/scheduler/` (NEW)

**Components:**
- `version_checker.py` - polls sources weekly for updates
- `sync_manager.py` - coordinates download of new versions
- UI button: "Watch This Dataset" in Library tab

**Implementation:**
- Use APScheduler for background jobs
- Store last_updated timestamp per dataset
- Notify user if newer version available

### 3.4 Health Dashboard (Expand analyzer.py)
**Files to modify:** `src/dataset_collector/analyzer/dataset_analyzer.py`

**New Profiling:**
- Missing data percentage per column
- Duplicate row count
- Class imbalance (for classification datasets)
- Data type distribution
- Statistical summaries (min/max/mean for numeric columns)

**Library:**
- Use `ydata-profiling` (lightweight) OR `pandas.describe()`
- Display as HTML report in Analysis tab

---

## Phase 4: UI/UX Improvements (Week 7)

### 4.1 Better Spacing & Alignment
**Files to modify:**
- `ui/main_window.py` - main layout margins
- `ui/widgets/*.py` - component spacing
- `ui/styles/dark_theme.qss` - spacing constants

**Changes:**
- Consistent 8px/16px grid spacing
- Better button sizing (min-width: 100px)
- Proper label alignment (right-align form labels)
- Adequate whitespace between sections
- Responsive padding for small windows

**QSS Updates:**
```css
QGroupBox {
    margin-top: 12px;
    padding-top: 8px;
    spacing: 8px;
}

QFormLayout {
    spacing: 12px;
    row-spacing: 8px;
}

QPushButton {
    min-width: 100px;
    padding: 8px;
}
```

### 4.2 Results Display Enhancement
**Files to modify:** `ui/widgets/results_table.py`

**Changes:**
- Add source badge/icon next to each result
- Show result index (1/50, 2/50, etc.) for real-time updates
- Better status indicators (Loading..., Completed, Cancelled)
- Improved pagination controls

---

## Implementation Priority Matrix

| Phase | Feature | Effort | Impact | Priority |
|-------|---------|--------|--------|----------|
| 1 | Preprint servers (13 sources) | HIGH | CRITICAL | P0 |
| 1 | Real-time streaming | MEDIUM | HIGH | P0 |
| 1 | Search cancellation | LOW | HIGH | P0 |
| 2 | Parallel search | MEDIUM | CRITICAL | P1 |
| 2 | Strategy pattern (downloads) | MEDIUM | MEDIUM | P1 |
| 2 | Utils consolidation | LOW | MEDIUM | P1 |
| 3 | ML framework export | MEDIUM | MEDIUM | P2 |
| 3 | Parquet conversion | LOW | MEDIUM | P2 |
| 3 | Scheduled sync | MEDIUM | LOW | P2 |
| 3 | Health dashboard | MEDIUM | MEDIUM | P2 |
| 4 | UI improvements | LOW | HIGH | P3 |

---

## Error Handling Strategy

**Principle:** "Graceful Degradation with Fallbacks"

### Connector Error Handling:
```
Try API → Scrape HTML → Google Scholar → Return Empty
```

### Download Error Handling:
```
Primary method → Secondary method → Skip dataset with warning
```

### Example (arXiv):
```python
async def search(self, query):
    try:
        # Primary: arXiv API (reliable)
        return await self._search_arxiv_api(query)
    except (requests.ConnectionError, asyncio.TimeoutError):
        try:
            # Fallback: Parse arXiv advanced search results
            return await self._search_arxiv_scrape(query)
        except:
            # Final fallback: Return empty list (don't crash)
            self._logger.warning(f"arXiv search failed for '{query}'")
            return []
```

---

## Testing Strategy

### Unit Tests:
- Each connector's search method (mock HTTP responses)
- Parallel execution (concurrent task completion)
- Error handling (simulate API failures)

### Integration Tests:
- Full search workflow with 5+ sources
- Real-time streaming display
- Download cancellation

### E2E Tests:
- Search → View results → Download → Analyze
- Dataset versioning & sync

---

## Rollout Plan

### v2.1.0 (Immediate)
- [ ] Phase 1: Data sources + real-time + cancellation
- [ ] Phase 4: UI improvements
- [ ] Release via GitHub Actions

### v2.2.0 (2 weeks later)
- [ ] Phase 2: Architectural improvements
- [ ] Performance benchmarks

### v2.3.0 (4 weeks later)
- [ ] Phase 3: Enhanced features
- [ ] User testing & feedback

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Connector rate limiting | Exponential backoff + caching |
| UI lag during search | Async rendering + threading |
| Disk space for downloads | Parquet conversion + warnings |
| Data loss on cancellation | Checkpoint partial downloads |
| API deprecation | Maintain fallback scraping methods |

---

## Success Metrics

- [ ] Search 5+ sources in <3 seconds (parallel)
- [ ] Results stream in real-time (first result <500ms)
- [ ] Zero crashes on API failures (100% fallback coverage)
- [ ] UI responsive during download (no freezing)
- [ ] 13+ data sources integrated
- [ ] Cancellation works reliably

