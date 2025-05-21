import pymysql
import sqlite3

# Connect to MySQL
mysql_conn = pymysql.connect(
    host="localhost",
    user="root",
    password="",
    database="halal_scan",
    charset="utf8mb4"
)
mysql_cursor = mysql_conn.cursor()

# Connect to SQLite
sqlite_conn = sqlite3.connect('halal_scan.db')
sqlite_cursor = sqlite_conn.cursor()

sqlite_cursor.execute("DROP TABLE IF EXISTS ingredients_v2")

# Ensure the table exists (if it doesn't, create it)
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

# Fetch data from MySQL (for the ingredients_v2 table)
mysql_cursor.execute("SELECT id, name, ecode, category, status, explanation FROM ingredients_v2")
data = mysql_cursor.fetchall()

# Insert data into SQLite (for the ingredients_v2 table)
for row in data:
    sqlite_cursor.execute("""
    INSERT INTO ingredients_v2 (id, name, ecode, category, status, explanation)
    VALUES (?, ?, ?, ?, ?, ?)
    """, row)

# Commit and close connections
sqlite_conn.commit()
mysql_conn.close()
sqlite_conn.close()

print("Data migration completed successfully.")
