"""Main application window."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from dataset_collector.analyzer.dataset_analyzer import DatasetAnalyzer
from dataset_collector.core.config_manager import ConfigManager
from dataset_collector.core.constants import DONATE_URL
from dataset_collector.core.credential_store import CredentialStore
from dataset_collector.core.enums import DataSource, DownloadStatus, ManifestFormat
from dataset_collector.core.models import DatasetResult
from dataset_collector.download.download_engine import DownloadEngine, KAGGLE_AUTH_MSG
from dataset_collector.logging.logger import AppLogger
from dataset_collector.manifest.manifest_generator import ManifestGenerator
from dataset_collector.search.search_engine import SearchEngine
from dataset_collector.storage.storage_manager import StorageManager
from dataset_collector.ui.widgets.analysis_panel import AnalysisPanel
from dataset_collector.ui.widgets.analytics_panel import AnalyticsPanel
from dataset_collector.ui.widgets.dataset_detail_dialog import DatasetDetailDialog
from dataset_collector.ui.widgets.download_panel import DownloadPanel
from dataset_collector.ui.widgets.health_panel import HealthPanel
from dataset_collector.ui.widgets.library_panel import LibraryPanel
from dataset_collector.ui.widgets.recommendations_panel import RecommendationsPanel
from dataset_collector.ui.widgets.results_table import ResultsTable
from dataset_collector.ui.widgets.search_panel import SearchPanel
from dataset_collector.ui.widgets.settings_panel import SettingsPanel
from dataset_collector.ui.workers import (
    AnalysisWorker,
    DownloadWorker,
    RetryDownloadWorker,
    SearchWorker,
)

if TYPE_CHECKING:
  from dataset_collector.databrain import DatasetBrain


class MainWindow(QMainWindow):
  """Primary application window orchestrating all workflow panels."""

  def __init__(self, config: ConfigManager) -> None:
    super().__init__()
    self._config = config
    self._logger = AppLogger(config.logs_dir)
    self._creds = CredentialStore()

    # Lazy-initialize DatasetBrain (defer heavy imports until needed)
    self._databrain: DatasetBrain | None = None

    # Initialize SearchEngine without DatasetBrain (will be added when DatasetBrain initializes)
    self._search_engine = SearchEngine(config, self._logger, self._creds, databrain=None)
    self._download_engine = DownloadEngine(config, self._logger, self._creds)
    self._manifest_gen = ManifestGenerator(config.manifest_dir, self._logger)
    self._analyzer = DatasetAnalyzer(self._logger)
    self._storage = StorageManager(config.library_dir, self._logger)

    self._search_worker: SearchWorker | None = None
    self._download_worker: DownloadWorker | RetryDownloadWorker | None = None
    self._analysis_worker: AnalysisWorker | None = None
    self._last_analysis_path: str = ""
    self._analyze_queue: list[tuple[str, str]] = []
    self._results: list[DatasetResult] = []
    self._last_search_id: int = -1

    self._setup_window()
    self._build_ui()
    self._connect_signals()

    print("[MAINWINDOW] Forcing DatasetBrain initialization on startup...")
    self._get_databrain()
    print(f"[MAINWINDOW] DatasetBrain after init: {self._databrain}")

  def _get_databrain(self) -> DatasetBrain | None:
    """Lazy-initialize DatasetBrain on first access."""
    if self._databrain is None:
      try:
        print("[DATABRAIN] Attempting initialization...")
        self._logger.info("Starting DatasetBrain initialization")

        from dataset_collector.databrain import DatasetBrain as DB
        print("[DATABRAIN] Import successful, creating instance...")

        self._databrain = DB(self._config, self._logger)
        print(f"[DATABRAIN] Instance created: {self._databrain}")
        print(f"[DATABRAIN] Enabled status: {self._databrain.enabled}")

        self._search_engine._databrain = self._databrain
        print("[DATABRAIN] Search engine updated")

        if hasattr(self, "_settings_panel"):
          print(f"[DATABRAIN] Setting in settings panel (had: {getattr(self._settings_panel, '_databrain', 'NOT SET')})")
          self._settings_panel.set_databrain(self._databrain)
          print(f"[DATABRAIN] Settings panel now has: {self._settings_panel._databrain}")

        if hasattr(self, "_analytics_panel"):
          print("[DATABRAIN] Setting in analytics panel")
          self._analytics_panel.set_databrain(self._databrain)

        if hasattr(self, "_recommendations_panel"):
          print("[DATABRAIN] Setting in recommendations panel")
          self._recommendations_panel.set_databrain(self._databrain)

        self._logger.info("DatasetBrain initialization successful")
        print("[DATABRAIN] Initialization complete")
      except Exception as e:
        error_msg = f"Failed to initialize DatasetBrain: {e}"
        print(f"[DATABRAIN ERROR] {error_msg}")
        print("[DATABRAIN] Full traceback:")
        import traceback
        traceback.print_exc()
        self._logger.error(error_msg)
        import sys
        sys.stderr.write(f"\n[DATABRAIN INITIALIZATION FAILED]\n{error_msg}\n")
        traceback.print_exc(file=sys.stderr)
    return self._databrain

  def _setup_window(self) -> None:
    self.setWindowTitle("Dataset_Collector")
    self.resize(
      self._config.get("ui", "window_width", default=1280),
      self._config.get("ui", "window_height", default=800),
    )
    self.setMinimumSize(1000, 700)

    theme_path = Path(__file__).parent / "styles" / "dark_theme.qss"
    if theme_path.exists():
      self.setStyleSheet(theme_path.read_text(encoding="utf-8"))

  def _build_ui(self) -> None:
    central = QWidget()
    self.setCentralWidget(central)
    main_layout = QVBoxLayout(central)
    main_layout.setContentsMargins(8, 8, 8, 8)

    # Header
    header = QHBoxLayout()
    title = QLabel("Dataset_Collector")
    title.setStyleSheet("font-size: 18px; font-weight: 700; color: #4F8CFF;")
    subtitle = QLabel("Dataset discovery, analysis, and download")
    subtitle.setObjectName("secondaryLabel")
    header.addWidget(title)
    header.addSpacing(12)
    header.addWidget(subtitle)
    header.addStretch()
    donate_btn = QPushButton("Donate")
    donate_btn.setObjectName("donateButton")
    donate_btn.setToolTip("Support Dataset_Collector development")
    donate_btn.clicked.connect(self._open_donate_page)
    header.addWidget(donate_btn)
    main_layout.addLayout(header)

    # Tabs
    self._tabs = QTabWidget()

    # Search tab
    search_tab = QWidget()
    search_layout = QVBoxLayout(search_tab)

    splitter = QSplitter(Qt.Orientation.Horizontal)
    splitter.setCollapsible(0, False)
    splitter.setCollapsible(1, False)

    # Left: search config
    left_widget = QWidget()
    left_layout = QVBoxLayout(left_widget)
    left_layout.setContentsMargins(0, 0, 0, 0)
    self._search_panel = SearchPanel()
    left_layout.addWidget(self._search_panel)
    left_widget.setMinimumWidth(280)
    splitter.addWidget(left_widget)

    # Right: results + download
    right_widget = QWidget()
    right_layout = QVBoxLayout(right_widget)
    right_layout.setContentsMargins(0, 0, 0, 0)

    self._scan_progress = QProgressBar()
    self._scan_progress.setRange(0, 100)
    self._scan_progress.setValue(0)
    self._scan_progress.setVisible(False)
    self._scan_status = QLabel("")
    self._scan_status.setObjectName("secondaryLabel")
    self._scan_status.setVisible(False)

    right_layout.addWidget(self._scan_status)
    right_layout.addWidget(self._scan_progress)

    self._results_table = ResultsTable()
    right_layout.addWidget(self._results_table, stretch=1)

    self._download_panel = DownloadPanel()
    right_layout.addWidget(self._download_panel)

    splitter.addWidget(right_widget)
    splitter.setStretchFactor(0, 1)
    splitter.setStretchFactor(1, 2)
    splitter.setSizes([400, 800])

    search_layout.addWidget(splitter)
    self._tabs.addTab(search_tab, "Search && Download")

    # Library tab
    self._library_panel = LibraryPanel(self._storage)
    self._tabs.addTab(self._library_panel, "Library")

    # Analysis tab
    self._analysis_panel = AnalysisPanel()
    self._tabs.addTab(self._analysis_panel, "Analysis")

    # Analytics tab (DatasetBrain)
    self._analytics_panel = AnalyticsPanel(None)
    self._tabs.addTab(self._analytics_panel, "Analytics")

    # Recommendations tab (DatasetBrain)
    self._recommendations_panel = RecommendationsPanel(None)
    self._tabs.addTab(self._recommendations_panel, "Recommendations")

    # Settings tab
    self._settings_panel = SettingsPanel(self._creds)
    self._settings_panel.set_databrain(None)
    self._tabs.addTab(self._settings_panel, "Settings")

    # System health tab
    self._health_panel = HealthPanel(
      self._logger,
      self._download_engine,
      self._creds,
      self._config.logs_dir,
    )
    self._tabs.addTab(self._health_panel, "System Health")

    main_layout.addWidget(self._tabs)

    # Status bar
    self._status_bar = QStatusBar()
    self.setStatusBar(self._status_bar)
    self._status_bar.showMessage("Ready")

  def _connect_signals(self) -> None:
    self._search_panel.scan_requested.connect(self._on_scan)
    self._search_panel.cancel_requested.connect(self._on_cancel_scan)
    self._results_table.selection_changed.connect(self._on_selection_changed)
    self._results_table.dataset_activated.connect(self._on_dataset_details)
    self._download_panel.download_clicked.connect(self._on_download)
    self._download_panel.manifest_clicked.connect(self._on_manifest)
    self._download_panel.pause_clicked.connect(self._download_engine.pause)
    self._download_panel.resume_clicked.connect(self._download_engine.resume)
    self._download_panel.cancel_clicked.connect(self._on_cancel_download)
    self._download_panel.retry_clicked.connect(self._on_retry_download)
    self._library_panel.analyze_requested.connect(self._on_analyze)
    self._settings_panel.credentials_changed.connect(self._on_credentials_changed)

  def _log_click(self, dataset: DatasetResult, rank_position: int = 0) -> None:
    """Log user click on dataset for learning."""
    try:
      databrain = self._get_databrain()
      if databrain and hasattr(databrain, "behavior_tracker"):
        search_id = dataset.metadata.get("_search_id", -1)
        if search_id > 0:
          databrain.behavior_tracker.log_click(
            search_id, dataset.id, rank_position, "table"
          )
    except Exception as e:
      self._logger.info(f"Failed to log click: {e}")

  def _open_donate_page(self) -> None:
    QDesktopServices.openUrl(QUrl(DONATE_URL))

  def _on_credentials_changed(self) -> None:
    self._search_engine.reload_connectors()
    self._health_panel.refresh()
    self._status_bar.showMessage("Credentials updated — connectors reloaded")

  def _on_scan(self) -> None:
    request = self._search_panel.get_search_request()
    if not request:
      QMessageBox.warning(self, "Search", "Enter a query and select at least one source.")
      return

    self._search_panel.set_scanning(True)
    self._scan_progress.setVisible(True)
    self._scan_status.setVisible(True)
    self._scan_progress.setValue(0)
    self._scan_status.setText("Searching sources...")
    self._status_bar.showMessage("Scanning...")
    self._results_table.set_results([])  # Clear old results for new search

    # Classify intent
    databrain = self._get_databrain()
    if databrain and hasattr(databrain, "intent_classifier"):
      try:
        intents = databrain.intent_classifier.classify_intent(request.query)
        self._search_panel.set_intent_tags(intents)
      except Exception:
        self._search_panel.set_intent_tags([])
    else:
      self._search_panel.set_intent_tags([])

    self._search_worker = SearchWorker(self._search_engine, request)
    self._search_worker.progress.connect(self._on_scan_progress)
    self._search_worker.result_received.connect(self._on_result_received)  # NEW: Stream results
    self._search_worker.finished.connect(self._on_scan_finished)
    self._search_worker.error.connect(self._on_scan_error)
    self._search_worker.start()

  def _on_cancel_scan(self) -> None:
    if self._search_worker and self._search_worker.isRunning():
      self._search_worker.cancel()
      self._search_panel.set_scanning(False)
      self._scan_progress.setVisible(False)
      self._scan_status.setText("Search cancelled")
      self._status_bar.showMessage("Search cancelled")

  def _on_scan_progress(self, message: str, percent: float) -> None:
    self._scan_progress.setValue(int(percent))
    self._scan_status.setText(message)
    self._status_bar.showMessage(message)

  def _on_result_received(self, result) -> None:
    """NEW: Add result to table as it arrives (real-time streaming)."""
    self._results_table.add_result(result)
    count = len(self._results_table._all_results)
    self._scan_status.setText(f"Scanning sources... {count} results found")
    self._status_bar.showMessage(f"Found {count} datasets so far")

  def _on_scan_finished(self, results: list) -> None:
    self._results = results

    # Compute health scores and populate dataset embeddings
    databrain = self._get_databrain()
    if databrain:
      try:
        databrain.health_scorer.populate_health_scores(results)
      except Exception as e:
        self._logger.info(f"Failed to populate health scores: {e}")

    self._results_table.set_results(results)
    self._search_panel.set_scanning(False)
    self._scan_progress.setVisible(False)
    self._scan_status.setText(f"Scan complete: {len(results)} relevant datasets found")
    self._status_bar.showMessage(f"Found {len(results)} datasets")

    budget = self._search_panel.get_budget_bytes()
    if budget and results:
      count = self._results_table.apply_budget_suggestions(budget)
      self._scan_status.setText(
        f"Scan complete: {len(results)} found — auto-selected {count} within budget"
      )
      self._status_bar.showMessage(f"Auto-selected {count} datasets within size budget")

    # Refresh analytics
    if databrain and hasattr(self, "_analytics_panel"):
      self._analytics_panel.set_databrain(databrain)
      self._analytics_panel.refresh()

    # Refresh recommendations
    if databrain and hasattr(self, "_recommendations_panel"):
      self._recommendations_panel.set_databrain(databrain)
      self._recommendations_panel.refresh()

    self._on_selection_changed()

  def _on_dataset_details(self, dataset: DatasetResult) -> None:
    self._log_click(dataset)
    databrain = self._get_databrain()
    dialog = DatasetDetailDialog(dataset, self, databrain=databrain, all_datasets=self._results)
    if dialog.exec():
      self._results_table.select_dataset(dataset.id)

  def _on_scan_error(self, error: str) -> None:
    self._search_panel.set_scanning(False)
    self._scan_progress.setVisible(False)
    self._scan_status.setText(f"Scan error: {error}")
    self._status_bar.showMessage("Scan failed")
    QMessageBox.critical(self, "Search Error", error)

  def _on_selection_changed(self) -> None:
    count = self._results_table.selected_count()
    self._download_panel.set_download_enabled(count > 0)

  def _on_manifest(self) -> None:
    selected = self._results_table.get_selected()
    if not selected:
      QMessageBox.warning(self, "Manifest", "Select at least one dataset.")
      return

    json_path = self._manifest_gen.save(selected, ManifestFormat.JSON)
    txt_path = self._manifest_gen.save(selected, ManifestFormat.TXT)
    QMessageBox.information(
      self,
      "Manifest Generated",
      f"Manifests saved:\n\nJSON: {json_path}\nTXT: {txt_path}",
    )

  def _on_download(self) -> None:
    selected = self._results_table.get_selected()
    if not selected:
      return

    blocked = [ds for ds in selected if ds.requires_auth and ds.auth_message]
    if blocked:
      QMessageBox.warning(
        self,
        "Authentication Required",
        blocked[0].auth_message or (
          "One or more selected datasets require authentication. "
          "Open Settings to connect your account."
        ),
      )
      return

    kaggle_no_creds = [
      ds for ds in selected
      if ds.source == DataSource.KAGGLE
      and not (self._creds.kaggle_username() and self._creds.kaggle_key())
      and not (self._config.get_api_key("kaggle_username") and self._config.get_api_key("kaggle_key"))
    ]
    if kaggle_no_creds:
      reply = QMessageBox.question(
        self,
        "Kaggle Download",
        f"{len(kaggle_no_creds)} Kaggle dataset(s) selected without API credentials.\n\n"
        f"Public download will be attempted. For reliable access:\n{KAGGLE_AUTH_MSG}\n\n"
        "Continue anyway?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
      )
      if reply != QMessageBox.StandardButton.Yes:
        return

    self._download_panel.clear_log()
    self._download_panel.update_queue_stats(len(selected), 0, 0)
    self._download_panel.set_downloading(True)
    self._status_bar.showMessage(f"Downloading {len(selected)} datasets...")

    # Log download set for co-download tracking
    databrain = self._get_databrain()
    if databrain:
      databrain.co_downloads_tracker.log_download_set([ds.id for ds in selected])

    self._download_worker = DownloadWorker(self._download_engine, selected)
    self._download_worker.progress.connect(self._download_panel.update_task)
    self._download_worker.finished.connect(self._on_download_finished)
    self._download_worker.error.connect(self._on_download_error)
    self._download_worker.start()

  def _on_download_finished(self, tasks: list) -> None:
    self._download_panel.set_downloading(False)
    completed = sum(1 for t in tasks if t.status == DownloadStatus.COMPLETED)
    failed = sum(1 for t in tasks if t.status == DownloadStatus.FAILED)
    self._status_bar.showMessage(f"Download complete: {completed} succeeded, {failed} failed")
    self._download_panel.set_has_failures(failed > 0)
    self._download_panel.update_queue_stats(len(tasks), completed, failed)
    self._health_panel.refresh()

    for task in tasks:
      if task.status == DownloadStatus.COMPLETED and task.local_path:
        self._library_panel.add_entry(
          task.dataset.name,
          task.dataset.source.value,
          task.local_path,
        )
        self._auto_analyze(task.local_path, task.dataset.name)

  def _on_download_error(self, error: str) -> None:
    self._download_panel.set_downloading(False)
    QMessageBox.critical(self, "Download Error", error)

  def _on_cancel_download(self) -> None:
    self._download_engine.cancel()
    self._download_panel.set_downloading(False)
    self._status_bar.showMessage("Download cancelled")

  def _on_retry_download(self) -> None:
    self._download_panel.set_downloading(True)
    self._download_worker = RetryDownloadWorker(self._download_engine)
    self._download_worker.progress.connect(self._download_panel.update_task)
    self._download_worker.finished.connect(self._on_download_finished)
    self._download_worker.error.connect(self._on_download_error)
    self._download_worker.start()

  def _on_analyze(self, path: str, name: str) -> None:
    self._tabs.setCurrentIndex(2)
    self._run_analysis(path, name, switch_tab=True)

  def _auto_analyze(self, path: str, name: str) -> None:
    self._analyze_queue.append((path, name))
    if self._analysis_worker is None or not self._analysis_worker.isRunning():
      self._process_analyze_queue()

  def _process_analyze_queue(self) -> None:
    if not self._analyze_queue:
      return
    path, name = self._analyze_queue.pop(0)
    self._run_analysis(path, name, switch_tab=False)

  def _run_analysis(self, path: str, name: str, switch_tab: bool) -> None:
    self._last_analysis_path = path
    if switch_tab:
      self._tabs.setCurrentIndex(2)
    self._analysis_panel.set_analyzing()

    self._analysis_worker = AnalysisWorker(self._analyzer, path, name)
    self._analysis_worker.finished.connect(self._on_analysis_finished)
    self._analysis_worker.error.connect(self._analysis_panel.show_error)
    self._analysis_worker.start()

  def _on_analysis_finished(self, profile) -> None:
    report_path = None
    if self._last_analysis_path:
      base = Path(self._last_analysis_path)
      report_path = str(base / "analysis_report.txt")
    report = self._analyzer.generate_report(profile, output_path=report_path)
    self._analysis_panel.show_profile(profile, report)
    self._process_analyze_queue()
