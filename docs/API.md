# Dataset Collector API Reference

## Table of Contents

1. [Core Search](#core-search)
2. [DatasetBrain (Semantic Discovery)](#datasetbrain-semantic-discovery)
3. [Models & Data](#models--data)
4. [Connectors](#connectors)
5. [Examples](#examples)

---

## Core Search

### SearchEngine

The main entry point for searching across multiple data sources.

#### `search(request: SearchRequest, progress_callback: Callable) -> list[DatasetResult]`

Perform parallel search across selected sources.

**Parameters**:
- `request`: SearchRequest object with query, sources, max_results
- `progress_callback`: Optional callback for progress updates (message, percentage)

**Returns**: List of DatasetResult objects, ranked by relevance

**Example**:
```python
from dataset_collector.search.search_engine import SearchEngine
from dataset_collector.search.models import SearchRequest
from dataset_collector.core.enums import DataSource

search_engine = SearchEngine(config, logger)

request = SearchRequest(
    query="anime dataset",
    sources=[DataSource.KAGGLE, DataSource.GITHUB],
    max_results=50
)

def on_progress(msg, pct):
    print(f"{msg}: {pct}%")

results = search_engine.search(request, progress_callback=on_progress)
print(f"Found {len(results)} datasets")
for result in results[:5]:
    print(f"  - {result.name} ({result.rank_score}/100)")
```

---

### SearchRequest

Configuration object for search queries.

**Attributes**:
- `query: str` — Search query
- `sources: list[DataSource]` — Data sources to search (default: all)
- `max_results: int` — Maximum results to return (default: 50)

---

### DatasetResult

Represents a single dataset from any source.

**Key Attributes**:
- `id: str` — Unique identifier
- `name: str` — Dataset name
- `description: str` — Full description
- `source: DataSource` — Original source (Kaggle, GitHub, etc.)
- `url: str` — URL to dataset
- `download_urls: list[str]` — Direct download URLs
- `size_display: str` — Human-readable size (e.g., "2.5 GB")
- `rank_score: int` — Final relevance score (0-100)
- `semantic_score: float` — Semantic similarity (0-1)
- `health_score: int` — Reliability score (0-100)
- `metadata: dict` — Additional metadata (DOI, authors, etc.)
- `available_sources: list[str]` — Where dataset appears

---

## DatasetBrain (Semantic Discovery)

### DatasetBrain

Orchestrator for all semantic discovery features.

#### `__init__(config, logger, enable_auto_download=True)`

Initialize DatasetBrain with optional automatic model download.

**Example**:
```python
from dataset_collector.databrain import DatasetBrain

databrain = DatasetBrain(config, logger, enable_auto_download=True)

# Check status
status = databrain.model_manager.get_model_status()
print(f"Model installed: {status['installed']}")
print(f"Cache size: {databrain.embeddings_cache.stats()['size_mb']} MB")
```

---

### SemanticRanker

Compute semantic similarity between queries and datasets.

#### `compute_query_embedding(query: str) -> np.ndarray`

Generate embedding for a search query.

**Parameters**:
- `query: str` — Search query

**Returns**: Numpy array (384 dimensions for all-MiniLM-L6-v2)

**Example**:
```python
from dataset_collector.databrain.semantic_ranker import SemanticRanker

ranker = SemanticRanker(model_manager, embeddings_cache, logger)

query_embedding = ranker.compute_query_embedding("machine learning data")
print(f"Query embedding shape: {query_embedding.shape}")  # (384,)
```

---

#### `score_semantic_similarity(query_embedding, dataset_embeddings) -> dict`

Compute cosine similarity between query and datasets.

**Parameters**:
- `query_embedding: np.ndarray` — Query embedding (384,)
- `dataset_embeddings: dict[str, np.ndarray]` — Dataset ID → embedding

**Returns**: Dict of dataset_id → similarity (0.0-1.0)

**Example**:
```python
# Query: "anime"
similarities = ranker.score_semantic_similarity(
    query_embedding,
    dataset_embeddings  # {dataset_id: embedding, ...}
)

# Results
for dataset_id, sim_score in sorted(similarities.items(), key=lambda x: x[1], reverse=True)[:5]:
    print(f"  {dataset_id}: {sim_score:.3f}")
```

---

### UserBehaviorTracker

Track search behavior for personalization and learning.

#### `log_search(query: str, sources: list[str], results_count: int) -> int`

Log a search query.

**Returns**: Search ID for later reference

**Example**:
```python
from dataset_collector.databrain.user_behavior import UserBehaviorTracker

tracker = UserBehaviorTracker(cache_dir)
search_id = tracker.log_search("anime", ["Kaggle", "GitHub"], 42)
print(f"Logged search ID: {search_id}")
```

---

#### `log_click(search_id: int, dataset_id: str, rank_position: int)`

Log when user clicks a result.

**Example**:
```python
# User clicked 3rd result
tracker.log_click(search_id, dataset_id="kaggle_12345", rank_position=2)
```

---

#### `log_download(dataset_id: str)`

Log when dataset is downloaded.

**Example**:
```python
tracker.log_download("kaggle_12345")
```

---

#### `log_download_set(dataset_ids: list[str])`

Log multi-dataset download (for co-occurrence tracking).

**Parameters**:
- `dataset_ids: list[str]` — List of downloaded dataset IDs

**Example**:
```python
# User downloaded 3 datasets together
tracker.log_download_set(["kaggle_001", "kaggle_002", "github_123"])
# Automatically logs all pairs: (001,002), (001,123), (002,123)
```

---

#### `get_click_score(dataset_id: str) -> float`

Get 0-1 score for dataset based on user clicks.

**Example**:
```python
score = tracker.get_click_score("kaggle_12345")
print(f"Click score: {score:.2f}")  # 0.65
```

---

### SimilarDatasetsEngine

Find semantically related datasets.

#### `find_similar(dataset_id: str, all_datasets: list[DatasetResult], limit: int = 5) -> list[DatasetResult]`

Find top N similar datasets.

**Example**:
```python
from dataset_collector.databrain.similar_datasets import SimilarDatasetsEngine

engine = SimilarDatasetsEngine(embeddings_cache, logger)

similar = engine.find_similar(
    "kaggle_anime_dataset",
    all_datasets=all_results,
    limit=5
)

print(f"Similar datasets:")
for ds in similar:
    print(f"  - {ds.name}")
```

---

### RecommendationEngine

Generate personalized dataset recommendations.

#### `get_recommendations(limit: int = 10) -> list[Recommendation]`

Get top personalized recommendations.

**Example**:
```python
from dataset_collector.databrain.recommendations import RecommendationEngine

engine = RecommendationEngine(user_behavior, similar_engine, collections, logger)

recs = engine.get_recommendations(limit=5)
for rec in recs:
    print(f"{rec.dataset.name} (Score: {rec.score:.2f})")
    print(f"  Reason: {rec.reason}")
```

---

## Models & Data

### DataSource Enum

Available data sources.

```python
from dataset_collector.core.enums import DataSource

sources = [
    DataSource.KAGGLE,
    DataSource.GITHUB,
    DataSource.ARXIV,
    DataSource.BIORXIV,
    DataSource.DATAVERSE,
    # ... others
]
```

---

## Connectors

### BaseConnector

Abstract base class for implementing custom data source connectors.

#### Implement Custom Connector

```python
from dataset_collector.search.connectors.base import BaseConnector
from dataset_collector.core.models import DatasetResult
from dataset_collector.core.enums import DataSource

class MyConnector(BaseConnector):
    """Custom data source connector."""
    
    API_URL = "https://api.example.com/datasets"
    DELAY_BETWEEN_REQUESTS = 0.2  # Rate limiting
    
    async def search(
        self,
        query: str,
        filters: object | None = None,
        max_results: int = 50,
        progress_callback = None,
    ) -> list[DatasetResult]:
        """Search implementation."""
        try:
            if progress_callback:
                progress_callback("Searching My Data Source...", 10.0)
            
            # Fetch from API
            results = await self._fetch_datasets(query, max_results)
            
            if progress_callback:
                progress_callback(f"Found {len(results)} datasets", 100.0)
            
            return results
        except Exception:
            return []
    
    async def _fetch_datasets(self, query: str, limit: int) -> list[DatasetResult]:
        """Internal fetch logic."""
        # Implement API calls, parsing, etc.
        pass
    
    async def get_download_urls(self, dataset: DatasetResult) -> list[str]:
        """Get download URLs for dataset."""
        return [dataset.url]  # or parse from API
```

#### Register Custom Connector

```python
# In search_engine.py or connector registry
from my_connectors import MyConnector

# Add to connector list
connectors = [
    KaggleConnector(...),
    GitHubConnector(...),
    MyConnector(...),  # Your custom connector
]
```

---

## Examples

### Complete Search + Discovery Workflow

```python
import asyncio
from dataset_collector.search.search_engine import SearchEngine
from dataset_collector.search.models import SearchRequest
from dataset_collector.core.enums import DataSource
from dataset_collector.databrain import DatasetBrain

async def main():
    # Initialize
    search_engine = SearchEngine(config, logger, databrain=databrain)
    databrain = DatasetBrain(config, logger)
    
    # Search
    request = SearchRequest(
        query="anime dataset",
        sources=[DataSource.KAGGLE, DataSource.GITHUB],
        max_results=50
    )
    
    def on_progress(msg, pct):
        print(f"{msg}... {pct}%")
    
    results = await search_engine.search(request, progress_callback=on_progress)
    print(f"Found {len(results)} datasets\n")
    
    # Log search for learning
    databrain.behavior_tracker.log_search("anime dataset", ["Kaggle", "GitHub"], len(results))
    
    # Display top results
    for i, result in enumerate(results[:5], 1):
        print(f"{i}. {result.name}")
        print(f"   Score: {result.rank_score}/100")
        print(f"   Health: {result.health_score}/100")
        print(f"   Source: {result.source.value}\n")
    
    # User clicks first result
    databrain.behavior_tracker.log_click(1, results[0].id, rank_position=0)
    
    # Find related datasets
    similar = databrain.similar_datasets.find_similar(
        results[0].id,
        results,
        limit=3
    )
    print(f"Similar to {results[0].name}:")
    for ds in similar:
        print(f"  - {ds.name}")
    
    # Get recommendations
    recs = databrain.recommendations.get_recommendations(limit=5)
    print(f"\nRecommendations for you:")
    for rec in recs:
        print(f"  - {rec.dataset.name} (Reason: {rec.reason})")

asyncio.run(main())
```

---

### Batch Processing

```python
import asyncio
from dataset_collector.search.search_engine import SearchEngine

async def batch_search(queries: list[str]):
    """Search multiple queries in parallel."""
    engine = SearchEngine(config, logger)
    
    tasks = [
        engine.search(SearchRequest(query=q, max_results=50))
        for q in queries
    ]
    
    all_results = await asyncio.gather(*tasks)
    
    return {q: results for q, results in zip(queries, all_results)}

# Run
queries = ["anime", "climate", "COVID-19", "genome"]
results = asyncio.run(batch_search(queries))

for query, datasets in results.items():
    print(f"{query}: {len(datasets)} datasets")
```

---

### Analytics & Insights

```python
from dataset_collector.databrain.analytics import SearchAnalytics

analytics = SearchAnalytics(user_behavior, embeddings_cache, logger)

# Get report
report = analytics.get_full_report(days_back=30)

print(f"Top searches (last 30 days):")
for query, count in report['top_searches']:
    print(f"  {query}: {count} times")

print(f"\nTop clicked datasets:")
for dataset_id, clicks in report['top_clicked']:
    print(f"  {dataset_id}: {clicks} clicks")

print(f"\nSearch success rate: {report['success_rate']:.1%}")
print(f"Model stats: {report['model_stats']}")
```

---

### Direct Database Queries

```python
import sqlite3
from pathlib import Path

db_path = Path.home() / ".dataset_collector" / "user_behavior.db"
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Most searched queries
cursor.execute("""
    SELECT query, COUNT(*) as count
    FROM searches
    GROUP BY query
    ORDER BY count DESC
    LIMIT 10
""")

for row in cursor.fetchall():
    print(f"{row['query']}: {row['count']} searches")

conn.close()
```

---

## Configuration

### Default Config

```yaml
# ~/.dataset_collector/config.yaml
databrain:
  enabled: true
  model: "all-MiniLM-L6-v2"
  auto_download: true
  weights:
    keyword: 0.40
    semantic: 0.40
    popularity: 0.10
    freshness: 0.05
    user_clicks: 0.05

search:
  timeout_per_source: 30
  rate_limit_delay: 0.1
  max_parallel: 11

cache:
  enabled: true
  ttl_days: 365
  max_size_mb: 10000
```

---

## Troubleshooting

### Common Issues

**ImportError: No module named 'dataset_collector'**
```bash
pip install dataset-collector
```

**RuntimeError: Model not installed**
```python
# Download model first
databrain.model_manager.download_model(progress_callback)
```

**Empty search results**
```python
# Try different sources or broader query
request.sources = [DataSource.KAGGLE, DataSource.GITHUB]
request.query = "machine learning"
```

---

## More Help

- **GitHub**: https://github.com/yourusername/dataset-collector
- **Issues**: Report bugs and feature requests
- **Examples**: See `examples/` directory in repository
