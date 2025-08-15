# verificar_shell.py
import sqlite3

DB_PATH = "instance/retroativos.db"  # ajuste conforme necessário

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# Verifica os artistas distintos
print("\n🎤 Artistas encontrados:\n")
for row in cur.execute("SELECT DISTINCT artista FROM retroativos_calculados ORDER BY artista"):
    print(f" - {row[0]}")

# Verifica os valores por artista e ano
print("\n📊 Valores por artista e ano:\n")
for row in cur.execute("SELECT artista, ano, lucro_liquido FROM retroativos_calculados ORDER BY artista, ano"):
    print(f"{row[0]} ({row[1]}): €{row[2]}")

conn.close()
