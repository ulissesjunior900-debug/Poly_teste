import sqlite3

conn = sqlite3.connect(r"instance\polymusic.db")
cursor = conn.cursor()

cursor.execute("SELECT sql FROM sqlite_master WHERE type='table'")
schema = "\n\n".join([row[0] for row in cursor.fetchall() if row[0] is not None])

with open("schema_sqlite.sql", "w", encoding="utf-8") as f:
    f.write(schema)

conn.close()
print("Arquivo schema_sqlite.sql gerado com sucesso!")