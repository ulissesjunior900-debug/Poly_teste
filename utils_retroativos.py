import unicodedata
import re
import pandas as pd
from decimal import Decimal
from fuzzywuzzy import fuzz
from decimal import Decimal, ROUND_HALF_UP


def normalizar(texto):
    """Remove acentos e pontuação e transforma em minúsculas"""
    texto = unicodedata.normalize("NFD", texto)
    texto = texto.encode("ascii", "ignore").decode("utf-8")
    texto = re.sub(r"[^\w\s]", "", texto)
    return texto.strip().lower()

def obter_valor_lucro_liquido(linha):
    """Retorna o valor da coluna 'lucro líquido' como Decimal, com precisão."""
    colunas_possiveis = [
        "lucro líquido", "lucro liquido", "lucro_liquido", "net income", "net revenue"
    ]

    for col in linha.index:
        if col.strip().lower() in colunas_possiveis:
            try:
                valor = linha[col]
                return Decimal(str(valor)).quantize(Decimal("0.0001"))
            except:
                continue

    return Decimal("0.0")

def mes_nome(numero):
    nomes = [
        "", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
        "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
    ]
    try:
        return nomes[int(numero)]
    except:
        return str(numero)


def processar_planilhas_retroativas(base_path, ano_inicio, ano_fim, artista, variacoes, titulos_percentuais):
    resultados_por_ano = {}

    for pasta in os.listdir(base_path):
        if not os.path.isdir(os.path.join(base_path, pasta)):
            continue

        try:
            ano = int(pasta.strip().split('-')[-1])
        except:
            continue

        if not (ano_inicio <= ano <= ano_fim):
            continue

        pasta_completa = os.path.join(base_path, pasta)
        arquivos = [f for f in os.listdir(pasta_completa) if f.endswith(('.csv', '.xls', '.xlsx'))]

        for arquivo in arquivos:
            caminho = os.path.join(pasta_completa, arquivo)

            try:
                if arquivo.endswith('.csv'):
                    df = pd.read_csv(caminho, encoding='utf-8', sep=';', engine='python')
                else:
                    df = pd.read_excel(caminho)
            except Exception as e:
                print(f"[ERRO] Não foi possível abrir: {arquivo} – {e}")
                continue

            df.columns = [col.strip().lower() for col in df.columns]
            df = padronizar_colunas(df)

            if 'nome do artista' not in df.columns or 'lucro líquido' not in df.columns:
                continue

            linhas_relevantes = df[df['nome do artista'].apply(
                lambda x: any(fuzz.partial_ratio(str(x).lower(), nome.lower()) >= 90 for nome in [artista] + variacoes)
            )]

            total_eur = Decimal("0.0")

            if titulos_percentuais:
                for titulo, percentual in titulos_percentuais.items():
                    titulo = titulo.lower().strip()
                    percentual = Decimal(percentual)

                    for _, linha in linhas_relevantes.iterrows():
                        titulo_linha = str(linha.get('título', '')).lower().strip()
                        if fuzz.ratio(titulo, titulo_linha) >= 90:
                            lucro_liquido = linha.get('lucro líquido', 0)
                            try:
                                valor = Decimal(str(lucro_liquido)).quantize(Decimal('0.0001'))
                                total_eur += (valor * percentual / Decimal('100'))
                            except:
                                continue
            else:
                for _, linha in linhas_relevantes.iterrows():
                    try:
                        valor = Decimal(str(linha.get('lucro líquido', 0))).quantize(Decimal('0.0001'))
                        total_eur += valor
                    except:
                        continue

            if ano not in resultados_por_ano:
                resultados_por_ano[ano] = Decimal('0.0')
            resultados_por_ano[ano] += total_eur

    return resultados_por_ano

def padronizar_colunas(df):
    df = df.rename(columns={
        'Artist': 'Artista',
        'Album': 'Título',
        'Total da conta': 'Lucro líquido',
        'total da conta': 'Lucro líquido',
        'lucro líquido': 'Lucro líquido',
        'Faixa': 'Título',
        # Adicione outros aliases conforme necessidade
    })
    return df

def carregar_arquivos_retroativos(pasta_base, mes_inicio, ano_inicio, mes_fim, ano_fim):
    import os
    import glob

    arquivos = []
    for ano in range(int(ano_inicio), int(ano_fim) + 1):
        for mes in range(1, 13):
            if (ano == int(ano_inicio) and mes < int(mes_inicio)) or \
               (ano == int(ano_fim) and mes > int(mes_fim)):
                continue

            nome_pasta = f"{str(mes).zfill(2)} - {ano}"
            caminho_pasta = os.path.join(pasta_base, nome_pasta)
            if os.path.exists(caminho_pasta):
                arquivos_encontrados = glob.glob(os.path.join(caminho_pasta, "*.xls*")) + \
                                       glob.glob(os.path.join(caminho_pasta, "*.csv"))
                arquivos.extend(arquivos_encontrados)

    return arquivos


def calcular_retroativo_por_artista(
    arquivos,
    artista,
    variacoes,
    titulos_dict,
    cotacao,
    percentual_padrao,
    ano_inicio,
    ano_fim,
    tipo_artista,
    artista_id,
    limiar_fuzzy=90
):
    import pandas as pd
    from decimal import Decimal, ROUND_HALF_UP
    from fuzzywuzzy import fuzz

    total_eur = Decimal("0.0000")

    for caminho in arquivos:
        try:
            df = pd.read_excel(caminho) if caminho.endswith((".xls", ".xlsx")) else pd.read_csv(caminho, sep=None, engine="python")

            col_artista = next((col for col in df.columns if "artista" in col.lower()), None)
            col_titulo = next((col for col in df.columns if "título" in col.lower() or "titulo" in col.lower() or "album" in col.lower()), None)
            col_lucro = next((col for col in df.columns if "lucro" in col.lower()), None)

            if not all([col_artista, col_titulo, col_lucro]):
                print(f"[AVISO] Colunas não encontradas na planilha: {caminho}")
                continue

            df = df[[col_artista, col_titulo, col_lucro]].dropna()
            df.columns = ["artista", "titulo", "lucro"]

            df["artista"] = df["artista"].astype(str).str.strip().str.lower()
            df["titulo"] = df["titulo"].astype(str).str.strip().str.lower()
            df["lucro"] = df["lucro"].astype(str).str.replace(",", ".").str.extract(r"([\d\.]+)")[0].astype(float)

            nomes_planilha = df["artista"].unique()
            print(f"\n[Planilha: {caminho}] Artistas encontrados:")
            for nome in nomes_planilha:
                match = max(fuzz.ratio(nome, v) for v in variacoes)
                print(f" - {nome} → match {match}")

            # Filtra somente linhas com match ≥ limiar
            df_filtrado = df[df["artista"].apply(lambda nome: any(fuzz.ratio(nome, v) >= limiar_fuzzy for v in variacoes))]

            if df_filtrado.empty:
                print(f"[INFO] Nenhum match encontrado para {artista} (ID: {artista_id}) na planilha {caminho}")
                continue

            for _, row in df_filtrado.iterrows():
                lucro = Decimal(str(row["lucro"])).quantize(Decimal("0.0001"))
                titulo = row["titulo"]

                percentual = titulos_dict.get(titulo, percentual_padrao)
                valor_final = (lucro * percentual / 100).quantize(Decimal("0.0001"))
                total_eur += valor_final

        except Exception as e:
            print(f"[ERRO] Falha ao processar {caminho}: {e}")
            continue

    total_brl = (total_eur * Decimal(str(cotacao.valor))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    return {
        'nome': artista,
        'tipo': tipo_artista,
        'periodo': f"{ano_inicio} a {ano_fim}",
        'total_eur': total_eur,
        'total_brl': total_brl
    }

def extrair_ano_arquivo(caminho):
    try:
        nome = os.path.basename(os.path.dirname(caminho))
        return int(nome.split('-')[-1])
    except:
        return 0
