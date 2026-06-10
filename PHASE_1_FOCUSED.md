# Dataset_Collector v2.1 Phase 1: Core UX Improvements

## Focus: Speed, Responsiveness, Academic Discovery

This phase prioritizes the **7 features** that directly impact search speed and dataset discovery quality. Everything else is deferred.

---

## Feature 1: Parallel Search Execution

### Current Problem
```python
# search_engine.py - SEQUENTIAL (SLOW)
for source in sources:
    results = await connector.search(query)  # Wait for each
    await asyncio.sleep(rate_delay)
    # Total time: sum of all connector times
```

### Solution
```python
# PARALLEL execution
tasks = [
    self._search_with_delay(connector, query, delay)
    for delay, connector in enumerate(sources)
]
results = await asyncio.gather(*tasks, return_exceptions=True)
# Total time: max(all connector times) ~ 1/5th the sequential time
```

### Files to Modify
- `src/dataset_collector/search/search_engine.py` - `search()` method
- Update progress reporting to handle concurrent sources

### Expected Result
- **5-10x faster searches** (test with 8 sources)
- All sources queried simultaneously
- User sees partial results immediately

### Complexity: MEDIUM | Time: 2-3 hours

---

## Feature 2: Real-Time Result Streaming

### Current Problem
UI blocks and shows empty table until ALL sources complete.

### Solution
Emit results as each source completes, update UI incrementally.

### Architecture
```
SearchWorker
  ├── Start all connector tasks in parallel
  └── As each completes:
      ├── Emit individual result via Signal
      ├── UI adds row to table
      ├── Update "X results found" counter
      └── Continue accepting more results

ResultsTable
  ├── Receive result signals
  ├── Add row to table dynamically
  └── Keep running total updated
```

### Files to Modify
- `ui/workers.py` - `SearchWorker` class (add result callback)
- `ui/widgets/results_table.py` - `add_result()` method (NEW)
- `ui/main_window.py` - connect signals

### Implementation
```python
class SearchWorker(QThread):
    result_received = Signal(object)  # NEW
    progress = Signal(str, float)
    finished = Signal(list)
    
    async def search(self):
        async def on_result(result):
            self.result_received.emit(result)
        
        # Pass callback to search engine
        await self._engine.search(request, on_result_callback=on_result)
```

### UI Update
```python
# When result arrives
self._results_table.add_result(result)
count = self._results_table.total_count()
self._scan_status.setText(f"Scanning... {count} results found")
```

### Expected Result
- First result appears within 0.5 seconds
- Counter updates live (3... 15... 42...)
- Table populates as data arrives
- App feels **dramatically faster**

### Complexity: MEDIUM | Time: 3-4 hours

---

## Feature 3: Search Cancellation

### Current Problem
No way to stop a search; must wait for all sources to complete.

### Solution
Add Stop/Cancel button; gracefully shut down all running tasks.

### Files to Modify
- `ui/widgets/search_panel.py` - button logic
- `ui/workers.py` - `SearchWorker` cancellation
- `search/search_engine.py` - cancel method

### Implementation
```python
class SearchWorker(QThread):
    def __init__(self, engine, request):
        self._cancel_event = asyncio.Event()
    
    def cancel(self):
        self._cancel_event.set()
        # Tasks check this flag regularly
    
    async def search(self):
        tasks = [...]
        await asyncio.gather(*tasks, return_exceptions=True)
        # Check cancellation between sources
        if self._cancel_event.is_set():
            raise asyncio.CancelledError()
```

### UI Changes
```python
# In SearchPanel
self._scan_btn.setText("Start Scan")
# After search starts:
self._scan_btn.setText("Stop Scan")
self._scan_btn.clicked.disconnect(self._on_scan)
self._scan_btn.clicked.connect(self._on_cancel)

def _on_cancel(self):
    self._search_worker.cancel()
    self._scan_btn.setText("Start Scan")
```

### Expected Result
- User can stop search at any time
- Cleanup happens instantly
- UI remains responsive

### Complexity: LOW | Time: 1-2 hours

---

## Feature 4: arXiv Connector

### Why arXiv?
- **Largest academic preprint repository** (>2.3M papers)
- **Free, public API** (no authentication needed)
- **Strong in: physics, math, CS, quantbio, astro-ph**
- **Reliable with low rate limits** (3 req/sec is reasonable)

### Files to Create
- `src/dataset_collector/search/connectors/arxiv_connector.py`

### Implementation
```python
class ArxivConnector(BaseConnector):
    async def search(self, query, limit=50, progress_callback=None):
        # Use arxiv Python library
        # 1. Parse query into arXiv search string
        # 2. Fetch papers via API
        # 3. Extract: title, authors, abstract, PDF URL, published date
        # 4. Return DatasetResult list
        
    async def get_download_urls(self, dataset):
        # Return PDF URL from arxiv
```

### arXiv API (Free)
```
Search URL: http://export.arxiv.org/api/query?search_query=...
No auth required. 3 requests/sec limit (reasonable).
```

### Expected Fields per Paper
```
- title
- authors
- abstract
- publication_date
- arxiv_id
- pdf_url (extract from arxiv_url)
- source: DataSource.RESEARCH_PAPERS
```

### Error Handling
- Timeouts → return empty list (graceful)
- Invalid queries → return empty list
- Rate limit (429) → respect and backoff

### Complexity: LOW | Time: 2-3 hours

---

## Feature 5: bioRxiv / medRxiv Connector

### Why bioRxiv + medRxiv?
- **Largest preprint servers for life sciences**
- **bioRxiv:** general biology, bioinformatics (300K+ papers)
- **medRxiv:** clinical/medical (100K+ papers)
- **Public API available** (requires careful scraping)

### Files to Create
- `src/dataset_collector/search/connectors/biorxiv_connector.py`

### Implementation Approach
```python
class BiorxivConnector(BaseConnector):
    # bioRxiv has a JSON API endpoint
    # Endpoint: https://www.biorxiv.org/search/...?format=json
    
    async def search(self, query, limit=50):
        # 1. Build search URL
        # 2. Fetch JSON results
        # 3. Extract: title, authors, abstract, PDF URL, date
        # 4. Return DatasetResult list
```

### bioRxiv API
```
Endpoint: https://www.biorxiv.org/search/
Query params: q (search), ldate_from, ldate_to, format=json
Rate limit: Reasonable (~10 req/sec)
```

### Error Handling
- Timeouts → empty list
- Bad JSON → empty list
- Rate limit → backoff

### Complexity: MEDIUM | Time: 3-4 hours

---

## Feature 6: Harvard Dataverse Connector

### Why Harvard Dataverse?
- **Largest open-source dataset repository** (50K+ datasets)
- **High quality** (curated by Harvard)
- **Free public API** (no auth required)
- **Strong metadata** (DOI, licenses, etc.)

### Files to Create
- `src/dataset_collector/search/connectors/dataverse_connector.py`

### Implementation
```python
class DataverseConnector(BaseConnector):
    # Harvard Dataverse API
    # https://guides.dataverse.org/en/latest/api/
    
    async def search(self, query, limit=50):
        # 1. Query: https://dataverse.harvard.edu/api/search
        # 2. Extract datasets (not papers)
        # 3. Get: title, description, DOI, size, files
        # 4. Return DatasetResult list
```

### Dataverse API
```
Endpoint: https://dataverse.harvard.edu/api/search
Params: q (query), per_page, start
No auth required. Generous rate limit.
```

### Expected Fields
```
- title
- description (abstract)
- DOI
- dataset_size_bytes
- files (list of downloadable items)
- publication_date
- source: DataSource.RESEARCH_DATASETS
```

### Error Handling
- Invalid JSON → empty list
- Timeouts → empty list
- Missing fields → use defaults

### Complexity: MEDIUM | Time: 3-4 hours

---

## Feature 7: Loader Generator

### Purpose
After downloading a dataset, auto-generate starter code for common tasks.

### Files to Create
- `src/dataset_collector/loader_generator.py` (NEW)

### Implementation

#### 1. Detect File Types
```python
def detect_dataset_type(directory: Path) -> str:
    """
    Scan directory and determine type:
    - 'csv' → CSV files
    - 'images' → image directory (JPG, PNG)
    - 'json' → JSON files
    - 'mixed' → combination
    """
```

#### 2. Generate Boilerplate Code

**For CSV:**
```python
import pandas as pd

# Load dataset
df = pd.read_csv("data.csv")
print(f"Loaded {len(df)} rows, {len(df.columns)} columns")

# Explore
print(df.head())
print(df.info())
```

**For Images (PyTorch):**
```python
from torchvision import datasets, transforms

# Define transforms
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                        std=[0.229, 0.224, 0.225])
])

# Load dataset
dataset = datasets.ImageFolder("images", transform=transform)
loader = torch.utils.data.DataLoader(
    dataset, batch_size=32, shuffle=True
)

print(f"Loaded {len(dataset)} images")
for batch_idx, (data, labels) in enumerate(loader):
    print(f"Batch {batch_idx}: {data.shape}")
    break
```

**For JSON:**
```python
import json

with open("data.json") as f:
    data = json.load(f)

print(f"Loaded {len(data)} records")
print(data[0])  # Show first record
```

#### 3. UI Integration

After download completes:
```python
# In DownloadPanel
self._loader_btn = QPushButton("Generate Loader Code")
self._loader_btn.clicked.connect(self._on_generate_loader)

def _on_generate_loader(self):
    dataset_path = ...  # Selected dataset
    loader_code = generate_loader_code(dataset_path)
    
    # Save to dataset_path/loader.py
    save_path = Path(dataset_path) / "loader.py"
    save_path.write_text(loader_code)
    
    QMessageBox.information(
        self, "Loader Generated",
        f"Saved to:\n{save_path}\n\nOpen in your editor to start."
    )
```

### Expected Result
Users can download dataset → click "Generate Loader" → immediately start using data in Jupyter/scripts.

### Complexity: LOW | Time: 2-3 hours

---

## Implementation Timeline

| Feature | Effort | Days | Cumulative |
|---------|--------|------|-----------|
| 1. Parallel Search | MEDIUM | 1 | 1 |
| 2. Real-Time Streaming | MEDIUM | 1.5 | 2.5 |
| 3. Search Cancellation | LOW | 0.5 | 3 |
| 4. arXiv Connector | LOW | 1 | 4 |
| 5. bioRxiv Connector | MEDIUM | 1.5 | 5.5 |
| 6. Harvard Dataverse | MEDIUM | 1.5 | 7 |
| 7. Loader Generator | LOW | 1 | 8 |

**Total: ~8 days of development**

---

## Testing Checklist

### Parallel Search
- [ ] Search with 5+ enabled sources
- [ ] Measure time vs sequential (should be 5-8x faster)
- [ ] No missing results

### Real-Time Streaming
- [ ] First result appears <500ms
- [ ] Counter updates live
- [ ] Final count matches total results

### Cancellation
- [ ] Stop button appears during search
- [ ] Cancel works at any time
- [ ] Tasks clean up (no hanging processes)

### arXiv
- [ ] Search returns papers
- [ ] Metadata correct (title, authors, abstract)
- [ ] PDF URL valid

### bioRxiv
- [ ] Search returns papers
- [ ] Handles 0 results gracefully
- [ ] Timeouts don't crash app

### Dataverse
- [ ] Search returns datasets
- [ ] Size info accurate
- [ ] Can filter by type

### Loader
- [ ] CSV → pandas code
- [ ] Images → PyTorch code
- [ ] JSON → json code
- [ ] Code runs without errors

---

## Success Criteria for v2.1 Release

✓ Searches complete in <3 seconds (5+ sources)
✓ First result visible <500ms
✓ User can cancel anytime
✓ 3 new academic sources integrated
✓ Loader generator functional
✓ Zero crashes on API failures
✓ UI responsive throughout

