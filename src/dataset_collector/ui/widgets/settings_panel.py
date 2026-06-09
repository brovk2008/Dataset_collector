"""Application settings and authentication panel."""

from __future__ import annotations

import asyncio

import httpx
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
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
    layout = QVBoxLayout(self)

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
    self._gov_status = QLabel("✓ Public access mode enabled — no API key required")
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

    layout.addStretch()

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
