"""Multi-threaded download engine with pause/resume/cancel support."""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

import aiofiles
import httpx

from dataset_collector.core.config_manager import ConfigManager
from dataset_collector.core.credential_store import CredentialStore
from dataset_collector.core.enums import DataSource, DownloadStatus
from dataset_collector.core.models import DatasetResult, DownloadTask
from dataset_collector.logging.logger import AppLogger

KAGGLE_AUTH_MSG = (
  "This dataset requires Kaggle authentication. "
  "Connect your Kaggle account in Settings to enable downloading."
)

BROWSER_HEADERS = {
  "User-Agent": (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
  ),
}


class DownloadEngine:
  """Manages concurrent dataset downloads with queue control."""

  def __init__(
    self,
    config: ConfigManager,
    logger: AppLogger,
    credential_store: CredentialStore | None = None,
  ) -> None:
    self._config = config
    self._logger = logger
    self._creds = credential_store or CredentialStore()
    self._tasks: dict[str, DownloadTask] = {}
    self._paused = False
    self._cancelled = False
    self._max_concurrent = config.get("download", "max_concurrent", default=4)
    self._chunk_size = config.get("download", "chunk_size", default=8192)
    self._retry_attempts = config.get("download", "retry_attempts", default=3)
    self._timeout = config.get("download", "timeout_seconds", default=300)

  def pause(self) -> None:
    self._paused = True
    for task in self._tasks.values():
      if task.status == DownloadStatus.DOWNLOADING:
        task.status = DownloadStatus.PAUSED

  def resume(self) -> None:
    self._paused = False
    for task in self._tasks.values():
      if task.status == DownloadStatus.PAUSED:
        task.status = DownloadStatus.PENDING

  def cancel(self) -> None:
    self._cancelled = True
    for task in self._tasks.values():
      if task.status in (DownloadStatus.DOWNLOADING, DownloadStatus.PENDING, DownloadStatus.PAUSED):
        task.status = DownloadStatus.CANCELLED

  def get_tasks(self) -> list[DownloadTask]:
    return list(self._tasks.values())

  def get_task(self, dataset_id: str) -> DownloadTask | None:
    return self._tasks.get(dataset_id)

  async def download_datasets(
    self,
    datasets: list[DatasetResult],
    progress_callback: Callable[[DownloadTask], None] | None = None,
  ) -> list[DownloadTask]:
    self._paused = False
    self._cancelled = False

    for ds in datasets:
      self._tasks[ds.id] = DownloadTask(dataset=ds)

    semaphore = asyncio.Semaphore(self._max_concurrent)
    coros = [self._download_one(ds, semaphore, progress_callback) for ds in datasets]
    await asyncio.gather(*coros, return_exceptions=True)
    return list(self._tasks.values())

  async def retry_failed(
    self,
    progress_callback: Callable[[DownloadTask], None] | None = None,
  ) -> list[DownloadTask]:
    failed = [t.dataset for t in self._tasks.values() if t.status == DownloadStatus.FAILED]
    for ds in failed:
      self._tasks[ds.id] = DownloadTask(dataset=ds)
    return await self.download_datasets(failed, progress_callback)

  async def _download_one(
    self,
    dataset: DatasetResult,
    semaphore: asyncio.Semaphore,
    progress_callback: Callable[[DownloadTask], None] | None,
  ) -> None:
    async with semaphore:
      task = self._tasks[dataset.id]
      if self._cancelled:
        task.status = DownloadStatus.CANCELLED
        return

      task.status = DownloadStatus.DOWNLOADING
      safe_name = _sanitize_filename(dataset.name)
      dest_dir = self._config.download_dir / safe_name
      dest_dir.mkdir(parents=True, exist_ok=True)
      task.local_path = str(dest_dir)

      try:
        await self._wait_if_paused()

        if dataset.metadata.get("content_type") == "paper" or dataset.source == DataSource.RESEARCH_PAPERS:
          await self._download_research_paper(dataset, task, dest_dir, progress_callback)
        elif dataset.source == DataSource.KAGGLE:
          await self._download_kaggle(dataset, task, dest_dir, progress_callback)
        elif dataset.source == DataSource.HUGGINGFACE:
          await self._download_huggingface(dataset, task, dest_dir, progress_callback)
        elif dataset.source == DataSource.GITHUB and dataset.metadata.get("full_name"):
          await self._download_github_repo(dataset, task, dest_dir, progress_callback)
        elif dataset.download_urls:
          await self._download_url_list(dataset.download_urls, task, dest_dir, progress_callback)
        elif dataset.files and _urls_look_valid(dataset.files):
          await self._download_url_list(dataset.files, task, dest_dir, progress_callback)
        else:
          dest_file = dest_dir / f"{safe_name}.zip"
          await self._download_url(dataset.url, task, dest_file, progress_callback)

        if task.status != DownloadStatus.CANCELLED:
          task.status = DownloadStatus.COMPLETED
          task.progress_percent = 100.0
          self._logger.log_download(dataset.name, "completed", path=task.local_path)
      except Exception as e:
        task.status = DownloadStatus.FAILED
        err = str(e)
        if dataset.source == DataSource.KAGGLE and ("401" in err or "403" in err or "auth" in err.lower()):
          err = KAGGLE_AUTH_MSG
          dataset.requires_auth = True
          dataset.auth_message = KAGGLE_AUTH_MSG
        task.error_message = err
        task.failed_files += 1
        self._logger.log_download(dataset.name, "failed", error=err)
        self._logger.error(f"Download failed: {dataset.name}", error=err)

      if progress_callback:
        progress_callback(task)

  async def _download_research_paper(
    self,
    dataset: DatasetResult,
    task: DownloadTask,
    dest_dir: Path,
    progress_callback: Callable[[DownloadTask], None] | None,
  ) -> None:
    urls = [u for u in dataset.download_urls if u.startswith("http")]
    if not urls and dataset.metadata.get("arxiv_id"):
      urls = [f"https://arxiv.org/pdf/{dataset.metadata['arxiv_id']}.pdf"]

    meta = {
      "title": dataset.name,
      "source": dataset.source.value,
      "url": dataset.url,
      "license": dataset.license_info,
      "authors": dataset.metadata.get("authors", []),
      "doi": dataset.metadata.get("doi", ""),
      "abstract": dataset.metadata.get("abstract", dataset.description),
      "provider": dataset.metadata.get("provider", ""),
      "arxiv_id": dataset.metadata.get("arxiv_id", ""),
    }
    (dest_dir / "paper_metadata.json").write_text(
      json.dumps(meta, indent=2, ensure_ascii=False),
      encoding="utf-8",
    )

    if not urls:
      raise ValueError("No downloadable PDF found for this paper")

    total = len(urls)
    for i, url in enumerate(urls):
      if self._cancelled:
        task.status = DownloadStatus.CANCELLED
        return
      filename = Path(urlparse(url).path).name or f"paper_{i + 1}.pdf"
      if not filename.lower().endswith(".pdf"):
        filename = f"{_sanitize_filename(dataset.name)}.pdf"
      try:
        await self._download_url(url, task, dest_dir / filename, progress_callback, extra_headers=BROWSER_HEADERS)
        task.downloaded_files += 1
      except Exception:
        task.failed_files += 1
      task.progress_percent = (i + 1) / total * 100
      if progress_callback:
        progress_callback(task)

  async def _download_kaggle(
    self,
    dataset: DatasetResult,
    task: DownloadTask,
    dest_dir: Path,
    progress_callback: Callable[[DownloadTask], None] | None,
  ) -> None:
    ref = dataset.metadata.get("ref", "")
    username = self._creds.kaggle_username() or self._config.get_api_key("kaggle_username")
    api_key = self._creds.kaggle_key() or self._config.get_api_key("kaggle_key")

    if ref and username and api_key:
      await self._download_kaggle_sdk(ref, dest_dir, task, progress_callback)
      return

    url = dataset.metadata.get("download_url") or (
      f"https://www.kaggle.com/api/v1/datasets/download/{ref}" if ref else dataset.url
    )
    dest = dest_dir / f"{_sanitize_filename(dataset.name)}.zip"
    await self._download_url(url, task, dest, progress_callback, extra_headers=BROWSER_HEADERS)

  async def _download_kaggle_sdk(
    self,
    ref: str,
    dest_dir: Path,
    task: DownloadTask,
    progress_callback: Callable[[DownloadTask], None] | None,
  ) -> None:
    def _do_download() -> None:
      from kaggle.api.kaggle_api_extended import KaggleApi

      api = KaggleApi()
      api.authenticate()
      api.dataset_download_files(ref, path=str(dest_dir), unzip=True, quiet=False)

    await asyncio.to_thread(_do_download)
    task.progress_percent = 100.0
    task.downloaded_files = max(1, len(list(dest_dir.rglob("*"))))
    if progress_callback:
      progress_callback(task)

  async def _download_huggingface(
    self,
    dataset: DatasetResult,
    task: DownloadTask,
    dest_dir: Path,
    progress_callback: Callable[[DownloadTask], None] | None,
  ) -> None:
    dataset_id = dataset.metadata.get("dataset_id", dataset.name)
    base = f"https://huggingface.co/datasets/{dataset_id}/resolve/main/"
    headers = dict(BROWSER_HEADERS)
    token = self._creds.huggingface_token() or self._config.get_api_key("huggingface_token")
    if token:
      headers["Authorization"] = f"Bearer {token}"

    async with httpx.AsyncClient(timeout=30, headers=headers) as client:
      resp = await client.get(f"https://huggingface.co/api/datasets/{dataset_id}/tree/main?recursive=1")
      resp.raise_for_status()
      tree = resp.json()

    file_paths = [
      item["path"]
      for item in tree
      if item.get("type") == "file" and not item["path"].startswith(".")
    ]
    if not file_paths:
      raise ValueError("No downloadable files found on Hugging Face")

    total = len(file_paths)
    for i, path in enumerate(file_paths):
      if self._cancelled:
        task.status = DownloadStatus.CANCELLED
        return
      url = base + path
      dest = dest_dir / path
      try:
        await self._download_url(url, task, dest, progress_callback, extra_headers=headers)
        task.downloaded_files += 1
      except Exception:
        task.failed_files += 1
      task.progress_percent = (i + 1) / total * 100
      if progress_callback:
        progress_callback(task)

  async def _wait_if_paused(self) -> None:
    while self._paused and not self._cancelled:
      await asyncio.sleep(0.5)

  async def _download_url_list(
    self,
    urls: list[str],
    task: DownloadTask,
    dest_dir: Path,
    progress_callback: Callable[[DownloadTask], None] | None,
  ) -> None:
    total = len(urls)
    for i, url in enumerate(urls):
      if self._cancelled:
        task.status = DownloadStatus.CANCELLED
        return
      if not url.startswith("http"):
        continue
      filename = Path(urlparse(url).path).name or f"file_{i}"
      try:
        await self._download_url(url, task, dest_dir / filename, progress_callback)
        task.downloaded_files += 1
      except Exception:
        task.failed_files += 1
      task.progress_percent = (i + 1) / total * 100
      if progress_callback:
        progress_callback(task)

  async def _download_url(
    self,
    url: str,
    task: DownloadTask,
    dest_path: Path,
    progress_callback: Callable[[DownloadTask], None] | None,
    extra_headers: dict | None = None,
  ) -> None:
    headers = dict(BROWSER_HEADERS)
    if extra_headers:
      headers.update(extra_headers)

    for attempt in range(self._retry_attempts):
      if self._cancelled:
        task.status = DownloadStatus.CANCELLED
        return
      try:
        await self._wait_if_paused()
        async with httpx.AsyncClient(timeout=self._timeout, follow_redirects=True) as client:
          async with client.stream("GET", url, headers=headers) as resp:
            resp.raise_for_status()
            total = int(resp.headers.get("content-length", 0)) or None
            task.total_bytes = total
            downloaded = 0
            start_time = time.monotonic()

            dest_path.parent.mkdir(parents=True, exist_ok=True)
            async with aiofiles.open(dest_path, "wb") as f:
              async for chunk in resp.aiter_bytes(self._chunk_size):
                if self._cancelled:
                  task.status = DownloadStatus.CANCELLED
                  return
                await self._wait_if_paused()
                await f.write(chunk)
                downloaded += len(chunk)
                task.downloaded_bytes = downloaded
                elapsed = time.monotonic() - start_time
                if elapsed > 0:
                  task.speed_bps = downloaded / elapsed
                if total:
                  task.progress_percent = downloaded / total * 100
                if progress_callback:
                  progress_callback(task)
        return
      except Exception:
        if attempt < self._retry_attempts - 1:
          await asyncio.sleep(self._config.get("download", "retry_delay_seconds", default=5))
        else:
          raise

  async def _download_github_repo(
    self,
    dataset: DatasetResult,
    task: DownloadTask,
    dest_dir: Path,
    progress_callback: Callable[[DownloadTask], None] | None,
  ) -> None:
    full_name = dataset.metadata.get("full_name", "")
    zip_url = f"https://github.com/{full_name}/archive/refs/heads/main.zip"
    try:
      await self._download_url(zip_url, task, dest_dir / f"{dataset.name}.zip", progress_callback)
    except Exception:
      zip_url = f"https://github.com/{full_name}/archive/refs/heads/master.zip"
      await self._download_url(zip_url, task, dest_dir / f"{dataset.name}.zip", progress_callback)


def _sanitize_filename(name: str) -> str:
  invalid = '<>:"/\\|?*'
  for ch in invalid:
    name = name.replace(ch, "_")
  return name[:200].strip() or "dataset"


def _urls_look_valid(urls: list[str]) -> bool:
  return bool(urls) and all(u.startswith("http") for u in urls[:3])
