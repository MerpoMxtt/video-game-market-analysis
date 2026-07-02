import kagglehub
import duckdb
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
dataset_path = Path(kagglehub.dataset_download(
    "amith1707/video-game-market-price-and-revenue-dataset"
))
raw_csv  = dataset_path / "data" / "full" / "videogames_full.csv" / "videogames_processed.csv"
db_path  = Path(__file__).parent.parent / "data" / "videogames.duckdb"
db_path.parent.mkdir(parents=True, exist_ok=True)

# DuckDB expects forward slashes even on Windows
raw_csv_str = raw_csv.as_posix()

print(f"Source : {raw_csv_str}")
print(f"Target : {db_path}\n")

con = duckdb.connect(str(db_path))

# ── dim_games ──────────────────────────────────────────────────────────────────
# One row per game — static attributes that never change week to week
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
    FROM read_csv_auto('{raw_csv_str}')
    GROUP BY game_id
""")
print(f"  ✓ {con.execute('SELECT COUNT(*) FROM dim_games').fetchone()[0]:,} games\n")

# ── dim_platform ───────────────────────────────────────────────────────────────
# One row per platform — only 6 rows total
print("Building dim_platform...")
con.execute(f"""
    CREATE OR REPLACE TABLE dim_platform AS
    SELECT
        platform_code,
        ANY_VALUE(platform)             AS platform,
        ANY_VALUE(storefront)           AS storefront,
        ANY_VALUE(subscription_service) AS subscription_service
    FROM read_csv_auto('{raw_csv_str}')
    GROUP BY platform_code
""")
print(f"  ✓ {con.execute('SELECT COUNT(*) FROM dim_platform').fetchone()[0]:,} platforms\n")

# ── dim_time ───────────────────────────────────────────────────────────────────
# One row per observation date — pre-computed calendar attributes
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
    FROM read_csv_auto('{raw_csv_str}')
    GROUP BY obs_date
""")
print(f"  ✓ {con.execute('SELECT COUNT(*) FROM dim_time').fetchone()[0]:,} dates\n")

# ── fact_weekly_metrics ────────────────────────────────────────────────────────
# One row per (game × platform × week) — all time-varying measures
print("Building fact_weekly_metrics  (scanning 5 GB — takes a few minutes)...")
con.execute(f"""
    CREATE OR REPLACE TABLE fact_weekly_metrics AS
    SELECT
        -- Foreign keys linking to dimension tables
        game_id, platform_code, obs_date,

        -- Lifecycle position
        days_since_release, days_since_release_log, launch_phase, is_new_release,

        -- Pricing
        current_price_usd, original_price_usd, discount_pct, is_on_sale,
        sale_event_name, lowest_price_usd, decay_factor, price_vs_launch,
        launch_price_decay, price_change_abs, price_change_pct,
        price_7obs_avg, price_30obs_avg, price_volatility,
        price_all_time_low, is_all_time_low, discount_frequency_proxy,
        discount_intensity, affordability_index,

        -- Regional pricing
        price_na, price_eu, price_gb, price_jp, price_br, price_au,

        -- Engagement
        concurrent_players, peak_ccu_alltime,
        ccu_7obs_avg, ccu_30obs_avg, player_growth_rate,
        review_count, positive_reviews, negative_reviews,
        steam_rating_pct, user_score, metacritic_score,
        wishlist_count, twitch_viewers_proxy, youtube_views_proxy,
        reddit_mentions, social_hype_index,
        hype_score, virality_score, influencer_boost_proxy, popularity_momentum,
        review_velocity, review_growth_rate,

        -- Revenue
        estimated_units_sold, estimated_revenue_usd,
        revenue_per_review, revenue_per_player,
        revenue_cumulative, units_cumulative,
        monetisation_intensity, revenue_momentum_4w,

        -- Sentiment & community health
        has_controversy, controversy_day, controversy_score,
        engagement_to_price, review_times_rating,
        critic_user_gap, sentiment_stability, community_health_score,
        tier_label, genre_popularity_rank, platform_popularity_rank,

        -- Anomaly flags
        rating_drop_flag, fake_discount_flag,
        player_spike_flag, review_inflation_flag,

        -- ML targets
        target_ccu_next_4w, target_revenue_next_4w, target_price_next_4w,
        target_review_count_next_4w, target_is_on_sale_next_obs,
        target_breakout_hit, target_sleeper_hit, target_long_tail
    FROM read_csv_auto('{raw_csv_str}')
""")
print(f"  ✓ {con.execute('SELECT COUNT(*) FROM fact_weekly_metrics').fetchone()[0]:,} rows\n")

con.close()
print(f"Database saved to: {db_path}")