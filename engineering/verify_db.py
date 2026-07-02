import duckdb
from pathlib import Path

db_path = Path(__file__).parent.parent / "data" / "videogames.duckdb"
con = duckdb.connect(str(db_path))

print("=== TABLE ROW COUNTS ===")
for table in ["dim_games", "dim_platform", "dim_time", "fact_weekly_metrics"]:
    count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    print(f"  {table:<25} {count:>10,} rows")

print("\n=== PLATFORMS ===")
platforms = con.execute("SELECT platform_code, platform, storefront FROM dim_platform").fetchall()
for row in platforms:
    print(f"  {row[0]:<15} {row[1]:<20} {row[2]}")

print("\n=== SAMPLE GAMES ===")
games = con.execute("""
    SELECT game_name, developer, genre, is_indie, is_aaa, release_year
    FROM dim_games
    LIMIT 5
""").fetchall()
for row in games:
    print(f"  {row[0]:<30} {row[1]:<20} {row[2]:<15} indie={int(row[3])} aaa={int(row[4])} ({int(row[5])})")

print("\n=== REVENUE SANITY CHECK ===")
result = con.execute("""
    SELECT
        ROUND(AVG(estimated_revenue_usd), 2) AS avg_revenue,
        ROUND(MAX(estimated_revenue_usd), 2) AS max_revenue,
        ROUND(AVG(current_price_usd), 2)     AS avg_price,
        ROUND(AVG(concurrent_players), 0)    AS avg_players
    FROM fact_weekly_metrics
""").fetchone()
print(f"  Avg revenue:  ${result[0]:>12,.2f}")
print(f"  Max revenue:  ${result[1]:>12,.2f}")
print(f"  Avg price:    ${result[2]:>12,.2f}")
print(f"  Avg players:  {int(result[3]):>12,}")

con.close()