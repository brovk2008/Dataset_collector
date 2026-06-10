"""Auto-generate starter code for loading downloaded datasets."""

from __future__ import annotations

from pathlib import Path
from typing import Literal


class LoaderGenerator:
  """Generate starter code for common dataset formats."""

  SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
  SUPPORTED_CSV_EXTENSIONS = {".csv", ".tsv", ".txt"}
  SUPPORTED_JSON_EXTENSIONS = {".json", ".jsonl"}

  @staticmethod
  def detect_dataset_type(directory: Path) -> Literal["csv", "images", "json", "mixed", "unknown"]:
    """Detect the primary dataset type by scanning directory.

    Args:
      directory: Path to dataset directory

    Returns:
      Type of dataset: 'csv', 'images', 'json', 'mixed', or 'unknown'
    """
    if not directory.is_dir():
      return "unknown"

    csv_count = 0
    image_count = 0
    json_count = 0

    # Scan files recursively (limit to first 100 for performance)
    file_count = 0
    for file_path in directory.rglob("*"):
      if file_count > 100:
        break
      if file_path.is_file():
        file_count += 1
        ext = file_path.suffix.lower()

        if ext in LoaderGenerator.SUPPORTED_CSV_EXTENSIONS:
          csv_count += 1
        elif ext in LoaderGenerator.SUPPORTED_IMAGE_EXTENSIONS:
          image_count += 1
        elif ext in LoaderGenerator.SUPPORTED_JSON_EXTENSIONS:
          json_count += 1

    # Determine dominant type
    totals = {
      "csv": csv_count,
      "images": image_count,
      "json": json_count,
    }

    max_type = max(totals, key=totals.get)
    max_count = totals[max_type]

    if max_count == 0:
      return "unknown"

    # Check for mixed types
    non_zero_types = sum(1 for count in totals.values() if count > 0)
    if non_zero_types > 1 and max_count < file_count * 0.8:
      return "mixed"

    return max_type

  @staticmethod
  def generate_loader_code(directory: Path) -> str:
    """Generate starter code for loading a dataset.

    Args:
      directory: Path to dataset directory

    Returns:
      Python code as a string
    """
    dataset_type = LoaderGenerator.detect_dataset_type(directory)

    if dataset_type == "csv":
      return LoaderGenerator._generate_csv_loader()
    elif dataset_type == "images":
      return LoaderGenerator._generate_image_loader()
    elif dataset_type == "json":
      return LoaderGenerator._generate_json_loader()
    elif dataset_type == "mixed":
      return LoaderGenerator._generate_mixed_loader()
    else:
      return LoaderGenerator._generate_generic_loader()

  @staticmethod
  def _generate_csv_loader() -> str:
    """Generate pandas CSV loading code."""
    return '''"""Load and explore CSV dataset."""

import pandas as pd
import os

# Load CSV file(s)
csv_file = "data.csv"  # Update with your filename
if os.path.exists(csv_file):
    df = pd.read_csv(csv_file)

    # Display basic info
    print(f"Loaded {len(df)} rows, {len(df.columns)} columns")
    print(f"Columns: {list(df.columns)}")

    # Show first few rows
    print("\\nFirst 5 rows:")
    print(df.head())

    # Display data types and missing values
    print("\\nData Info:")
    print(df.info())

    # Summary statistics
    print("\\nStatistics:")
    print(df.describe())

    # Check for missing values
    print("\\nMissing values:")
    print(df.isnull().sum())
else:
    print(f"File not found: {csv_file}")
    print("Update the csv_file variable with the correct filename.")
'''

  @staticmethod
  def _generate_image_loader() -> str:
    """Generate PyTorch image loading code."""
    return '''"""Load and explore image dataset."""

import os
from pathlib import Path
from PIL import Image
import torch
from torchvision import datasets, transforms

# Define image transforms
transform = transforms.Compose([
    transforms.Resize((224, 224)),  # Resize to standard size
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],  # ImageNet normalization
        std=[0.229, 0.224, 0.225]
    )
])

# Load images from directory
# Assumes subdirectories for each class
dataset_dir = "images"  # Update with your directory

if os.path.isdir(dataset_dir):
    try:
        # Try to load as ImageFolder (with class subdirectories)
        dataset = datasets.ImageFolder(dataset_dir, transform=transform)
        print(f"Loaded {len(dataset)} images")
        print(f"Classes: {dataset.classes}")

        # Create data loader for batching
        batch_size = 32
        dataloader = torch.utils.data.DataLoader(
            dataset,
            batch_size=batch_size,
            shuffle=True,
            num_workers=0  # Set to 4+ for multi-core loading
        )

        # Display batch info
        print(f"Number of batches: {len(dataloader)}")

        # Get one batch to check dimensions
        for images, labels in dataloader:
            print(f"\\nBatch shape: {images.shape}")
            print(f"Labels: {labels}")
            break

    except Exception as e:
        print(f"Error loading images: {e}")
        print("Make sure images are organized in subdirectories:")
        print("  dataset/class1/image1.jpg")
        print("  dataset/class2/image2.jpg")
else:
    print(f"Directory not found: {dataset_dir}")
    print("Update the dataset_dir variable with the correct path.")
'''

  @staticmethod
  def _generate_json_loader() -> str:
    """Generate JSON loading code."""
    return '''"""Load and explore JSON dataset."""

import json
import os

json_file = "data.json"  # Update with your filename

if os.path.exists(json_file):
    try:
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Check data structure
        if isinstance(data, list):
            print(f"Loaded list with {len(data)} items")
            if data:
                print("\\nFirst item:")
                print(json.dumps(data[0], indent=2))
        elif isinstance(data, dict):
            print(f"Loaded dictionary with keys: {list(data.keys())}")
            print("\\nSample:")
            print(json.dumps(data, indent=2)[:500])
        else:
            print(f"Loaded data of type: {type(data)}")
            print(data)

        # For JSONL (JSON Lines) format
    except json.JSONDecodeError:
        print("File is not valid JSON. Trying JSONL format...")
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                items = [json.loads(line) for line in f if line.strip()]
            print(f"Loaded {len(items)} items from JSONL")
            if items:
                print("\\nFirst item:")
                print(json.dumps(items[0], indent=2))
        except Exception as e:
            print(f"Error reading JSONL: {e}")
else:
    print(f"File not found: {json_file}")
    print("Update the json_file variable with the correct filename.")
'''

  @staticmethod
  def _generate_mixed_loader() -> str:
    """Generate generic loader for mixed format datasets."""
    return '''"""Load mixed-format dataset."""

import os
import json
import pandas as pd
from pathlib import Path
from PIL import Image

dataset_dir = "."  # Update with your dataset directory

# List all files
print("Dataset structure:")
for root, dirs, files in os.walk(dataset_dir):
    level = root.replace(dataset_dir, "").count(os.sep)
    indent = " " * 2 * level
    print(f"{indent}{os.path.basename(root)}/")

    subindent = " " * 2 * (level + 1)
    for file in files[:5]:  # Show first 5 files per directory
        ext = Path(file).suffix.lower()
        print(f"{subindent}{file}")

    if len(files) > 5:
        print(f"{subindent}... and {len(files) - 5} more files")

# Load CSV if present
csv_files = list(Path(dataset_dir).glob("*.csv"))
if csv_files:
    print(f"\\nFound CSV files: {[f.name for f in csv_files[:3]]}")
    # df = pd.read_csv(csv_files[0])

# Load JSON if present
json_files = list(Path(dataset_dir).glob("*.json"))
if json_files:
    print(f"Found JSON files: {[f.name for f in json_files[:3]]}")
    # with open(json_files[0]) as f:
    #     data = json.load(f)

# Load images if present
image_extensions = {".jpg", ".png", ".jpeg"}
images = [f for f in Path(dataset_dir).glob("*")
          if f.suffix.lower() in image_extensions]
if images:
    print(f"Found {len(images)} image files")
    # img = Image.open(images[0])

print("\\nUncomment the code above to start loading specific files.")
'''

  @staticmethod
  def _generate_generic_loader() -> str:
    """Generate generic loader for unknown formats."""
    return '''"""Load dataset (generic)."""

import os
from pathlib import Path

dataset_dir = "."  # Update with your dataset directory

print("Exploring dataset structure:")
print(f"Directory: {os.path.abspath(dataset_dir)}")
print()

# List files by type
extensions = {}
for file_path in Path(dataset_dir).rglob("*"):
    if file_path.is_file():
        ext = file_path.suffix.lower()
        if ext not in extensions:
            extensions[ext] = []
        extensions[ext].append(file_path.name)

# Print summary
for ext in sorted(extensions.keys()):
    count = len(extensions[ext])
    print(f"{ext:15} : {count:4} files")
    for filename in extensions[ext][:3]:
        print(f"  - {filename}")
    if count > 3:
        print(f"  ... and {count - 3} more")

print("\\nNext steps:")
print("1. Identify the file format(s)")
print("2. Use appropriate libraries:")
print("   - CSV:    pandas.read_csv()")
print("   - JSON:   json.load() or pandas.read_json()")
print("   - Images: PIL.Image.open() or torchvision")
print("   - Data:   numpy, scipy, or domain-specific loaders")
print("\\nFor more information, see the dataset's README or documentation.")
'''
