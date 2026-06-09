"""Enumerations for Dataset_Collector."""

from enum import Enum, auto


class DataSource(str, Enum):
    KAGGLE = "Kaggle"
    GITHUB = "GitHub"
    HUGGINGFACE = "HuggingFace"
    GOVERNMENT = "Government Data"
    RESEARCH = "Research Sources"
    INTERNET_ARCHIVE = "Internet Archive"
    GOOGLE_DATASET = "Google Dataset Search"


class FileType(str, Enum):
    CSV = "CSV"
    JSON = "JSON"
    XLSX = "XLSX"
    IMAGES = "Images"
    VIDEOS = "Videos"
    AUDIO = "Audio"
    ZIP = "ZIP"
    TAR = "TAR"
    PARQUET = "Parquet"
    ANY = "Any"


class LicenseFilter(str, Enum):
    OPEN_SOURCE = "Open Source"
    COMMERCIAL = "Commercial Use"
    RESEARCH_ONLY = "Research Only"
    ANY = "Any"


class SizeFilter(str, Enum):
    ANY = "Any"
    MAX_SIZE = "Maximum Size"


class DownloadStatus(str, Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ManifestFormat(str, Enum):
    TXT = "txt"
    JSON = "json"


class LogCategory(str, Enum):
    SEARCH = "search"
    DOWNLOAD = "download"
    ERROR = "error"
    ANALYSIS = "analysis"
    MANIFEST = "manifest"
