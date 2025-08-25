# init_db.py  —— one-off schema initializer (Windows-safe)
import os, sqlite3

DB_PATH = r"app/data/als.db"
SCHEMA_PATH = r"app/data/schema.sql"

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
con = sqlite3.connect(DB_PATH)
with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
    con.executescript(f.read())

tables = con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
con.close()
print("Applied schema. Tables:", tables)
