"""Configuration management for Dataset_Collector."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


class ConfigManager:
  """Loads and manages application configuration."""

  def __init__(self, config_path: Path | None = None) -> None:
    self._config_path = config_path or self._default_config_path()
    self._config: dict[str, Any] = {}
    self.load()

  @staticmethod
  def _default_config_path() -> Path:
    candidates = [
      Path.home() / ".dataset_collector" / "config.yaml",
      Path(__file__).resolve().parents[1] / "config" / "default_config.yaml",
      Path(__file__).resolve().parents[3] / "config" / "default_config.yaml",
    ]
    for path in candidates:
      if path.exists():
        return path
    return candidates[1]

  def load(self) -> None:
    with open(self._config_path, encoding="utf-8") as f:
      self._config = yaml.safe_load(f) or {}
    self._expand_paths()
    self._ensure_directories()

  def _expand_paths(self) -> None:
    paths = self._config.get("paths", {})
    for key, value in paths.items():
      if isinstance(value, str):
        paths[key] = str(Path(value).expanduser().resolve())

  def _ensure_directories(self) -> None:
    for key in ("download_dir", "manifest_dir", "library_dir", "logs_dir"):
      path = self.get_path(key)
      Path(path).mkdir(parents=True, exist_ok=True)

  def get(self, *keys: str, default: Any = None) -> Any:
    node: Any = self._config
    for key in keys:
      if not isinstance(node, dict):
        return default
      node = node.get(key, default)
      if node is default:
        return default
    return node

  def get_path(self, key: str) -> str:
    return self.get("paths", key, default="")

  def set(self, *keys: str, value: Any) -> None:
    node = self._config
    for key in keys[:-1]:
      node = node.setdefault(key, {})
    node[keys[-1]] = value

  def save(self) -> None:
    user_config = Path.home() / ".dataset_collector" / "config.yaml"
    user_config.parent.mkdir(parents=True, exist_ok=True)
    with open(user_config, "w", encoding="utf-8") as f:
      yaml.safe_dump(self._config, f, default_flow_style=False)

  @property
  def download_dir(self) -> Path:
    return Path(self.get_path("download_dir"))

  @property
  def manifest_dir(self) -> Path:
    return Path(self.get_path("manifest_dir"))

  @property
  def library_dir(self) -> Path:
    return Path(self.get_path("library_dir"))

  @property
  def logs_dir(self) -> Path:
    return Path(self.get_path("logs_dir"))

  def get_api_key(self, service: str) -> str:
    env_map = {
      "kaggle_username": "KAGGLE_USERNAME",
      "kaggle_key": "KAGGLE_KEY",
      "github_token": "GITHUB_TOKEN",
      "huggingface_token": "HF_TOKEN",
      "india_data_api_key": "DATA_GOV_IN_API_KEY",
    }
    env_var = env_map.get(service, "")
    if env_var:
      env_value = os.environ.get(env_var, "")
      if env_value:
        return env_value
    return self.get("api_keys", service, default="")
