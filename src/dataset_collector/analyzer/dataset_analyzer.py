"""Dataset profiling and analysis."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pandas as pd
from langdetect import detect, LangDetectException
from PIL import Image

from dataset_collector.core.models import (
    CsvProfile,
    DatasetProfile,
    ImageProfile,
    TextProfile,
)
from dataset_collector.logging.logger import AppLogger

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"}
TEXT_EXTENSIONS = {".txt", ".md", ".csv", ".json", ".jsonl"}
CSV_EXTENSIONS = {".csv", ".tsv"}


class DatasetAnalyzer:
  """Analyzes downloaded datasets and generates profiles."""

  def __init__(self, logger: AppLogger) -> None:
    self._logger = logger

  def analyze(self, dataset_path: str, dataset_name: str = "") -> DatasetProfile:
    path = Path(dataset_path)
    if not path.exists():
      raise FileNotFoundError(f"Dataset path not found: {dataset_path}")

    name = dataset_name or path.name
    all_files = list(path.rglob("*")) if path.is_dir() else [path]
    files = [f for f in all_files if f.is_file()]

    total_size = sum(f.stat().st_size for f in files)
    extensions = Counter(f.suffix.lower() for f in files if f.suffix)
    detected_formats = [ext.lstrip(".") for ext, _ in extensions.most_common(10)]

    dataset_type = self._infer_type(extensions)
    csv_profile = self._analyze_csv(files) if dataset_type in ("tabular", "mixed") else None
    image_profile = self._analyze_images(files) if dataset_type in ("images", "mixed") else None
    text_profile = self._analyze_text(files) if dataset_type in ("text", "mixed") else None

    profile = DatasetProfile(
      dataset_name=name,
      dataset_type=dataset_type,
      file_count=len(files),
      total_size_bytes=total_size,
      detected_formats=detected_formats,
      csv_profile=csv_profile,
      image_profile=image_profile,
      text_profile=text_profile,
    )

    self._logger.log_analysis(name, self._profile_to_dict(profile))
    return profile

  def generate_report(self, profile: DatasetProfile, output_path: str | None = None) -> str:
    lines = [
      f"Dataset Analysis Report: {profile.dataset_name}",
      "=" * 60,
      f"Type: {profile.dataset_type}",
      f"File Count: {profile.file_count}",
      f"Total Size: {_format_bytes(profile.total_size_bytes)}",
      f"Detected Formats: {', '.join(profile.detected_formats) or 'None'}",
      "",
    ]

    if profile.csv_profile:
      cp = profile.csv_profile
      lines.extend([
        "CSV Analysis:",
        f"  Rows: {cp.rows:,}",
        f"  Columns: {cp.columns}",
        f"  Missing Values: {cp.missing_values:,}",
        f"  Duplicate Percentage: {cp.duplicate_percentage:.2f}%",
        "",
      ])

    if profile.image_profile:
      ip = profile.image_profile
      lines.extend([
        "Image Analysis:",
        f"  Image Count: {ip.image_count}",
        "  Resolution Distribution:",
      ])
      for res, count in sorted(ip.resolutions.items(), key=lambda x: -x[1])[:10]:
        lines.append(f"    {res}: {count}")
      lines.append("")

    if profile.text_profile:
      tp = profile.text_profile
      lines.extend([
        "Text Analysis:",
        f"  Character Count: {tp.character_count:,}",
        f"  Word Count: {tp.word_count:,}",
        f"  Detected Language: {tp.detected_language}",
        "",
      ])

    report = "\n".join(lines)
    if output_path:
      Path(output_path).write_text(report, encoding="utf-8")
    return report

  def _infer_type(self, extensions: Counter) -> str:
    ext_set = set(extensions.keys())
    has_images = bool(ext_set & IMAGE_EXTENSIONS)
    has_csv = bool(ext_set & CSV_EXTENSIONS)
    has_text = bool(ext_set & TEXT_EXTENSIONS)
    types_found = sum([has_images, has_csv, has_text])
    if types_found > 1:
      return "mixed"
    if has_images:
      return "images"
    if has_csv:
      return "tabular"
    if has_text:
      return "text"
    return "unknown"

  def _analyze_csv(self, files: list[Path]) -> CsvProfile | None:
    csv_files = [f for f in files if f.suffix.lower() in CSV_EXTENSIONS]
    if not csv_files:
      return None
    try:
      df = pd.read_csv(csv_files[0], nrows=100000, low_memory=False)
      missing = int(df.isnull().sum().sum())
      dup_pct = (df.duplicated().sum() / len(df) * 100) if len(df) > 0 else 0.0
      return CsvProfile(
        rows=len(df),
        columns=len(df.columns),
        missing_values=missing,
        duplicate_percentage=round(dup_pct, 2),
        column_names=list(df.columns[:50]),
      )
    except Exception:
      return None

  def _analyze_images(self, files: list[Path]) -> ImageProfile | None:
    image_files = [f for f in files if f.suffix.lower() in IMAGE_EXTENSIONS]
    if not image_files:
      return None
    resolutions: Counter[str] = Counter()
    for img_path in image_files[:500]:
      try:
        with Image.open(img_path) as img:
          resolutions[f"{img.width}x{img.height}"] += 1
      except Exception:
        continue
    return ImageProfile(image_count=len(image_files), resolutions=dict(resolutions))

  def _analyze_text(self, files: list[Path]) -> TextProfile | None:
    text_files = [f for f in files if f.suffix.lower() in {".txt", ".md", ".json", ".jsonl"}]
    if not text_files:
      return None
    sample = ""
    char_count = 0
    for tf in text_files[:5]:
      try:
        content = tf.read_text(encoding="utf-8", errors="ignore")
        char_count += len(content)
        if len(sample) < 5000:
          sample += content[:5000 - len(sample)]
      except Exception:
        continue
    language = "unknown"
    if sample.strip():
      try:
        language = detect(sample[:5000])
      except LangDetectException:
        pass
    word_count = len(sample.split()) if sample.strip() else 0
    return TextProfile(character_count=char_count, word_count=word_count, detected_language=language)

  def _profile_to_dict(self, profile: DatasetProfile) -> dict:
    d = {
      "dataset_name": profile.dataset_name,
      "dataset_type": profile.dataset_type,
      "file_count": profile.file_count,
      "total_size_bytes": profile.total_size_bytes,
      "detected_formats": profile.detected_formats,
    }
    if profile.csv_profile:
      d["csv"] = {
        "rows": profile.csv_profile.rows,
        "columns": profile.csv_profile.columns,
        "missing_values": profile.csv_profile.missing_values,
        "duplicate_percentage": profile.csv_profile.duplicate_percentage,
      }
    if profile.image_profile:
      d["images"] = {
        "count": profile.image_profile.image_count,
        "resolutions": profile.image_profile.resolutions,
      }
    if profile.text_profile:
      d["text"] = {
        "character_count": profile.text_profile.character_count,
        "language": profile.text_profile.detected_language,
      }
    return d


def _format_bytes(size: int) -> str:
  size_float = float(size)
  for unit in ("B", "KB", "MB", "GB", "TB"):
    if size_float < 1024:
      return f"{size_float:.1f} {unit}" if unit != "B" else f"{int(size_float)} B"
    size_float /= 1024
  return f"{size_float:.1f} PB"
