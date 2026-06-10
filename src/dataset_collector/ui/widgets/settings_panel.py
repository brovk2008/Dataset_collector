"""Application settings and authentication panel."""

from __future__ import annotations

import asyncio

import httpx
from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from dataset_collector.core.credential_store import CredentialStore


class SettingsPanel(QWidget):
  """Manage optional API credentials. App works without any configuration."""

  credentials_changed = Signal()

  def __init__(self, store: CredentialStore, parent: QWidget | None = None) -> None:
    super().__init__(parent)
    self._store = store
    self._build_ui()
    self._load_values()

  def _build_ui(self) -> None:
    outer_layout = QVBoxLayout(self)
    outer_layout.setContentsMargins(0, 0, 0, 0)

    # Create scrollable content area
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll.setFrameShape(QScrollArea.Shape.NoFrame)

    content_widget = QWidget()
    layout = QVBoxLayout(content_widget)
    layout.setContentsMargins(8, 8, 8, 8)

    intro = QLabel(
      "All authentication is optional. Dataset_Collector works immediately for public datasets. "
      "Connect accounts below only when you need higher rate limits or private/gated content."
    )
    intro.setWordWrap(True)
    intro.setObjectName("secondaryLabel")
    layout.addWidget(intro)

    # Kaggle
    kaggle_group = QGroupBox("Kaggle (Optional)")
    kaggle_form = QFormLayout(kaggle_group)
    self._kaggle_user = QLineEdit()
    self._kaggle_user.setPlaceholderText("Kaggle username")
    kaggle_form.addRow("Username:", self._kaggle_user)
    self._kaggle_key = QLineEdit()
    self._kaggle_key.setEchoMode(QLineEdit.EchoMode.Password)
    self._kaggle_key.setPlaceholderText("API key from kaggle.com/settings")
    kaggle_form.addRow("API Key:", self._kaggle_key)
    self._kaggle_status = QLabel("Not connected")
    self._kaggle_status.setObjectName("secondaryLabel")
    kaggle_form.addRow("Status:", self._kaggle_status)
    kaggle_btns = QHBoxLayout()
    self._kaggle_test = QPushButton("Test Connection")
    self._kaggle_test.clicked.connect(self._test_kaggle)
    self._kaggle_save = QPushButton("Save")
    self._kaggle_save.setObjectName("primaryButton")
    self._kaggle_save.clicked.connect(self._save_kaggle)
    kaggle_btns.addWidget(self._kaggle_test)
    kaggle_btns.addWidget(self._kaggle_save)
    kaggle_btns.addStretch()
    kaggle_form.addRow("", kaggle_btns)
    layout.addWidget(kaggle_group)

    # GitHub
    gh_group = QGroupBox("GitHub (Optional)")
    gh_form = QFormLayout(gh_group)
    self._github_token = QLineEdit()
    self._github_token.setEchoMode(QLineEdit.EchoMode.Password)
    self._github_token.setPlaceholderText("Personal access token — improves search rate limits")
    gh_form.addRow("Token:", self._github_token)
    self._github_status = QLabel("Not configured — public search active")
    self._github_status.setObjectName("secondaryLabel")
    gh_form.addRow("Status:", self._github_status)
    gh_save = QPushButton("Save GitHub Token")
    gh_save.clicked.connect(self._save_github)
    gh_form.addRow("", gh_save)
    layout.addWidget(gh_group)

    # Hugging Face
    hf_group = QGroupBox("Hugging Face (Optional)")
    hf_form = QFormLayout(hf_group)
    self._hf_token = QLineEdit()
    self._hf_token.setEchoMode(QLineEdit.EchoMode.Password)
    self._hf_token.setPlaceholderText("Required only for private or gated datasets")
    hf_form.addRow("Token:", self._hf_token)
    self._hf_status = QLabel("Not configured — public datasets available")
    self._hf_status.setObjectName("secondaryLabel")
    hf_form.addRow("Status:", self._hf_status)
    hf_save = QPushButton("Save Hugging Face Token")
    hf_save.clicked.connect(self._save_hf)
    hf_form.addRow("", hf_save)
    layout.addWidget(hf_group)

    # Government
    gov_group = QGroupBox("Government Data")
    gov_layout = QVBoxLayout(gov_group)
    self._gov_status = QLabel("Public access mode enabled - no API key required")
    self._gov_status.setStyleSheet("color: #4F8CFF;")
    gov_layout.addWidget(self._gov_status)
    gov_hint = QLabel(
      "India data.gov.in: optional API key for enhanced catalog access. "
      "Register free at data.gov.in if public search is insufficient."
    )
    gov_hint.setWordWrap(True)
    gov_hint.setObjectName("secondaryLabel")
    gov_layout.addWidget(gov_hint)
    self._india_key = QLineEdit()
    self._india_key.setEchoMode(QLineEdit.EchoMode.Password)
    self._india_key.setPlaceholderText("Optional India OGD API key")
    gov_layout.addWidget(self._india_key)
    india_save = QPushButton("Save India API Key (Optional)")
    india_save.clicked.connect(self._save_india)
    gov_layout.addWidget(india_save)
    layout.addWidget(gov_group)

    # Enhanced Search (DatasetBrain)
    enhanced_group = QGroupBox("Enhanced Search (DatasetBrain)")
    enhanced_form = QFormLayout(enhanced_group)

    self._enhanced_status = QLabel("Not installed")
    self._enhanced_status.setObjectName("secondaryLabel")
    enhanced_form.addRow("Status:", self._enhanced_status)

    self._model_info = QLabel("")
    self._model_info.setObjectName("secondaryLabel")
    enhanced_form.addRow("Info:", self._model_info)

    self._cache_size = QLabel("Cache: 0 MB")
    self._cache_size.setObjectName("secondaryLabel")
    enhanced_form.addRow("Size:", self._cache_size)

    # Buttons in two rows for small screens
    enhanced_btns1 = QHBoxLayout()
    self._download_model = QPushButton("Download Model (90 MB)")
    self._download_model.clicked.connect(self._on_download_model)
    self._download_model.setMinimumWidth(120)
    enhanced_btns1.addWidget(self._download_model)
    enhanced_btns1.addStretch()
    enhanced_form.addRow("", enhanced_btns1)

    enhanced_btns2 = QHBoxLayout()
    self._rebuild_cache = QPushButton("Rebuild Embeddings")
    self._rebuild_cache.clicked.connect(self._on_rebuild_cache)
    self._rebuild_cache.setMinimumWidth(120)
    self._clear_learning = QPushButton("Clear Learning Data")
    self._clear_learning.clicked.connect(self._on_clear_learning)
    self._clear_learning.setMinimumWidth(120)
    enhanced_btns2.addWidget(self._rebuild_cache)
    enhanced_btns2.addWidget(self._clear_learning)
    enhanced_btns2.addStretch()
    enhanced_form.addRow("", enhanced_btns2)

    layout.addWidget(enhanced_group)
    layout.addStretch()

    scroll.setWidget(content_widget)
    outer_layout.addWidget(scroll)

  def _load_values(self) -> None:
    self._kaggle_user.setText(self._store.kaggle_username())
    if self._store.kaggle_username():
      self._kaggle_status.setText(f"Saved for user: {self._store.kaggle_username()}")
    self._github_token.setText(self._store.github_token())
    if self._store.github_token():
      self._github_status.setText("Token saved — enhanced rate limits active")
    self._hf_token.setText(self._store.huggingface_token())
    if self._store.huggingface_token():
      self._hf_status.setText("Token saved — private/gated datasets enabled")
    self._india_key.setText(self._store.india_api_key())

  def _save_kaggle(self) -> None:
    self._store.save_kaggle(self._kaggle_user.text(), self._kaggle_key.text())
    self._kaggle_status.setText(f"Saved for user: {self._kaggle_user.text() or '—'}")
    self.credentials_changed.emit()
    QMessageBox.information(self, "Saved", "Kaggle credentials saved securely.")

  def _save_github(self) -> None:
    self._store.save_github(self._github_token.text())
    status = "Token saved" if self._github_token.text() else "Cleared"
    self._github_status.setText(f"{status} — public search always available")
    self.credentials_changed.emit()

  def _save_hf(self) -> None:
    self._store.save_huggingface(self._hf_token.text())
    self._hf_status.setText(
      "Token saved" if self._hf_token.text() else "Cleared — public datasets available"
    )
    self.credentials_changed.emit()

  def _save_india(self) -> None:
    self._store.save_india(self._india_key.text())
    self.credentials_changed.emit()
    QMessageBox.information(self, "Saved", "India API key saved (optional enhancement).")

  def _test_kaggle(self) -> None:
    user = self._kaggle_user.text().strip()
    key = self._kaggle_key.text().strip()
    if not user or not key:
      QMessageBox.warning(self, "Kaggle", "Enter username and API key to test.")
      return
    self._kaggle_status.setText("Testing...")
    try:
      resp = httpx.get(
        "https://www.kaggle.com/api/v1/datasets/list",
        params={"pageSize": 1},
        auth=(user, key),
        timeout=15,
      )
      if resp.status_code == 200 and "json" in resp.headers.get("content-type", ""):
        self._kaggle_status.setText(f"✓ Connected as {user}")
        self._store.save_kaggle(user, key)
        self.credentials_changed.emit()
      else:
        self._kaggle_status.setText("✗ Connection failed — check credentials")
        QMessageBox.warning(self, "Kaggle", "Could not validate credentials.")
    except Exception as e:
      self._kaggle_status.setText("✗ Connection error")
      QMessageBox.warning(self, "Kaggle", f"Connection failed: {e}")

  def set_databrain(self, databrain) -> None:
    """Set DatasetBrain instance and update UI."""
    self._databrain = databrain
    self._refresh_enhanced_search_status()

  def _refresh_enhanced_search_status(self) -> None:
    """Update Enhanced Search UI with current status."""
    if not hasattr(self, "_databrain") or self._databrain is None:
      self._enhanced_status.setText("DatasetBrain not available")
      return

    status = self._databrain.model_manager.get_model_status()
    if status["installed"]:
      self._enhanced_status.setText("Installed ✓")
      size_mb = status.get("size_mb", 90)
      self._model_info.setText(f"all-MiniLM-L6-v2 ({size_mb:.0f} MB)")
      self._download_model.setEnabled(False)
    else:
      self._enhanced_status.setText("Not installed")
      self._model_info.setText("Download to enable semantic search")
      self._download_model.setEnabled(True)

    cache_stats = self._databrain.embeddings_cache.stats()
    self._cache_size.setText(
      f"Cache: {cache_stats['total_size_mb']:.1f} MB ({cache_stats['total_cached']} datasets)"
    )

  def _on_download_model(self) -> None:
    """Download the embedding model."""
    if not hasattr(self, "_databrain"):
      QMessageBox.warning(self, "Error", "DatasetBrain not available")
      return

    self._download_model.setEnabled(False)
    self._enhanced_status.setText("Downloading...")

    def progress_callback(msg: str, pct: float) -> None:
      self._enhanced_status.setText(f"{msg} {int(pct)}%")

    success = self._databrain.model_manager.download_model(progress_callback)

    if success:
      self._refresh_enhanced_search_status()
      QMessageBox.information(
        self, "Success", "Embedding model downloaded successfully!"
      )
    else:
      self._enhanced_status.setText("Download failed")
      QMessageBox.warning(
        self,
        "Error",
        "Failed to download model. Check internet connection and try again.",
      )

  def _on_rebuild_cache(self) -> None:
    """Rebuild embeddings cache."""
    reply = QMessageBox.question(
      self,
      "Rebuild Cache",
      "Regenerate all dataset embeddings? This may take a few minutes.",
      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
    )
    if reply == QMessageBox.StandardButton.Yes:
      self._databrain.embeddings_cache.clear()
      self._refresh_enhanced_search_status()
      QMessageBox.information(self, "Cache Cleared", "Embeddings will be regenerated on next search.")

  def _on_clear_learning(self) -> None:
    """Clear user behavior database."""
    reply = QMessageBox.question(
      self,
      "Clear Learning Data",
      "Delete all search history, clicks, and learning data? Cannot be undone.",
      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
    )
    if reply == QMessageBox.StandardButton.Yes:
      self._databrain.behavior_tracker.clear_all()
      QMessageBox.information(self, "Data Cleared", "Learning data has been deleted.")
