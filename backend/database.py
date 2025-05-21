import pandas as pd
import pymysql

# Connect to your MySQL database
db = pymysql.connect(
    host="localhost",
    user="root",
    password="",
    database="halal_scan",
    charset="utf8mb4"
)
cursor = db.cursor()

# Load Excel file
df = pd.read_excel("common ingredients.xlsx")  # Change the file name if different

# Optional: Map status shorthand to full label
status_map = {
    "Y": "halal",
    "N": "haram",
    "!": "doubtful"
}

# Insert into DB
for index, row in df.iterrows():
    status = status_map.get(str(row['Halal']).strip(), "unknown")
    name = str(row['Ingredient']).strip()
    category = str(row['Category']).strip()
    explanation = str(row['Description']).strip()

    try:
        cursor.execute(
            "INSERT INTO ingredients_v2 (ecode, name, category, status, explanation) VALUES (%s, %s, %s, %s, %s)",
            (None, name, category, status, explanation)
        )
    except Exception as e:
        print(f"Error inserting {name}: {e}")

db.commit()
cursor.close()
db.close()

print("✅ Excel data inserted into ingredients_v2 successfully.")
