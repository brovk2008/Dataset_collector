# Dataset Collector User Guide

## Table of Contents

1. [Installation & Setup](#installation--setup)
2. [Quick Start](#quick-start)
3. [UI Walkthrough](#ui-walkthrough)
4. [Search Features](#search-features)
5. [Discovery Features](#discovery-features)
6. [Settings & Configuration](#settings--configuration)
7. [Understanding Scores](#understanding-scores)
8. [Advanced Usage](#advanced-usage)
9. [FAQ](#faq)

---

## Installation & Setup

### From PyPI

```bash
pip install dataset-collector
dataset-collector
```

### From GitHub

```bash
git clone https://github.com/yourusername/dataset-collector.git
cd dataset-collector
pip install -e .
python -m dataset_collector
```

### From Standalone Executable

1. Download `dataset-collector-v2.4.0.exe` from [Releases](https://github.com/yourusername/dataset-collector/releases)
2. Double-click to launch (no installation required)
3. On first launch, the app will download the embeddings model (~90 MB)

### Initial Configuration

1. **First Launch**: App opens with empty search history
2. **Model Download**: Click "Settings" → "Enhanced Search" → "Download Model" (one-time, ~90 MB)
3. **Data Location**: All data stored in `~/.dataset_collector/` (configurable in settings)

---

## Quick Start

### 1. Search for a Dataset

1. Click in the search box
2. Type keywords (e.g., "anime", "COVID-19", "MRI scans")
3. Select data sources (or leave "All" checked)
4. Press Enter or click "Search"

### 2. View Results

- Results appear in the table, ranked by relevance
- **Health Score**: Green indicator (80+), Yellow (60-79), Red (<60)
- **Intent Tags**: Show detected topic (e.g., "NLP", "Medical Imaging")

### 3. Explore a Dataset

- Click any result to open **Dataset Details** dialog
- See description, download links, related datasets, and "People Also Downloaded"
- Click "Select This Dataset" to download

### 4. Download Multiple Datasets

- Check multiple results, then click "Download Selected"
- Co-downloads are tracked for future recommendations

---

## UI Walkthrough

### Main Window

```
┌─────────────────────────────────────────────┐
│ [Logo] Dataset Collector v2.4.0             │
├─────────────────────────────────────────────┤
│ Search: [anime____________] [Search] [Help] │
│ Sources: ☑ Kaggle ☑ GitHub ☑ arXiv ... ☑  │
│ Intent: Computer Vision, Animation         │
├─────────────────────────────────────────────┤
│ Results (42 found)                          │
│ ┌─────────────────────────────────────────┐ │
│ │ [☐] Anime Subtitle Dataset      99%  OK │ │
│ │ [☐] Japanese Animation Scripts   87%    │ │
│ │ [☐] Manga OCR Training Set       76%    │ │
│ └─────────────────────────────────────────┘ │
│ [Select All] [Download Selected] [⋮ More]   │
├─────────────────────────────────────────────┤
│ Recommendations | Analytics | Settings      │
└─────────────────────────────────────────────┘
```

### Dataset Details Dialog

```
┌─────────────────────────────────┐
│ Dataset Details — Anime Dataset │
├─────────────────────────────────┤
│ Name: Anime Subtitle Dataset    │
│ Rank Score: 99/100              │
│ Quality: 9/10                   │
│ Available Sources: Kaggle       │
│ DOI: 10.1234/example            │
│ License: CC-BY-4.0              │
│                                 │
│ Description:                    │
│ [Large text area...]            │
│                                 │
│ Related Datasets:               │
│ • Japanese Animation Scripts 0.94
│ • Manga OCR Training Set    0.87 │
│                                 │
│ People Also Downloaded:         │
│ • Dataset A (42 downloads)      │
│ • Dataset B (31 downloads)      │
│                                 │
│ [Select] [Close]                │
└─────────────────────────────────┘
```

---

## Search Features

### Basic Search

- **Keywords**: Type any words (e.g., "anime", "climate data")
- **Multi-source**: Results merged from 11 sources (Kaggle, GitHub, arXiv, bioRxiv, etc.)
- **Filtering**: Select specific sources to narrow search
- **Cancellation**: Click "Stop" button during search to cancel

### Intent Detection

Dataset Collector **automatically detects** what you're looking for:

- **Search**: "I need OCR data"
- **Detected Intent**: Computer Vision, OCR, Document Image, Text Recognition
- **Result**: Ranking boosts datasets tagged with these intents

### Semantic Search

Results ranked by **both** keyword match + semantic meaning:

- **Keyword (40%)**: How well title/description matches your search
- **Semantic (40%)**: How similar embedding-space meaning is
- **Popularity (10%)**: Download count, stars, usage
- **Freshness (5%)**: How recent the dataset is
- **User Clicks (5%)**: Your historical clicks on similar datasets

### Query Expansion

Automatically expands queries to improve recall without losing precision:

- User searches: `"anime"`
- Expansion finds: `"anime"`, `"japanese animation"`, `"manga"`, `"anime dialogue"`
- Results matching any expanded term get a 10-20% ranking boost

---

## Discovery Features

### Related Datasets

Find datasets similar to one you're interested in:

1. Click any result to open **Dataset Details**
2. Scroll to **"Related Datasets"** section
3. Click a related dataset to open its details
4. Use this to explore dataset clusters

**Use case**: "I liked this astronomy dataset, what else is in this domain?"

### People Also Downloaded

Learn what others downloaded together with a dataset:

1. Open **Dataset Details**
2. Scroll to **"People Also Downloaded"** section
3. Shows co-downloaded datasets with counts
4. Example: "42 users also downloaded: [Dataset A], [Dataset B]"

**Use case**: Discover complementary datasets you might have missed

### Collections

Auto-generated thematic groups of related datasets:

1. Search results may show **"Recommended Collection"** banner
2. Click to view all datasets in that cluster (e.g., "Robotics" collection)
3. Collections based on semantic similarity + user tagging

**Use case**: Browse entire domain at once instead of individual searches

### Recommendations

Personalized dataset suggestions based on your search + download history:

1. Click **"Recommendations"** tab
2. Shows: "Because you searched 'anime', try: [Dataset A], [Dataset B]"
3. Recommendations improve as you search and download more
4. Reasons shown for each recommendation

**Use case**: "What should I explore next?"

---

## Settings & Configuration

### Enhanced Search Settings

1. Click **"Settings"** → **"Enhanced Search"**
2. **Status**: Shows if embeddings model is installed
3. **Download Model**: Click to download (one-time, ~90 MB, non-blocking)
4. **Cache Stats**: Shows embeddings cache size and dataset count
5. **Rebuild Cache**: Regenerate all embeddings (rare, takes a few minutes)
6. **Clear Learning Data**: Delete all search/click history (cannot be undone)

### Data Location

All data stored locally in: `~/.dataset_collector/`

```
~/.dataset_collector/
├── cache/
│   ├── embeddings.db          # Dataset embeddings (indexed for <5ms lookup)
│   ├── user_behavior.db       # Search/click/download history
│   └── sentence-transformers/ # Embeddings model (90 MB)
└── downloads/                 # Downloaded datasets
```

### Clearing Data

- **Clear Cache**: Settings → "Rebuild Cache" → "Yes"
- **Clear History**: Settings → "Clear Learning Data" → "Yes"
- **Clear Downloads**: Delete files from `~/.dataset_collector/downloads/`

---

## Understanding Scores

### Health Score (0-100)

Measures dataset reliability and usefulness:

- **80-100** 🟢 Excellent: Well-documented, recent, popular
- **60-79** 🟡 Good: Usable, some documentation gaps
- **40-59** 🟠 Fair: Minimal docs, may need cleanup
- **0-39** 🔴 Poor: Sparse documentation, outdated

**Factors**:
- Documentation quality (has README, description)
- Metadata completeness (title, description, tags)
- Download availability (URLs working)
- Update recency (< 6 months old)
- Popularity (downloads, stars, usage)

### Rank Score (0-100)

How relevant a result is to your search:

```
Rank = (
  Keyword Match     × 40% +
  Semantic Match    × 40% +
  Popularity        × 10% +
  Freshness         ×  5% +
  User Clicks       ×  5%
)
```

**Example**: Search "anime"
```
Result: Anime Subtitle Dataset
├─ Keyword Match: 95/100 (title contains "anime")
├─ Semantic: 98/100 (embedding very similar)
├─ Popularity: 72/100 (many downloads)
├─ Freshness: 84/100 (updated 2 months ago)
└─ User Clicks: 12/100 (you clicked it before)
Final Score: 93/100 ✓ Highly Relevant
```

### Semantic Similarity (0.0-1.0)

Cosine similarity between query and dataset in embedding space:

- **0.90+**: Nearly identical semantic meaning
- **0.75-0.89**: Similar topics
- **0.60-0.74**: Related but distinct
- **<0.60**: Unrelated

---

## Advanced Usage

### Batch Download

1. Check multiple results
2. Click "Download Selected"
3. All checked datasets download in parallel
4. Co-downloads tracked automatically

### Custom Analysis

Access raw data in `~/.dataset_collector/`:

- **Searches**: Query `user_behavior.db` → `searches` table
- **Clicks**: Query `user_behavior.db` → `clicks` table
- **Co-downloads**: Query `user_behavior.db` → `co_downloads` table

Example SQL:
```sql
-- Top searched keywords
SELECT query, COUNT(*) as count FROM searches
GROUP BY query ORDER BY count DESC LIMIT 10;

-- Most clicked datasets
SELECT dataset_id, COUNT(*) as clicks FROM clicks
GROUP BY dataset_id ORDER BY clicks DESC LIMIT 10;
```

### Offline Usage

All features work offline once downloaded:

1. First search requires internet (to fetch from sources)
2. Subsequent searches use cached results + embeddings
3. Intent detection, recommendations, scoring: all local

---

## FAQ

**Q: Why is my first search slow?**
A: First search downloads the embeddings model (~90 MB). Subsequent searches are 10-50x faster.

**Q: Can I use this without downloading the model?**
A: Yes. Enhanced Search is optional. Keyword-only search works without model.

**Q: Where does my data go?**
A: Everything stays local: `~/.dataset_collector/`. No cloud sync, no telemetry.

**Q: How do I update the application?**
A: PyPI: `pip install --upgrade dataset-collector`
EXE: Download new version from releases page.

**Q: Can I add custom data sources?**
A: Yes. Implement the `BaseConnector` interface in `src/dataset_collector/search/connectors/`.

**Q: Why do recommendations change over time?**
A: Recommendations improve as you search, click, and download more datasets.

**Q: Can I export my search history?**
A: Yes. Query `user_behavior.db` or use analytics dashboard.

**Q: Is my search data anonymous?**
A: Yes. All data stored locally; nothing sent to remote servers.

---

## Getting Help

- **In-App Help**: Click "?" button in main window
- **Issues**: [GitHub Issues](https://github.com/yourusername/dataset-collector/issues)
- **Troubleshooting**: See [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
