"""Encrypted local credential storage."""

from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken


class CredentialStore:
  """Stores API credentials encrypted at rest. Never logs or exposes secrets."""

  SERVICE = "dataset_collector"
  _KEY_FILE = ".cred_key"

  def __init__(self, config_dir: Path | None = None) -> None:
    self._dir = config_dir or Path.home() / ".dataset_collector"
    self._dir.mkdir(parents=True, exist_ok=True)
    self._cred_file = self._dir / "credentials.enc"
    self._fernet = Fernet(self._get_or_create_key())

  def _get_or_create_key(self) -> bytes:
    key_path = self._dir / self._KEY_FILE
    if key_path.exists():
      return key_path.read_bytes()
    seed = f"{self.SERVICE}:{os.environ.get('USERNAME', '')}:{os.environ.get('COMPUTERNAME', '')}"
    digest = hashlib.sha256(seed.encode()).digest()
    key = base64.urlsafe_b64encode(digest)
    key_path.write_bytes(key)
    try:
      os.chmod(key_path, 0o600)
    except OSError:
      pass
    return key

  def _load(self) -> dict[str, str]:
    if not self._cred_file.exists():
      return {}
    try:
      raw = self._fernet.decrypt(self._cred_file.read_bytes())
      data = json.loads(raw.decode())
      return {k: str(v) for k, v in data.items() if v}
    except (InvalidToken, json.JSONDecodeError, OSError):
      return {}

  def _save(self, data: dict[str, str]) -> None:
    payload = json.dumps(data).encode()
    self._cred_file.write_bytes(self._fernet.encrypt(payload))
    try:
      os.chmod(self._cred_file, 0o600)
    except OSError:
      pass

  def get(self, key: str) -> str:
    return self._load().get(key, "")

  def set(self, key: str, value: str) -> None:
    data = self._load()
    if value:
      data[key] = value
    elif key in data:
      del data[key]
    self._save(data)

  def get_all_masked(self) -> dict[str, str]:
    return {k: self._mask(v) for k, v in self._load().items()}

  def clear(self) -> None:
    if self._cred_file.exists():
      self._cred_file.unlink()

  @staticmethod
  def _mask(value: str) -> str:
    if len(value) <= 4:
      return "****"
    return value[:2] + "*" * (len(value) - 4) + value[-2:]

  # Convenience accessors
  def kaggle_username(self) -> str:
    return self.get("kaggle_username")

  def kaggle_key(self) -> str:
    return self.get("kaggle_key")

  def github_token(self) -> str:
    return self.get("github_token")

  def huggingface_token(self) -> str:
    return self.get("huggingface_token")

  def india_api_key(self) -> str:
    return self.get("india_data_api_key")

  def save_kaggle(self, username: str, api_key: str) -> None:
    self.set("kaggle_username", username.strip())
    self.set("kaggle_key", api_key.strip())

  def save_github(self, token: str) -> None:
    self.set("github_token", token.strip())

  def save_huggingface(self, token: str) -> None:
    self.set("huggingface_token", token.strip())

  def save_india(self, api_key: str) -> None:
    self.set("india_data_api_key", api_key.strip())
