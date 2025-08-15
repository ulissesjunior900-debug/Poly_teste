# migrate_sqlite.py (nome alternativo)
import os
import sqlite3

DB_PATH = os.path.join('instance', 'your_database.db')  # Ajuste o nome

def migrate():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        print("Verificando estrutura atual...")
        cursor.execute("PRAGMA table_info(pagamento_realizado)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'valor_brl' in columns:
            print("Coluna já existe")
            return
        
        print("Executando migração...")
        
        # Desativa foreign keys temporariamente
        cursor.execute("PRAGMA foreign_keys=off")
        
        # Cria nova tabela com a estrutura correta
        cursor.execute("""
        CREATE TABLE pagamento_realizado_temp (
            id INTEGER PRIMARY KEY,
            artista_id INTEGER NOT NULL,
            tabela_artista TEXT NOT NULL,
            sp_id INTEGER,
            mes INTEGER NOT NULL,
            ano INTEGER NOT NULL,
            valor_eur REAL NOT NULL,
            valor_brl REAL NOT NULL,
            cotacao REAL NOT NULL,
            data_pagamento TEXT NOT NULL,
            status TEXT NOT NULL,
            herdeiro TEXT,
            FOREIGN KEY(sp_id) REFERENCES sp_importada(id)
        )
        """)
        
        # Copia dados com valores padrão
        cursor.execute("""
        INSERT INTO pagamento_realizado_temp
        SELECT 
            id, artista_id, tabela_artista, sp_id, mes, ano, valor_eur,
            valor_eur * 5.5, 5.5, data_pagamento, status, herdeiro
        FROM pagamento_realizado
        """)
        
        # Remove a tabela antiga e renomeia a nova
        cursor.execute("DROP TABLE pagamento_realizado")
        cursor.execute("ALTER TABLE pagamento_realizado_temp RENAME TO pagamento_realizado")
        
        # Reativa foreign keys
        cursor.execute("PRAGMA foreign_keys=on")
        
        conn.commit()
        print("Migração concluída com sucesso!")
        
    except Exception as e:
        print(f"Erro: {str(e)}")
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()