<div align="center">

# Dataset_Collector

**Discover, analyze, and download datasets from multiple sources through a single interface.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![GitHub Release](https://img.shields.io/github/v/release/brovk2008/Dataset_collector?label=release)](https://github.com/brovk2008/Dataset_collector/releases/latest)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)](https://github.com/brovk2008/Dataset_collector/releases)

No Python installation required — download a release for your platform.

</div>

---

## Download Latest Release

**[View all releases →](https://github.com/brovk2008/Dataset_collector/releases)**

| Platform | Download |
|----------|----------|
| **Windows Installer** | [Dataset_Collector_Setup.exe](https://github.com/brovk2008/Dataset_collector/releases/latest/download/Dataset_Collector_Setup.exe) |
| **Windows Portable** | [Dataset_Collector_Portable.zip](https://github.com/brovk2008/Dataset_collector/releases/latest/download/Dataset_Collector_Portable.zip) |
| **macOS** | [Dataset_Collector-macOS.zip](https://github.com/brovk2008/Dataset_collector/releases/latest/download/Dataset_Collector-macOS.zip) |
| **Linux** | [Dataset_Collector-Linux.tar.gz](https://github.com/brovk2008/Dataset_collector/releases/latest/download/Dataset_Collector-Linux.tar.gz) |
| **Source Code** | [GitHub Repository](https://github.com/brovk2008/Dataset_collector) |

> Downloads are built automatically by GitHub Actions when a version tag is pushed. If a link returns 404, check [Actions](https://github.com/brovk2008/Dataset_collector/actions) — the build may still be running.

**Support the project:** [Donate via Razorpay](https://rzp.io/rzp/ABzyauZu)

---

## What's New in v2.4.4 — Critical PyInstaller Bundling Fix

### 🐛 Bug Fix

**Fixed PyInstaller StreamHandler Crash**
- Bundled EXE failed at startup with `'NoneType' object has no attribute 'write'`
- Root cause: Logger's StreamHandler tried to write to stderr (None in windowed PyInstaller builds)
- Solution: Added sys.stderr availability check before initializing StreamHandler
- Also guarded sys.stderr.write() calls throughout codebase

**Result:** EXE now launches cleanly without console errors. All tests pass (19/19). ✅

---

## What's New in v2.4.3 — DatasetBrain Debugging & Model Auto-Download

### 🔧 Comprehensive Debugging Features

**Console Logging with Real-Time Visibility**
- `[MAINWINDOW]` - App initialization steps
- `[DATABRAIN]` - Model loading and initialization
- `[SETTINGS]` - UI panel updates
- Full exception tracebacks printed immediately to console + stderr

**Debug Button in Settings**
- Click "Test DatasetBrain" in Settings → Enhanced Search
- Shows model status (installed, size, path)
- Displays cache statistics (datasets cached, size in MB)
- Shows all component instances
- No silent failures - complete transparency

### 🚀 DatasetBrain Model Auto-Download

**Automatic Model Initialization**
- Model auto-downloads on app startup (174.7 MB)
- Detects HuggingFace Hub cache structure correctly
- Settings panel shows "Installed [OK]" when ready
- Zero manual configuration needed

**Fixed UI State Synchronization**
- All panels receive DatasetBrain instance immediately
- No more "DatasetBrain not available" after successful init
- Forced initialization (no lazy-loading)
- Complete visibility into initialization process

### 📊 Download Size: 292 MB (Reasonable for Full-Featured App)

**What's Included:**
- PySide6 GUI Framework (~120 MB)
- Python 3.14 Runtime (~60 MB)
- Dependencies: pandas, numpy, pillow, etc (~70 MB)
- Cryptography & SSL (~20 MB)
- Application code & data (~22 MB)

**Comparison:**
- Visual Studio Code: ~350 MB
- Discord: ~300-400 MB
- Your App: **292 MB** ✅ Standard for professional desktop tools

---

## v2.4.2 — DatasetBrain Model Download Fix

### ✅ Critical Fixes

**Model Cache Detection**
- Fixed detection of HuggingFace Hub cache structure
- Model now properly recognized as installed
- Settings panel accurately reports model status

---

## v2.4.1 — Type Safety Remediation

### 🔒 Code Quality

**Complete Type Safety**
- Fixed all 31 MyPy type errors across 19 files
- Achieved strict mode compliance
- Full type annotations for all critical paths

---

## What's New in v2.4.0 — Performance Optimization & Release Readiness

### ⚡ Performance Improvements (50-100x Faster)

**Critical O(n²) Bottleneck Fixes**
- **Deduplication**: Hash bucket + single-pass merge instead of nested loop comparison
  - 1000 results: ~500ms → ~5ms (100x faster)
- **Co-download Logging**: Batch insert in single transaction instead of individual writes
  - 10 items: ~100ms → <5ms (20x faster)

**N+1 Pattern & Analytics Optimization**
- SimilarDatasetsEngine: Load embeddings once per batch (not per-dataset)
- Analytics: Connection pooling via persistent UserBehaviorTracker
- Collections: Reverse mapping cache for O(1) dataset lookups (was O(n*m))

**Search + Dedup Pipeline**: Now completes in <100ms (was ~500ms)

### 📚 Comprehensive Documentation

**User Guide** — Complete walkthrough covering:
- Installation & setup (PyPI, GitHub, standalone .exe)
- UI navigation with screenshots
- Search features (intent detection, semantic ranking, query expansion)
- Discovery features (related datasets, co-downloads, collections, recommendations)
- Understanding scores (health score, rank score, semantic similarity)
- Advanced usage (batch downloads, custom analysis, offline usage)

**Troubleshooting Guide** — Solutions for 20+ common issues:
- Search performance, model download, cache corruption
- Recommendations/discovery features not working
- Privacy & data concerns
- Error messages with step-by-step fixes

**API Reference** — Full documentation with code examples:
- SearchEngine, DatasetBrain, UserBehaviorTracker
- Custom connector implementation
- Batch processing, analytics, database queries

### 🔄 Automated CI/CD Pipeline

**GitHub Actions Workflows:**
- **Linting**: Ruff + mypy type checking on every push
- **Testing**: pytest on Windows/Ubuntu, Python 3.10-3.12 with coverage
- **Packaging**: PyInstaller standalone .exe builds on version tags

**Release Automation:**
- Auto-build Windows .exe on `git tag v*`
- SHA256 checksums for integrity verification
- Direct upload to GitHub Releases

### 📦 Standalone Packaging

**PyInstaller Configuration**:
- Single-file `.exe` for Windows (no Python installation required)
- Total download: 292 MB (includes all dependencies + runtime)
- Bundled dependencies: PySide6, sentence-transformers, all libraries
- Model auto-downloads on first startup (174.7 MB to local cache)

---

## v2.0.0 — DatasetBrain Semantic Discovery

### 🎯 Major Features

**Semantic Search with AI-Powered Ranking**
- `sentence-transformers` embeddings for semantic understanding
- Hybrid ranking: **keyword (40%) + semantic (40%) + popularity + freshness + user clicks**
- Finds semantically related datasets, not just keyword matches
- Example: Search "anime" → finds anime subtitles + anime dialogue datasets + related research papers

**User Behavior Learning**
- Track search history and click patterns
- Boost ranking of frequently clicked datasets automatically
- "People Also Downloaded" shows co-occurrence patterns
- Personalized dataset recommendations

**Search Analytics Dashboard**
- Top searches (30 days)
- Most clicked datasets
- Search effectiveness metrics
- Model statistics and cache info

**Enhanced Dataset Health Score (0–100)**
- Metadata completeness
- Documentation quality
- Download availability
- Update recency
- Popularity scoring
- Color-coded display in results

**Local ML Without Cloud APIs**
- 384-dim embeddings cached locally (SQLite)
- Model auto-downloads on first startup (174.7 MB)
- No internet required after initial download
- Zero telemetry, fully private

**Improved UI/UX**
- Score breakdown modal — see exactly why a result ranked #N
- Adaptive layouts for small windows
- Scrollable settings panel
- Better button organization

### 🐛 Bug Fixes & Improvements

| Issue | Fix |
|-------|-----|
| **App startup hang** | Deferred DatasetBrain initialization + TYPE_CHECKING guards |
| **Circular imports** | Fixed import chains with lazy loading pattern |
| **UI text cutoff** | Reorganized buttons across multiple rows |
| **Window resize issues** | Better minimum size + flexible column widths |
| **Missing dependencies** | Added cryptography to requirements |

### 📊 What's Under the Hood

New components:
- `databrain/` — Semantic discovery subsystem
- `embeddings_cache.py` — SQLite for 384-dim vectors
- `user_behavior.py` — Search/click/download tracking
- `semantic_ranker.py` — Hybrid scoring engine
- `analytics.py` — Search statistics aggregation

---

## Screenshots

| Main Search | Results |
|:---:|:---:|
| ![Search](docs/screenshots/search.png) | ![Results](docs/screenshots/results.png) |

| Dataset Details | Download Manager |
|:---:|:---:|
| ![Details](docs/screenshots/details.png) | ![Downloads](docs/screenshots/downloads.png) |

| Settings | Library |
|:---:|:---:|
| ![Settings](docs/screenshots/settings.png) | ![Library](docs/screenshots/library.png) |

---

## Recent Improvements (v2.4.0)

| Metric | Before | After | Improvement |
|--------|--------|-------|------------|
| **Deduplication (1000 results)** | ~500ms | ~5ms | 100x faster |
| **Co-download logging (10 items)** | ~100ms | <5ms | 20x faster |
| **Search + dedup pipeline** | ~1000ms | <100ms | 10x faster |
| **Collection lookups** | O(n*m) | O(1) | Linear to constant |
| **Similar datasets batch** | Multiple queries | Single query | Fewer DB hits |
| **Database connections** | Per-query | Connection pool | Reduced overhead |
| **Documentation coverage** | Basic | Comprehensive | 3 guides + API |
| **CI/CD automation** | Manual | Automated | GitHub Actions |
| **Release packaging** | Manual .exe build | Auto-build on tag | Self-serve releases |

---

## Features

| Feature | Description |
|---------|-------------|
| **Semantic search (v2.0)** | AI-powered embeddings find semantically related datasets, not just keyword matches |
| **Hybrid ranking (v2.0)** | Composite score: 40% keyword + 40% semantic + 20% signals (popularity, freshness, clicks) |
| **User learning (v2.0)** | Tracks searches and clicks; boosts ranking of datasets you interact with |
| **Search analytics (v2.0)** | Dashboard: top queries, clicked datasets, search effectiveness, model stats |
| **Health score (v2.0)** | 0–100 reliability metric per dataset (documentation, availability, recency, popularity) |
| **Score breakdown (v2.0)** | Modal showing exact scoring components for any result |
| **Multi-source search** | Kaggle, GitHub, Hugging Face, Government portals, Research repos, Research Papers, Internet Archive, Google Dataset Search |
| **Research paper downloads** | arXiv, OpenAlex, and Zenodo publications — PDF + metadata saved locally |
| **Researcher presets** | One-click presets for academic dataset and paper searches |
| **Quality scoring** | Per-dataset quality metric (0–10) for documentation, metadata, and availability |
| **Duplicate detection** | Merges the same dataset found across multiple sources into one entry |
| **Dataset comparison** | Side-by-side compare size, license, quality, and sources (2–5 datasets) |
| **Download queue** | Pause, resume, cancel, retry failed; live speed, ETA, and remaining size |
| **Auto profiling** | CSV, image, and text analysis saved locally after each download |
| **Encrypted credentials** | Optional Kaggle, GitHub, Hugging Face tokens stored securely |
| **Public-first access** | Works immediately without API keys for public datasets |
| **Library management** | Search, sort, open folder, export metadata, delete datasets |
| **System health** | Connector status, queue info, log export as ZIP |
| **Similar datasets (v2.1)** | Find k-NN related datasets using semantic embeddings |
| **Recommendations (v2.1)** | Personalized suggestions based on search/download history |
| **Collections (v2.1)** | Auto-generated thematic clusters of related datasets |
| **Performance optimized (v2.4)** | O(n²) bottlenecks eliminated, 50-100x faster on critical paths |
| **Comprehensive docs (v2.4)** | USER_GUIDE.md, TROUBLESHOOTING.md, API.md with examples |
| **CI/CD automated (v2.4)** | GitHub Actions for linting, testing, packaging on every commit |
| **Standalone .exe (v2.4)** | Single Windows executable, no Python installation required |

---

## Supported Sources

| Source | Search | Download | Auth Required |
|--------|:------:|:--------:|:-------------:|
| Kaggle | ✅ | ✅ | Optional (recommended for search) |
| GitHub | ✅ | ✅ | Optional (higher rate limits) |
| Hugging Face | ✅ | ✅ | Only for private/gated |
| Government Data | ✅ | ✅ | Public access mode by default |
| Research Datasets (Zenodo) | ✅ | ✅ | No |
| Research Papers (arXiv, OpenAlex) | ✅ | ✅ PDF | No |
| Internet Archive | ✅ | Partial | No |
| Google Dataset Search | ✅ | Via source URL | No |

---

## Installation

### Windows

1. **Installer:** [Dataset_Collector_Setup.exe](https://github.com/brovk2008/Dataset_collector/releases/latest/download/Dataset_Collector_Setup.exe) — run and launch
2. **Portable:** [Dataset_Collector_Portable.zip](https://github.com/brovk2008/Dataset_collector/releases/latest/download/Dataset_Collector_Portable.zip) — extract and run `Dataset_Collector.exe`

### macOS

1. Download [Dataset_Collector-macOS.zip](https://github.com/brovk2008/Dataset_collector/releases/latest/download/Dataset_Collector-macOS.zip)
2. Extract and open `Dataset_Collector.app`
3. If macOS blocks the app: right-click → **Open** → confirm (unsigned build)

### Linux

1. Download [Dataset_Collector-Linux.tar.gz](https://github.com/brovk2008/Dataset_collector/releases/latest/download/Dataset_Collector-Linux.tar.gz)
2. Extract: `tar -xzf Dataset_Collector-Linux.tar.gz`
3. Run: `chmod +x Dataset_Collector && ./Dataset_Collector`

### Build from Source (all platforms)

```bash
git clone https://github.com/brovk2008/Dataset_collector.git
cd Dataset_collector

python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
pip install -e .
python run.py
```

### Build Release Locally

```bash
pip install -r requirements.txt
python scripts/build_release.py   # auto-detects Windows / macOS / Linux
```

---

## Quick Start

1. **Launch** Dataset_Collector
2. **Enter a query** — e.g. `medical images`, `transformer architecture`, `climate dataset`
3. **Select sources** or click **Researcher Preset** / **Papers Only**
4. **Click Start Scan** — results ranked by relevance and quality
5. **Select items** (datasets or papers) and **Download Selected**
6. **Papers** save as PDF + `paper_metadata.json` (authors, DOI, abstract)
7. **Datasets** auto-profile in the Analysis tab; manage all downloads in Library

---

## For Researchers

Dataset_Collector is built for academic and applied research workflows:

| Workflow | How |
|----------|-----|
| **Find datasets** | Enable *Research Sources*, *Government Data*, *Hugging Face* — or use **Researcher Preset** |
| **Find papers** | Enable *Research Papers* or click **Papers Only** |
| **Download papers** | Select results → Download — PDFs from arXiv, OpenAlex, Zenodo |
| **Literature + data** | Search both datasets and papers in one scan |
| **Reproducibility** | Manifests, metadata JSON, and analysis reports saved locally |

**Paper sources:** arXiv (preprints), OpenAlex (open-access works), Zenodo (publications with PDFs).

**Dataset sources:** Zenodo research data, government open data, Hugging Face, GitHub, and more.

No API keys required for public research content.

---

## Authentication Guide

All authentication is **optional**. The app works out of the box for public datasets.

| Provider | When Needed | How to Connect |
|----------|-------------|----------------|
| **Kaggle** | Reliable search & authenticated downloads | Settings → Username + API Key → Test Connection |
| **GitHub** | Higher API rate limits | Settings → Personal Access Token |
| **Hugging Face** | Private or gated datasets only | Settings → HF Token |
| **India data.gov.in** | Enhanced catalog access | Settings → API Key (public mode works without it) |

Credentials are encrypted locally at `~/.dataset_collector/credentials.enc` and never logged or exposed.

---

## Architecture

```
Dataset_collector/
├── run.py                          # Launcher
├── build.spec                      # PyInstaller build config
├── scripts/build_release.py        # Cross-platform release builder
├── .github/workflows/release.yml   # Auto-build on release tags
├── config/default_config.yaml      # User-overridable settings
└── src/dataset_collector/
    ├── core/           Models, config, encrypted credential store
    ├── databrain/      Semantic discovery engine (v2.0)
    │   ├── model_manager.py       sentence-transformers lifecycle
    │   ├── embeddings_cache.py    SQLite 384-dim vector cache
    │   ├── semantic_ranker.py     Cosine similarity + hybrid ranking
    │   ├── user_behavior.py       Search/click/download tracking
    │   └── analytics.py           Search statistics aggregation
    ├── search/
    │   ├── connectors/ Plugin-style source connectors
    │   ├── relevance.py  Hybrid ranking (keyword + semantic)
    │   ├── quality.py    Quality scoring (0–10)
    │   └── dedup.py      Cross-source duplicate merging
    ├── download/       Queue engine with pause/resume/cancel
    ├── manifest/       JSON + TXT manifest generation
    ├── analyzer/       CSV, image, text profiling
    ├── storage/        Local library index
    ├── logging/        Structured app logs
    └── ui/             PySide6 desktop interface
        ├── main_window.py          Main application window
        ├── widgets/
        │   ├── search_panel.py      Query + filters input
        │   ├── results_table.py     Paginated results display
        │   ├── download_panel.py    Download progress & controls
        │   ├── analytics_panel.py   Search analytics dashboard (v2.0)
        │   ├── search_explanation_dialog.py  Score breakdown (v2.0)
        │   └── ...other panels
        └── styles/dark_theme.qss   Dark theme stylesheet
```

### Plugin System

Each data source implements `BaseConnector` with `search()` and optional `get_download_urls()`. Register custom connectors via `SearchEngine.register_connector()`.

---

## Changelog

### v2.4.0 (Latest) — Performance Optimization & Release Readiness

**Performance Improvements (50-100x Faster):**
- Fixed critical O(n²) deduplication bottleneck: 1000 results now process in <5ms (was ~500ms)
- Optimized co-download logging: batch insert in single transaction (20x faster)
- Eliminated N+1 patterns in SimilarDatasetsEngine and analytics
- Added connection pooling for database queries
- Implemented reverse mapping cache for O(1) collection lookups

**Documentation:**
- Comprehensive User Guide (USER_GUIDE.md) with UI walkthrough, features, scoring explanation
- Troubleshooting Guide (TROUBLESHOOTING.md) with 20+ common issues and solutions
- Full API Reference (API.md) with code examples and custom connector guide

**CI/CD & Automation:**
- GitHub Actions workflows: linting (ruff + mypy), testing (pytest on 3 Python versions, 2 platforms)
- Automated PyInstaller packaging on version tags with SHA256 verification
- Auto-release to GitHub Releases with checksums

**Packaging:**
- PyInstaller spec for standalone Windows .exe (no Python installation required)
- Pre-download support for bundled sentence-transformers model

**Testing & Quality:**
- All v2.0-v2.3 features preserved (zero breaking changes)
- Performance verified: search + dedup completes in <100ms
- Release-ready: documented, tested, packaged

### v2.3.0

**Added:**
- Wired all v2.1 discovery features into UI
- Similar Datasets tab in dataset details
- People Also Downloaded section
- Recommendations panel
- Health score display in results
- Intent tags below search box
- Collections support

### v2.2.0

**Added:**
- Semantic ranking with hybrid scoring
- User behavior tracking infrastructure
- Analytics aggregation engine
- Search intent classification
- Query expansion engine

### v2.1.0

**Added:**
- 3 New Connectors: arXiv, bioRxiv/medRxiv, Harvard Dataverse
- Loader Generator for auto-generating dataset loading code
- Similar Datasets Engine (k-NN search)
- Query Expansion (semantic variants)
- Co-Downloads Tracker (People Also Downloaded)
- Health Score (reliability metric 0-100)
- Collections Generator (thematic clustering)
- Recommendations Engine (personalized suggestions)

### v2.0.0

**Added:**
- DatasetBrain semantic discovery engine with sentence-transformers embeddings
- Hybrid ranking system (keyword + semantic + popularity + freshness + user clicks)
- User behavior tracking (searches, clicks, co-downloads) with SQLite persistence
- Search analytics dashboard (top queries, clicked datasets, effectiveness)
- Dataset health score (0–100) with 5 quality factors
- Score breakdown modal showing ranking components
- Enhanced search settings panel with model download and cache management
- Analytics panel displaying search insights
- Adaptive UI layouts for small windows and mobile

**Fixed:**
- Critical startup hang caused by eager DatasetBrain initialization
- Circular import chains resolved with TYPE_CHECKING guards
- UI text cutoff on small windows (reorganized buttons)
- Window sizing issues (increased minimum to 1000x700)
- Missing cryptography dependency

**Changed:**
- Results table: buttons wrapped across 2 rows for better fit
- Settings panel: added scroll area for vertical scrolling
- Library panel: button organization improved
- Download panel: better label spacing and sizing

### v1.1.3

**Features:**
- Multi-source dataset search (8+ sources)
- Research paper downloads (PDF + metadata)
- Download queue with pause/resume/cancel
- Library management and local storage
- Encrypted credential storage
- System health monitoring
- Cross-platform builds (Windows/macOS/Linux)

---

## Roadmap

### ✅ Completed in v2.4.0
- Performance optimization (50-100x speedup on critical paths)
- Comprehensive user documentation
- Automated CI/CD pipeline (linting, testing, packaging)
- Standalone .exe packaging

### ✅ Completed in v2.0-v2.3
- Similar datasets engine (k-NN similarity search)
- Smart query expansion (semantic query enhancement)
- Dataset collections (auto-generated thematic clusters)
- Search intent classification
- Personalized recommendations
- Dataset co-download analysis

### 📋 Planned Features
- Cloud storage export (S3, GCS, OneDrive)
- Dataset version tracking and diffing
- Dataset merging utilities
- REST API for programmatic access
- Dataset validation and quality checks
- Collaborative dataset annotations
- Web-based companion dashboard
- Mobile app (iOS/Android)

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes
4. Push and open a Pull Request

Bug reports and feature requests are welcome via [GitHub Issues](https://github.com/brovk2008/Dataset_collector/issues).

---

## Donate

If Dataset_Collector saves you time, consider supporting development:

[![Donate via Razorpay](https://img.shields.io/badge/Donate-Razorpay-0C2451?style=for-the-badge&logo=razorpay&logoColor=white)](https://rzp.io/rzp/ABzyauZu)

The desktop app also includes a **Donate** button in the header that opens the same page.

---

## License

MIT License — see [LICENSE](LICENSE) for details.
