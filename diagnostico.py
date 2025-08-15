import pandas as pd
from decimal import Decimal
from collections import defaultdict

def normalizar_texto(texto):
    import unicodedata
    if not isinstance(texto, str):
        return ""
    texto = texto.lower().strip()
    texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')
    texto = ''.join(c for c in texto if c.isalnum() or c.isspace())
    return texto.strip()

def diagnostico_titulos(path_planilha):
    ext = path_planilha.split('.')[-1].lower()
    df = pd.read_csv(path_planilha, sep=None, engine='python') if ext == 'csv' else pd.read_excel(path_planilha)

    # Padroniza colunas
    df.columns = [col.strip().lower().replace('ç', 'c') for col in df.columns]
    col_titulo = next((c for c in df.columns if "titulo" in c), None)
    col_lucro = next((c for c in df.columns if "lucro" in c), None)

    if not col_titulo or not col_lucro:
        print("❌ Colunas obrigatórias não encontradas.")
        return

    df['titulo_normalizado'] = df[col_titulo].astype(str).apply(normalizar_texto)
    df['lucro'] = pd.to_numeric(df[col_lucro].astype(str).str.replace(',', '.'), errors='coerce').fillna(0).apply(Decimal)

    print("\n✅ Títulos únicos encontrados:")
    agrupado = df.groupby('titulo_normalizado')['lucro'].agg(['count', 'sum']).reset_index()
    agrupado = agrupado.sort_values(by='sum', ascending=False)

    for _, row in agrupado.iterrows():
        print(f"- {row['titulo_normalizado']} | Linhas: {row['count']} | Lucro Total: € {row['sum']}")

    # Detecta duplicatas exatas
    duplicadas = df[df.duplicated(subset=['titulo_normalizado', 'lucro'], keep=False)]
    if not duplicadas.empty:
        print("\n⚠️ Linhas Duplicadas Detalhadas:")
        print(duplicadas[['titulo_normalizado', 'lucro']])

# Exemplo de uso:
# diagnostico_titulos("uploads/NomeDoArquivo.xlsx")
