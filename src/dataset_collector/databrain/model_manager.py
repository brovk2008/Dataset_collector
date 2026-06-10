"""Manages sentence-transformers model download and lifecycle."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from sentence_transformers import SentenceTransformer

from dataset_collector.core.config_manager import ConfigManager
from dataset_collector.logging.logger import AppLogger


class ModelManager:
  """Download, load, and cache sentence-transformers embeddings model."""

  MODEL_NAME = "all-MiniLM-L6-v2"
  MODEL_SIZE_MB = 90
  EMBEDDING_DIM = 384

  def __init__(
    self,
    config: ConfigManager,
    logger: AppLogger,
    download_on_init: bool = False,
  ) -> None:
    self._config = config
    self._logger = logger
    self._cache_dir = Path.home() / ".dataset_collector" / "cache"
    self._cache_dir.mkdir(parents=True, exist_ok=True)
    self._model_path = self._cache_dir / "sentence-transformers" / self.MODEL_NAME
    self._model_instance: SentenceTransformer | None = None

    if download_on_init and not self.is_installed():
      self.download_model()

  def is_installed(self) -> bool:
    """Check if model is already downloaded."""
    return (self._model_path / "pytorch_model.bin").exists()

  def get_model_status(self) -> dict:
    """Return current model status."""
    if self.is_installed():
      size_bytes = sum(
        f.stat().st_size for f in self._model_path.rglob("*") if f.is_file()
      )
      size_mb = size_bytes / (1024 * 1024)
      return {
        "installed": True,
        "size_mb": size_mb,
        "path": str(self._model_path),
        "embedding_dim": self.EMBEDDING_DIM,
      }
    return {
      "installed": False,
      "size_mb": 0,
      "path": str(self._model_path),
      "embedding_dim": self.EMBEDDING_DIM,
    }

  def download_model(
    self, progress_callback: Callable[[str, float], None] | None = None
  ) -> bool:
    """Download model from Hugging Face."""
    try:
      if progress_callback:
        progress_callback("Downloading model...", 10.0)

      # SentenceTransformer will cache to our custom path automatically
      # via SENTENCE_TRANSFORMERS_HOME env var (set via config)
      SentenceTransformer(
        self.MODEL_NAME,
        cache_folder=str(self._cache_dir),
      )

      if progress_callback:
        progress_callback("Model downloaded successfully", 100.0)

      self._logger.info(f"Model downloaded: {self.MODEL_NAME}")
      return True
    except Exception as e:
      self._logger.error(
        f"Failed to download model: {e}",
        origin="ModelManager",
      )
      return False

  def get_encoder(self) -> SentenceTransformer:
    """Get or load model encoder instance."""
    if self._model_instance is None:
      if not self.is_installed():
        raise RuntimeError(
          "Model not installed. Call download_model() first or enable automatic download."
        )
      self._model_instance = SentenceTransformer(
        self.MODEL_NAME,
        cache_folder=str(self._cache_dir),
      )
    return self._model_instance

  def get_model_info(self) -> dict:
    """Return model metadata."""
    return {
      "name": self.MODEL_NAME,
      "embedding_dim": self.EMBEDDING_DIM,
      "typical_size_mb": self.MODEL_SIZE_MB,
      **self.get_model_status(),
    }

  def clear_cache(self) -> None:
    """Delete cached model files."""
    try:
      if self._model_path.exists():
        import shutil

        shutil.rmtree(self._model_path)
        self._model_instance = None
        self._logger.info("Model cache cleared")
    except Exception as e:
      self._logger.error(f"Failed to clear cache: {e}")
