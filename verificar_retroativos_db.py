import sqlite3
from decimal import Decimal

# Caminho do banco retroativos.db (ajuste conforme necessário)
caminho_db = "instance/retroativos.db"

try:
    conn = sqlite3.connect(caminho_db)
    cursor = conn.cursor()

    # Verifica artistas únicos
    print("\n🎤 Artistas encontrados:")
    cursor.execute("SELECT DISTINCT artista FROM retroativos_calculados ORDER BY artista")
    artistas = cursor.fetchall()
    for artista in artistas:
        print(f"- {artista[0]}")

    # Verifica valores por artista e ano
    print("\n📊 Valores por artista e ano:")
    for artista in artistas:
        nome = artista[0]
        cursor.execute("""
            SELECT ano, lucro_liquido FROM retroativos_calculados
            WHERE artista = ?
            ORDER BY ano
        """, (nome,))
        resultados = cursor.fetchall()
        print(f"\n🎼 {nome}:")
        for ano, valor in resultados:
            print(f"   {ano}: € {Decimal(valor):,.4f}")

    conn.close()
except Exception as e:
    print(f"❌ Erro ao acessar o banco de dados: {e}")
