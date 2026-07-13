"""
download_data.py
----------------
Downloads the Video Game Market Price and Revenue Dataset from Kaggle
using the kagglehub library.

The dataset (~5GB) is saved to your local kagglehub cache, NOT inside
this repo. The cache path is printed at the end so you know where it
landed.

Requirements:
    pip install kagglehub

Usage:
    python download_data.py
"""

import sys
from pathlib import Path

try:
    import kagglehub
except ImportError:
    print("ERROR: kagglehub is not installed.")
    print("Fix: pip install kagglehub")
    sys.exit(1)


# ── Constants ────────────────────────────────────────────────────────────────

DATASET_HANDLE = "amith1707/video-game-market-price-and-revenue-dataset"


# ── Main ─────────────────────────────────────────────────────────────────────

def download_dataset() -> Path:
    """
    Downloads the dataset from Kaggle and returns the local cache path.

    If the dataset has already been downloaded, kagglehub skips the
    download and just returns the existing path instantly.

    Returns:
        Path: The local directory containing the downloaded dataset files.
    """
    print(f"Downloading dataset: {DATASET_HANDLE}")
    print("(If already cached this will be instant)\n")

    try:
        path = Path(kagglehub.dataset_download(DATASET_HANDLE))
    except Exception as e:
        print(f"ERROR: Download failed — {e}")
        print("Make sure you have a Kaggle account and are logged in.")
        sys.exit(1)

    return path


def summarise_download(path: Path) -> None:
    """
    Prints a summary of what was downloaded — file names and sizes.

    Args:
        path: The local directory returned by kagglehub.
    """
    print(f"Dataset location: {path}\n")

    # Walk every file under the download path and report its size
    all_files = sorted(path.rglob("*.csv"))
    if not all_files:
        print("No CSV files found. Check the path above manually.")
        return

    print(f"{'File':<55} {'Size':>10}")
    print("-" * 67)
    for f in all_files:
        size_mb = f.stat().st_size / (1024 ** 2)
        # Show path relative to the dataset root for readability
        relative = f.relative_to(path)
        print(f"{str(relative):<55} {size_mb:>8.1f} MB")


if __name__ == "__main__":
    dataset_path = download_dataset()
    summarise_download(dataset_path)
    print("\nDone. Run engineering/ingest.py next to build the database.")