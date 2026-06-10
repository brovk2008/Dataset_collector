"""Download status detection for datasets."""

from __future__ import annotations

from enum import Enum

from dataset_collector.core.models import DatasetResult


class DownloadStatus(Enum):
  """Dataset download availability status."""

  CAN_AUTO_DOWNLOAD = "auto"  # ✅ Direct URLs available
  MANUAL_DOWNLOAD = "manual"  # 🔗 Web link but no auto-download
  CHECK_AVAILABILITY = "check"  # ❓ Need to visit page
  CONTACT_REQUIRED = "contact"  # 📋 Signup/request form
  ACCESS_RESTRICTED = "restricted"  # ⚠️ Auth/approval needed


def detect_download_status(result: DatasetResult) -> DownloadStatus:
  """Detect dataset download status."""
  # Auto-download available
  if result.download_urls and len(result.download_urls) > 0:
    return DownloadStatus.CAN_AUTO_DOWNLOAD

  # Check for auth requirements
  if result.requires_auth:
    return DownloadStatus.ACCESS_RESTRICTED

  # Check for generic web URL
  if result.url and result.url.startswith("http"):
    # Check for indicators of restricted access
    url_lower = result.url.lower()
    if any(x in url_lower for x in ["login", "signin", "signup", "request", "contact"]):
      return DownloadStatus.CONTACT_REQUIRED

    # Check if it's a generic landing page
    if any(x in url_lower for x in ["github.com", "kaggle.com", "huggingface.co"]):
      return DownloadStatus.MANUAL_DOWNLOAD

    # Default to manual for web URLs
    return DownloadStatus.MANUAL_DOWNLOAD

  # No URL available
  return DownloadStatus.CHECK_AVAILABILITY


def get_status_display(status: DownloadStatus) -> str:
  """Get human-readable status."""
  mapping = {
    DownloadStatus.CAN_AUTO_DOWNLOAD: "✅ Can Download",
    DownloadStatus.MANUAL_DOWNLOAD: "🔗 Manual Download",
    DownloadStatus.CHECK_AVAILABILITY: "❓ Check Availability",
    DownloadStatus.CONTACT_REQUIRED: "📋 Contact Required",
    DownloadStatus.ACCESS_RESTRICTED: "⚠️ Access Restricted",
  }
  return mapping.get(status, "Unknown")
