"""
inspect_schema.py
-----------------
Connects directly to the raw CSV (without loading it into memory) and
prints every column name with its inferred data type.

This uses DuckDB's read_csv_auto() function, which scans a sample of
the file to infer types — similar to how pandas infers dtypes, but
without loading the whole file into RAM.

Useful for understanding the raw data before designing a schema.

Usage:
    python engineering/inspect_schema.py
"""

import sys
from pathlib import Path

try:
    import duckdb
    import kagglehub
except ImportError as e:
    print(f"ERROR: Missing dependency — {e}")
    print("Fix: pip install duckdb kagglehub")
    sys.exit(1)


# ── Constants ────────────────────────────────────────────────────────────────

DATASET_HANDLE = "amith1707/video-game-market-price-and-revenue-dataset"
RAW_CSV_RELATIVE = Path(
    "data/full/videogames_full.csv/videogames_processed.csv"
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def get_csv_path() -> Path:
    """
    Resolves the full path to the raw CSV using the kagglehub cache.

    Returns:
        Path: Full path to videogames_processed.csv
    """
    base = Path(kagglehub.dataset_download(DATASET_HANDLE))
    return base / RAW_CSV_RELATIVE


def inspect_schema(csv_path: Path) -> None:
    """
    Uses DuckDB to infer and print the schema of the raw CSV.

    DuckDB scans only a sample of the file to infer column types,
    so this runs in seconds even on a 5GB file.

    Args:
        csv_path: Full path to the CSV file to inspect.
    """
    if not csv_path.exists():
        print(f"ERROR: CSV not found at {csv_path}")
        print("Have you run download_data.py first?")
        sys.exit(1)

    print(f"Inspecting: {csv_path}\n")

    con = duckdb.connect()
    rows = con.execute(
        f"DESCRIBE SELECT * FROM read_csv_auto('{csv_path.as_posix()}')"
    ).fetchall()
    con.close()

    print(f"{'Column':<40} {'Type'}")
    print("-" * 55)
    for row in rows:
        print(f"{row[0]:<40} {row[1]}")

    print(f"\nTotal columns: {len(rows)}")


# ── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    csv_path = get_csv_path()
    inspect_schema(csv_path)