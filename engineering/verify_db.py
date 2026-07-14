"""
verify_db.py
------------
Runs a set of sanity checks against the DuckDB database built by
ingest.py. Confirms that all four tables exist, have the expected
row counts, and contain sensible data.

Run this after ingest.py completes to confirm everything is healthy
before moving to the analysis or modeling notebooks.

Usage:
    python engineering/verify_db.py
"""

import sys
from pathlib import Path

try:
    import duckdb
except ImportError:
    print("ERROR: duckdb is not installed.")
    print("Fix: pip install duckdb")
    sys.exit(1)


# ── Constants ────────────────────────────────────────────────────────────────

DB_PATH = Path(__file__).parent.parent / "data" / "videogames.duckdb"

# Expected minimum row counts — used to flag obvious ingestion failures
EXPECTED_COUNTS = {
    "dim_games":           9_000,
    "dim_platform":        6,
    "dim_time":            2_000,
    "fact_weekly_metrics": 5_000_000,
}


# ── Checks ───────────────────────────────────────────────────────────────────

def check_row_counts(con: duckdb.DuckDBPyConnection) -> bool:
    """
    Checks that all four tables exist and meet minimum row count thresholds.

    Args:
        con: Open DuckDB connection.

    Returns:
        bool: True if all checks pass, False if any fail.
    """
    print("=== Table row counts ===")
    all_passed = True

    for table, minimum in EXPECTED_COUNTS.items():
        try:
            count = con.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()[0]
            status = "✓" if count >= minimum else "✗ BELOW EXPECTED"
            print(f"  {status}  {table:<25} {count:>12,} rows")
            if count < minimum:
                all_passed = False
        except Exception as e:
            print(f"  ✗  {table:<25} ERROR — {e}")
            all_passed = False

    return all_passed


def check_platforms(con: duckdb.DuckDBPyConnection) -> None:
    """
    Prints all rows from dim_platform so you can visually confirm
    the six expected platforms are present.

    Args:
        con: Open DuckDB connection.
    """
    print("\n=== Platforms ===")
    rows = con.execute(
        "SELECT platform_code, platform, storefront FROM dim_platform "
        "ORDER BY platform"
    ).fetchall()
    for row in rows:
        print(f"  {row[0]:<10} {row[1]:<22} {row[2]}")


def check_sample_games(con: duckdb.DuckDBPyConnection) -> None:
    """
    Prints five sample rows from dim_games as a spot check.

    Args:
        con: Open DuckDB connection.
    """
    print("\n=== Sample games (5 rows) ===")
    rows = con.execute("""
        SELECT
            game_name,
            developer,
            genre,
            CAST(is_indie AS INTEGER) AS is_indie,
            CAST(is_aaa   AS INTEGER) AS is_aaa,
            CAST(release_year AS INTEGER) AS release_year
        FROM dim_games
        LIMIT 5
    """).fetchall()

    for row in rows:
        print(
            f"  {row[0]:<32} {row[1]:<22} {row[2]:<14} "
            f"indie={row[3]}  aaa={row[4]}  ({row[5]})"
        )


def check_revenue_sanity(con: duckdb.DuckDBPyConnection) -> None:
    """
    Prints summary statistics from fact_weekly_metrics to confirm
    the revenue and player numbers are in a sensible range.

    Args:
        con: Open DuckDB connection.
    """
    print("\n=== Revenue sanity check ===")
    row = con.execute("""
        SELECT
            ROUND(AVG(estimated_revenue_usd), 2) AS avg_revenue,
            ROUND(MAX(estimated_revenue_usd), 2) AS max_revenue,
            ROUND(AVG(current_price_usd),     2) AS avg_price,
            ROUND(AVG(concurrent_players),    0) AS avg_players
        FROM fact_weekly_metrics
    """).fetchone()

    print(f"  Avg weekly revenue : ${row[0]:>15,.2f}")
    print(f"  Max weekly revenue : ${row[1]:>15,.2f}")
    print(f"  Avg price (USD)    : ${row[2]:>15,.2f}")
    print(f"  Avg concurrent CCU :  {int(row[3]):>15,}")


# ── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== Video Game Market Analysis — Database Verification ===\n")

    if not DB_PATH.exists():
        print(f"ERROR: Database not found at {DB_PATH}")
        print("Run engineering/ingest.py first.")
        sys.exit(1)

    con = duckdb.connect(str(DB_PATH))

    try:
        passed = check_row_counts(con)
        check_platforms(con)
        check_sample_games(con)
        check_revenue_sanity(con)
    finally:
        con.close()

    print("\n" + ("=== All checks passed ✓" if passed else
                  "=== Some checks FAILED ✗ — review output above"))