# Installation

## Requirements

- Python 3.10 or later
- pip
- Internet connection for dataset search and download

## Quick Install

```bash
# Clone or download the project
cd Dataset_collector

# Create a virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install the package in development mode
pip install -e .
```

## API Keys (Optional)

Some sources work without API keys. For better rate limits and access:

| Service | Environment Variable | Config Key |
|---------|---------------------|------------|
| Kaggle | `KAGGLE_USERNAME`, `KAGGLE_KEY` | `api_keys.kaggle_username`, `api_keys.kaggle_key` |
| GitHub | `GITHUB_TOKEN` | `api_keys.github_token` |
| Hugging Face | `HF_TOKEN` | `api_keys.huggingface_token` |

Edit `config/default_config.yaml` or set environment variables.

## Run

```bash
python run.py
```

Or after installation:

```bash
dataset-collector
```

## Data Directories

On first launch, the application creates:

- `~/Dataset_Collector/downloads` — Downloaded datasets
- `~/Dataset_Collector/manifests` — Generated manifests
- `~/Dataset_Collector/library` — Library index
- `~/Dataset_Collector/logs` — Application logs
