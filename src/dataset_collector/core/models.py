"""Core data models for Dataset_Collector."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from dataset_collector.core.enums import (
    DataSource,
    DownloadStatus,
    FileType,
    LicenseFilter,
    SizeFilter,
)


@dataclass
class SearchFilters:
    file_types: list[FileType] = field(default_factory=lambda: [FileType.ANY])
    custom_types: list[str] = field(default_factory=list)
    country: str = "Worldwide"
    region: str = ""
    size_filter: SizeFilter = SizeFilter.ANY
    max_size_bytes: int | None = None
    license_filter: LicenseFilter = LicenseFilter.ANY


@dataclass
class SearchRequest:
    query: str
    sources: list[DataSource]
    filters: SearchFilters = field(default_factory=SearchFilters)


@dataclass
class DatasetResult:
    id: str
    name: str
    source: DataSource
    url: str
    estimated_size_bytes: int | None = None
    file_count: int | None = None
    license_info: str = "Unknown"
    last_updated: datetime | None = None
    description: str = ""
    files: list[str] = field(default_factory=list)
    download_urls: list[str] = field(default_factory=list)
    relevance_score: float = 0.0
    quality_score: float = 0.0
    rank_score: int = 0
    semantic_score: float = 0.0
    click_score: float = 0.0
    health_score: int = 0
    available_sources: list[str] = field(default_factory=list)
    requires_auth: bool = False
    auth_message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def size_display(self) -> str:
        if self.estimated_size_bytes is None:
            return "Unknown"
        return _format_bytes(self.estimated_size_bytes)


@dataclass
class DownloadTask:
    dataset: DatasetResult
    status: DownloadStatus = DownloadStatus.PENDING
    progress_percent: float = 0.0
    downloaded_bytes: int = 0
    total_bytes: int | None = None
    speed_bps: float = 0.0
    downloaded_files: int = 0
    failed_files: int = 0
    error_message: str = ""
    local_path: str = ""


@dataclass
class ManifestEntry:
    dataset_name: str
    source: str
    url: str
    size: str
    files: list[str]
    license: str
    timestamp: str


@dataclass
class CsvProfile:
    rows: int
    columns: int
    missing_values: int
    duplicate_percentage: float
    column_names: list[str]


@dataclass
class ImageProfile:
    image_count: int
    resolutions: dict[str, int]


@dataclass
class TextProfile:
    character_count: int
    word_count: int
    detected_language: str


@dataclass
class DatasetProfile:
    dataset_name: str
    dataset_type: str
    file_count: int
    total_size_bytes: int
    detected_formats: list[str]
    csv_profile: CsvProfile | None = None
    image_profile: ImageProfile | None = None
    text_profile: TextProfile | None = None


@dataclass
class LibraryEntry:
    id: str
    name: str
    source: str
    local_path: str
    size_bytes: int
    downloaded_at: datetime
    file_count: int
    metadata: dict[str, Any] = field(default_factory=dict)


def _format_bytes(size: int) -> str:
    size_float = float(size)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size_float < 1024:
            return f"{size_float:.1f} {unit}" if unit != "B" else f"{int(size_float)} B"
        size_float /= 1024
    return f"{size_float:.1f} PB"
