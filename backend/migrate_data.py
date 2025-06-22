import sqlite3

sqlite_conn = sqlite3.connect('halal_scan.db')
sqlite_cursor = sqlite_conn.cursor()
sqlite_cursor.execute("DROP TABLE IF EXISTS ingredients_v2")

sqlite_cursor.execute("""
CREATE TABLE ingredients_v2 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255),
    ecode VARCHAR(10),
    category VARCHAR(255),
    status VARCHAR(50),
    explanation TEXT
);
""")

sqlite_conn.commit()
sqlite_conn.close()

print("Data migration completed successfully.")
