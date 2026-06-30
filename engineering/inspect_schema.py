import kagglehub
import duckdb

path = kagglehub.dataset_download("amith1707/video-game-market-price-and-revenue-dataset")
full_csv = f"{path}\\data\\full\\videogames_full.csv\\videogames_processed.csv"

con = duckdb.connect()
result = con.execute(f"DESCRIBE SELECT * FROM read_csv_auto('{full_csv}')").fetchall()

for row in result:
    print(f"{row[0]}: {row[1]}")