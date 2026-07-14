"""
ingest.py
---------
Builds a star-schema DuckDB database from the raw 5GB CSV.

What is a star schema?
    A way of organising data in an analytics database. Instead of one
    giant flat table with everything repeated, you split it into:

    - Dimension tables: small tables of descriptive info (one row per
      game, platform, or date). These rarely change.

    - Fact table: the large table of measurements (one row per game x
      platform x week). This is where all the numbers live.

    The fact table links to dimension tables via foreign keys, like a
    lookup table. This avoids repeating "developer = CD Projekt Red,
    genre = RPG" 558 times for every weekly observation of one game.

Tables created:
    dim_games           — 1 row per game (static attributes)
    dim_platform        — 1 row per platform (6 platforms total)
    dim_time            — 1 row per observation date
    fact_weekly_metrics — 1 row per game x platform x week (5.58M rows)

Usage:
    python engineering/ingest.py
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

DATASET_HANDLE  = "amith1707/video-game-market-price-and-revenue-dataset"
RAW_CSV_RELATIVE = Path(
    "data/full/videogames_full.csv/videogames_processed.csv"
)
DB_RELATIVE = Path("data/videogames.duckdb")


# ── Helpers ──────────────────────────────────────────────────────────────────

def resolve_paths() -> tuple[Path, Path]:
    """
    Resolves the full path to the raw CSV and the target database file.

    Returns:
        tuple: (csv_path, db_path)
    """
    base     = Path(kagglehub.dataset_download(DATASET_HANDLE))
    csv_path = base / RAW_CSV_RELATIVE
    db_path  = Path(__file__).parent.parent / DB_RELATIVE

    if not csv_path.exists():
        print(f"ERROR: Raw CSV not found at {csv_path}")
        print("Run download_data.py first.")
        sys.exit(1)

    # Create the data/ directory if it doesn't exist yet
    db_path.parent.mkdir(parents=True, exist_ok=True)

    return csv_path, db_path


def build_dim_games(con: duckdb.DuckDBPyConnection, csv: str) -> None:
    """
    Builds dim_games — one row per unique game_id.

    Uses ANY_VALUE() to collapse the 5.58M row CSV down to 10,000 rows.
    ANY_VALUE() picks one value from the group — safe here because these
    static columns (name, genre, developer etc.) are identical across all
    weekly observations for the same game.

    Args:
        con: Open DuckDB connection.
        csv: POSIX path string to the raw CSV.
    """
    print("Building dim_games...")
    con.execute(f"""
        CREATE OR REPLACE TABLE dim_games AS
        SELECT
            game_id,
            ANY_VALUE(game_name)              AS game_name,
            ANY_VALUE(developer)              AS developer,
            ANY_VALUE(publisher)              AS publisher,
            ANY_VALUE(publisher_tier)         AS publisher_tier,
            ANY_VALUE(franchise)              AS franchise,
            ANY_VALUE(genre)                  AS genre,
            ANY_VALUE(genre_code)             AS genre_code,
            ANY_VALUE(subgenre)               AS subgenre,
            ANY_VALUE(tags)                   AS tags,
            ANY_VALUE(age_rating)             AS age_rating,
            ANY_VALUE(release_date)           AS release_date,
            ANY_VALUE(release_year)           AS release_year,
            ANY_VALUE(release_month)          AS release_month,
            ANY_VALUE(release_quarter)        AS release_quarter,
            ANY_VALUE(base_price_usd)         AS base_price_usd,
            ANY_VALUE(dlc_count)              AS dlc_count,
            ANY_VALUE(expansion_count)        AS expansion_count,
            ANY_VALUE(achievement_count)      AS achievement_count,
            ANY_VALUE(supported_languages)    AS supported_languages,
            ANY_VALUE(is_free_to_play)        AS is_free_to_play,
            ANY_VALUE(is_indie)               AS is_indie,
            ANY_VALUE(is_early_access)        AS is_early_access,
            ANY_VALUE(is_multiplayer)         AS is_multiplayer,
            ANY_VALUE(is_online)              AS is_online,
            ANY_VALUE(is_franchise)           AS is_franchise,
            ANY_VALUE(is_sequel)              AS is_sequel,
            ANY_VALUE(is_remaster)            AS is_remaster,
            ANY_VALUE(is_remake)              AS is_remake,
            ANY_VALUE(is_crossplay)           AS is_crossplay,
            ANY_VALUE(has_crossbuy)           AS has_crossbuy,
            ANY_VALUE(publisher_market_share) AS publisher_market_share,
            ANY_VALUE(publisher_avg_budget)   AS publisher_avg_budget,
            ANY_VALUE(is_aaa)                 AS is_aaa,
            ANY_VALUE(holiday_release_flag)   AS holiday_release_flag,
            ANY_VALUE(q4_release_flag)        AS q4_release_flag
        FROM read_csv_auto('{csv}')
        GROUP BY game_id
    """)
    count = con.execute("SELECT COUNT(*) FROM dim_games").fetchone()[0]
    print(f"  ✓ {count:,} games\n")


def build_dim_platform(con: duckdb.DuckDBPyConnection, csv: str) -> None:
    """
    Builds dim_platform — one row per unique platform_code.

    There are only 6 platforms in this dataset (PC, PS5, PS4,
    Xbox Series X/S, Xbox One, Nintendo Switch).

    Args:
        con: Open DuckDB connection.
        csv: POSIX path string to the raw CSV.
    """
    print("Building dim_platform...")
    con.execute(f"""
        CREATE OR REPLACE TABLE dim_platform AS
        SELECT
            platform_code,
            ANY_VALUE(platform)             AS platform,
            ANY_VALUE(storefront)           AS storefront,
            ANY_VALUE(subscription_service) AS subscription_service
        FROM read_csv_auto('{csv}')
        GROUP BY platform_code
    """)
    count = con.execute("SELECT COUNT(*) FROM dim_platform").fetchone()[0]
    print(f"  ✓ {count:,} platforms\n")


def build_dim_time(con: duckdb.DuckDBPyConnection, csv: str) -> None:
    """
    Builds dim_time — one row per unique observation date.

    Pre-computing calendar attributes here (year, month, quarter,
    season flags) means the analyst layer never has to re-derive them
    in every query — they're already in the table ready to join.

    Args:
        con: Open DuckDB connection.
        csv: POSIX path string to the raw CSV.
    """
    print("Building dim_time...")
    con.execute(f"""
        CREATE OR REPLACE TABLE dim_time AS
        SELECT
            obs_date,
            ANY_VALUE(obs_year)       AS obs_year,
            ANY_VALUE(obs_month)      AS obs_month,
            ANY_VALUE(obs_quarter)    AS obs_quarter,
            ANY_VALUE(obs_dow)        AS obs_dow,
            ANY_VALUE(is_q4)          AS is_q4,
            ANY_VALUE(is_summer)      AS is_summer,
            ANY_VALUE(is_weekend_obs) AS is_weekend_obs
        FROM read_csv_auto('{csv}')
        GROUP BY obs_date
    """)
    count = con.execute("SELECT COUNT(*) FROM dim_time").fetchone()[0]
    print(f"  ✓ {count:,} dates\n")


def build_fact_weekly_metrics(
    con: duckdb.DuckDBPyConnection, csv: str
) -> None:
    """
    Builds fact_weekly_metrics — one row per game x platform x week.

    This is the largest table (5.58M rows) and the heart of the schema.
    Every time-varying measurement lives here: pricing, player counts,
    revenue, engagement scores, anomaly flags, and ML targets.

    The three foreign key columns (game_id, platform_code, obs_date)
    link each row back to the relevant dimension tables.

    Note: This scans the full 5GB CSV so it takes a few minutes.

    Args:
        con: Open DuckDB connection.
        csv: POSIX path string to the raw CSV.
    """
    print("Building fact_weekly_metrics (scanning 5GB — a few minutes)...")
    con.execute(f"""
        CREATE OR REPLACE TABLE fact_weekly_metrics AS
        SELECT
            -- Foreign keys (link to dimension tables)
            game_id,
            platform_code,
            obs_date,

            -- Lifecycle position
            days_since_release,
            days_since_release_log,
            launch_phase,
            is_new_release,

            -- Pricing
            current_price_usd,
            original_price_usd,
            discount_pct,
            is_on_sale,
            sale_event_name,
            lowest_price_usd,
            decay_factor,
            price_vs_launch,
            launch_price_decay,
            price_change_abs,
            price_change_pct,
            price_7obs_avg,
            price_30obs_avg,
            price_volatility,
            price_all_time_low,
            is_all_time_low,
            discount_frequency_proxy,
            discount_intensity,
            affordability_index,

            -- Regional pricing
            price_na, price_eu, price_gb,
            price_jp, price_br, price_au,

            -- Engagement
            concurrent_players,
            peak_ccu_alltime,
            ccu_7obs_avg,
            ccu_30obs_avg,
            player_growth_rate,
            review_count,
            positive_reviews,
            negative_reviews,
            steam_rating_pct,
            user_score,
            metacritic_score,
            wishlist_count,
            twitch_viewers_proxy,
            youtube_views_proxy,
            reddit_mentions,
            social_hype_index,
            hype_score,
            virality_score,
            influencer_boost_proxy,
            popularity_momentum,
            review_velocity,
            review_growth_rate,

            -- Revenue
            estimated_units_sold,
            estimated_revenue_usd,
            revenue_per_review,
            revenue_per_player,
            revenue_cumulative,
            units_cumulative,
            monetisation_intensity,
            revenue_momentum_4w,

            -- Sentiment and community
            has_controversy,
            controversy_day,
            controversy_score,
            engagement_to_price,
            review_times_rating,
            critic_user_gap,
            sentiment_stability,
            community_health_score,
            tier_label,
            genre_popularity_rank,
            platform_popularity_rank,

            -- Anomaly flags
            rating_drop_flag,
            fake_discount_flag,
            player_spike_flag,
            review_inflation_flag,

            -- ML targets
            target_ccu_next_4w,
            target_revenue_next_4w,
            target_price_next_4w,
            target_review_count_next_4w,
            target_is_on_sale_next_obs,
            target_breakout_hit,
            target_sleeper_hit,
            target_long_tail
        FROM read_csv_auto('{csv}')
    """)
    count = con.execute(
        "SELECT COUNT(*) FROM fact_weekly_metrics"
    ).fetchone()[0]
    print(f"  ✓ {count:,} rows\n")


# ── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== Video Game Market Analysis — Database Ingestion ===\n")

    csv_path, db_path = resolve_paths()
    print(f"Source : {csv_path}")
    print(f"Target : {db_path}\n")

    con = duckdb.connect(str(db_path))

    try:
        build_dim_games(con, csv_path.as_posix())
        build_dim_platform(con, csv_path.as_posix())
        build_dim_time(con, csv_path.as_posix())
        build_fact_weekly_metrics(con, csv_path.as_posix())
    except Exception as e:
        print(f"\nERROR during ingestion: {e}")
        con.close()
        sys.exit(1)
    finally:
        con.close()

    print(f"Database saved to: {db_path}")
    print("Run engineering/verify_db.py to confirm everything loaded.")