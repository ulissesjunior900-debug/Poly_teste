# processar_retroativos.py
import sys
import os
import pandas as pd
import re
import unicodedata
from decimal import Decimal, getcontext, ROUND_HALF_UP, InvalidOperation
from datetime import datetime
from collections import defaultdict
import logging
from unidecode import unidecode
import glob
import gc
import time
from typing import Dict, Set

# =================================================================
# 1. Configuração e Dependências
# =================================================================

# Configurar logging explicitamente
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Garantir que os handlers não sejam adicionados várias vezes
if not logger.handlers:
    file_handler = logging.FileHandler("retroativos_processing.log", encoding='utf-8')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(stream_handler)

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    pass

# Configurar precisão decimal global para cálculos intermediários
getcontext().prec = 28
getcontext().rounding = ROUND_HALF_UP

# Nomes dos arquivos de entrada
ARQUIVO_ARTISTAS_FILTRO = "artistas_retroativos.txt"

# Mapeamento de colunas alvo para variantes possíveis
COLUNAS_ALVO = {
    "artista": ["nome do artista", "artista", "Artist"],
    "titulo": ["tatulo do lancamento", "titulo do lancamento", " Album"],
    "lucro": ["lucro liquido", "lucro laquido", "Total da conta" , "lucro"],
    "gravadora": ["gravadora", "Gravadora"],
    "mes_relatorio": ["mes do relatorio", "Mes do relatorio" ,  "mes"]
}

# Importar app e db
try:
    from app import app, db
    from models import Artista, ArtistaEspecial
    from retroativos_models import (
        RetroativoCalculado,
        RetroativoArquivo,
        RetroativoTitulo,
        TituloPeriodoValor
    )
    from sqlalchemy import tuple_, func
    from sqlalchemy.orm import sessionmaker

    logger.info("Dependências importadas com sucesso.")
    app.app_context().push()
    logger.info("Contexto da aplicação Flask ativado com sucesso.")
except ImportError as e:
    logger.error(f"Erro de importação: {e}", exc_info=True)
    logger.error("Certifique-se de que o ambiente virtual está ativado e as dependências instaladas.")
    db = None
    app = None
    sys.exit(1)

# =================================================================
# 2. Funções de Utilitário e Normalização
# =================================================================

def remover_acentos(texto):
    """Remove acentos de uma string, usando unidecode."""
    if not isinstance(texto, str):
        return ""
    return unidecode(texto).lower().strip()

def normalizar_nome_artista(nome):
    """
    Normaliza o nome do artista para um formato consistente, removendo
    acentos, caracteres especiais, e variações comuns como "e ou".
    """
    if not nome:
        return ""
    nome_normalizado = remover_acentos(nome)
    # Trata a variação "e ou" e "ou" para garantir consistência
    nome_normalizado = re.sub(r'\s+e\s+ou\s+|\s+ou\s+', ' ', nome_normalizado)
    nome_normalizado = re.sub(r'[^a-z0-9 ]', '', nome_normalizado)
    return ' '.join(nome_normalizado.split()).strip()

def normalizar_coluna(coluna):
    """Normaliza nomes de colunas, removendo acentos e caracteres especiais."""
    coluna = remover_acentos(coluna)
    coluna = re.sub(r"[^a-z0-9 ]", "", coluna)
    return coluna.strip()

def identificar_colunas(df):
    """Identifica as colunas essenciais no DataFrame com base nas variantes."""
    colunas_normalizadas = {normalizar_coluna(c): c for c in df.columns}
    mapeamento = {}
    for chave, variantes in COLUNAS_ALVO.items():
        for variante in variantes:
            variante_normalizada = normalizar_coluna(variante)
            if variante_normalizada in colunas_normalizadas:
                mapeamento[chave] = colunas_normalizadas[variante_normalizada]
                break
    if "artista" in mapeamento and "lucro" in mapeamento:
        return mapeamento
    else:
        logger.error(f"Não foi possível identificar as colunas 'artista' ou 'lucro'.")
        logger.debug(f"Colunas normalizadas disponíveis: {list(colunas_normalizadas.keys())}")
        return None

def parse_valor(valor_raw):
    """Converte um valor de string para Decimal, garantindo precisão."""
    if valor_raw is None:
        return Decimal("0")
    if not isinstance(valor_raw, str):
        valor_raw = str(valor_raw)
    valor_raw = valor_raw.replace(",", ".").replace("€", "").strip()
    valor_raw = re.sub(r"\s+", "", valor_raw)
    try:
        return Decimal(valor_raw)
    except InvalidOperation:
        return Decimal("0")

def carregar_artistas_para_filtro(caminho_arquivo: str) -> Set[str]:
    """
    Carrega nomes de artistas de um arquivo de texto para serem usados como filtro.
    Retorna um conjunto de nomes normalizados.
    """
    artistas_para_filtrar = set()
    if not os.path.exists(caminho_arquivo):
        logger.warning(f"Arquivo de filtro de artistas não encontrado: '{caminho_arquivo}'. Nenhum filtro será aplicado.")
        return artistas_para_filtrar
    
    with open(caminho_arquivo, 'r', encoding='utf-8') as f:
        for linha in f:
            nome_original = linha.strip()
            if nome_original:
                artistas_para_filtrar.add(normalizar_nome_artista(nome_original))
    
    logger.info(f"Carregados {len(artistas_para_filtrar)} artistas do arquivo de filtro.")
    return artistas_para_filtrar

def obter_mapeamento_artistas(ano_alvo: int, artistas_para_filtrar: Set[str]) -> Dict[str, str]:
    """
    Melhoria na lógica: Cria um mapeamento robusto de nomes de artistas da planilha para
    nomes canónicos do banco de dados, a partir dos dados já salvos, com maior
    tolerância a variações. Apenas considera artistas do conjunto de filtro.
    """
    logger.info("Iniciando a criação do mapeamento de artistas...")
    
    mapeamento = {}
    nao_mapeados = set()

    # Mapeia nomes canônicos do banco de dados para suas versões normalizadas
    artistas_canonic_map = {normalizar_nome_artista(a.nome): a.nome for a in Artista.query.all()}
    artistas_canonic_map.update({normalizar_nome_artista(a.nome): a.nome for a in ArtistaEspecial.query.all()})

    # Busca nomes de artistas nas planilhas já processadas, mas apenas dos artistas do filtro
    if artistas_para_filtrar:
        artistas_planilhas_query = db.session.query(RetroativoCalculado.artista).filter_by(ano=ano_alvo).distinct()
        artistas_planilhas = {a.artista for a in artistas_planilhas_query}
    else:
        # Se não houver filtro, não precisamos de mapeamento para esta etapa
        return {}
    
    # Itera sobre os nomes encontrados nas planilhas E no arquivo de filtro
    for nome_planilha_original in artistas_planilhas:
        nome_planilha_norm = normalizar_nome_artista(nome_planilha_original)
        
        # Ignora artistas que não estão no filtro
        if artistas_para_filtrar and nome_planilha_norm not in artistas_para_filtrar:
            continue
        
        match_encontrado = False
        
        # 1. Tenta correspondência exata (normalizada)
        if nome_planilha_norm in artistas_canonic_map:
            mapeamento[nome_planilha_original] = artistas_canonic_map[nome_planilha_norm]
            match_encontrado = True
            logger.debug(f"Correspondência exata: '{nome_planilha_original}' -> '{mapeamento[nome_planilha_original]}'")
        
        # 2. Se não houver correspondência exata, tenta correspondência de sub-string
        if not match_encontrado:
            for nome_canonico_norm, nome_canonico_original in artistas_canonic_map.items():
                if nome_planilha_norm in nome_canonico_norm or nome_canonico_norm in nome_planilha_norm:
                    mapeamento[nome_planilha_original] = nome_canonico_original
                    match_encontrado = True
                    logger.debug(f"Correspondência parcial: '{nome_planilha_original}' -> '{nome_canonico_original}'")
                    break
        
        # 3. Se nenhuma correspondência for encontrada, usa o nome original
        if not match_encontrado:
            mapeamento[nome_planilha_original] = nome_planilha_original
            nao_mapeados.add(nome_planilha_original)
            logger.debug(f"Nenhum mapeamento: '{nome_planilha_original}'")

    if nao_mapeados:
        logger.warning(f"⚠️ {len(nao_mapeados)} artistas das planilhas não foram encontrados no banco de dados e serão processados com os nomes originais.")
    
    logger.info("Mapeamento de artistas concluído.")
    return mapeamento

# =================================================================
# 3. Processamento de Arquivos
# =================================================================

def processar_arquivo_unificado(caminho: str, ano: int, mes_padrao: int, artistas_para_filtrar: Set[str]):
    """
    Função unificada para processar arquivos, com filtragem da gravadora "Rozenblit"
    e agora com filtro de artistas.
    """
    nome_arquivo = os.path.basename(caminho)
    logger.info(f"Iniciando processamento: {nome_arquivo}")
    
    df = None
    try:
        if caminho.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(caminho, dtype=str, engine='openpyxl')
        else: # Assumir CSV
            try:
                df = pd.read_csv(caminho, sep=';', thousands='.', decimal=',', encoding='utf-8', dtype=str, on_bad_lines='skip')
            except Exception:
                df = pd.read_csv(caminho, sep=';', thousands='.', decimal=',', encoding='latin-1', dtype=str, on_bad_lines='skip', engine='python')
    except Exception as e:
        logger.error(f"Erro ao ler {nome_arquivo}: {e}")
        return [], 0

    if df is None or df.empty:
        logger.warning(f"Arquivo {nome_arquivo} vazio ou inválido.")
        return [], 0

    colunas = identificar_colunas(df)
    if not colunas:
        logger.error(f"Colunas essenciais não identificadas no arquivo: {nome_arquivo}")
        return [], len(df)

    col_artista = colunas["artista"]
    col_lucro = colunas["lucro"]
    col_titulo = colunas.get("titulo")
    col_gravadora = colunas.get("gravadora")
    col_mes_relatorio = colunas.get("mes_relatorio")
    
    logger.info(f"Colunas identificadas para '{nome_arquivo}': {colunas}")
    
    registros = []
    linhas_invalidas = 0
    linhas_filtradas_rozenblit = 0
    linhas_filtradas_artista = 0

    df_processar = df[df[col_artista].notna() & df[col_lucro].notna()].copy()
    linhas_invalidas += len(df) - len(df_processar)

    for _, row in df_processar.iterrows():
        try:
            nome_artista_planilha = str(row[col_artista]).strip()
            nome_artista_normalizado = normalizar_nome_artista(nome_artista_planilha)

            # LÓGICA DE FILTRAGEM 1: Artista
            if artistas_para_filtrar and nome_artista_normalizado not in artistas_para_filtrar:
                linhas_filtradas_artista += 1
                continue

            # LÓGICA DE FILTRAGEM 2: Gravadora "Rozenblit"
            if col_gravadora and str(row.get(col_gravadora, '')).lower().strip() == 'rozenblit':
                linhas_filtradas_rozenblit += 1
                continue

            valor = parse_valor(row[col_lucro])
            if valor == 0:
                linhas_invalidas += 1
                continue

            mes_final = mes_padrao
            if col_mes_relatorio:
                valor_mes_coluna = str(row.get(col_mes_relatorio, '')).strip()
                if valor_mes_coluna:
                    data_parseada = None
                    for fmt in ('%d/%m/%Y', '%d/%m/%y', '%Y-%m-%d', '%m/%Y', '%m/%y', '%Y/%m/%d', '%Y-%m-%d %H:%M:%S'):
                        try:
                            data_parseada = datetime.strptime(valor_mes_coluna, fmt)
                            break
                        except ValueError:
                            continue
                    
                    if data_parseada:
                        mes_final = data_parseada.month

            registros.append(RetroativoCalculado(
                artista=nome_artista_planilha,
                titulo=str(row.get(col_titulo, "")).strip(),
                lucro_liquido=valor,
                ano=int(ano),
                mes=int(mes_final),
                origem_planilha=nome_arquivo
            ))
        except Exception as e:
            logger.warning(f"Linha inválida ignorada em '{nome_arquivo}': {row.to_dict()}. Erro: {e}")
            linhas_invalidas += 1

    logger.info(f"Processamento de '{nome_arquivo}' concluído. Linhas válidas: {len(registros)}, Linhas filtradas (Rozenblit): {linhas_filtradas_rozenblit}, Linhas filtradas (Artista): {linhas_filtradas_artista}, Linhas inválidas: {linhas_invalidas}")
    return registros, (linhas_invalidas + linhas_filtradas_rozenblit + linhas_filtradas_artista)

def processar_arquivos_retroativos(ano_alvo: int, artistas_para_filtrar: Set[str], pasta_base="static/uploads/retroativos"):
    """
    Processa todos os arquivos de retroativos para um ano específico,
    salvando os dados no banco de dados após a leitura de cada arquivo.
    """
    subpasta_ano = None
    subpastas = glob.glob(os.path.join(pasta_base, f"*{ano_alvo}*"))
    if subpastas:
        subpasta_ano = subpastas[0]
    
    if not subpasta_ano or not os.path.isdir(subpasta_ano):
        logger.error(f"Não foi encontrada uma pasta para o ano {ano_alvo} em '{pasta_base}'.")
        return set()

    logger.info(f"Pasta do ano {ano_alvo} encontrada: '{subpasta_ano}'.")
    
    todos_titulos = set()
    total_registros_salvos = 0
    total_arquivos_processados = 0

    arquivos_encontrados = sorted(os.listdir(subpasta_ano))
    logger.info(f"Encontrados {len(arquivos_encontrados)} arquivos na pasta '{subpasta_ano}'.")

    for nome_arquivo in arquivos_encontrados:
        caminho_completo = os.path.join(subpasta_ano, nome_arquivo)
        
        if nome_arquivo.lower() in ('thumbs.db', '.ds_store'):
            logger.warning(f"Arquivo ignorado: {nome_arquivo}")
            continue

        mes_do_nome_arquivo = 0
        if nome_arquivo.split(' ')[0].isdigit():
            mes_do_nome_arquivo = int(nome_arquivo.split(' ')[0])

        registros_do_arquivo, registros_invalidos = processar_arquivo_unificado(caminho_completo, ano_alvo, mes_do_nome_arquivo, artistas_para_filtrar)
        
        if registros_do_arquivo:
            try:
                db.session.bulk_save_objects(registros_do_arquivo)
                arquivo_salvo = RetroativoArquivo(
                    nome=nome_arquivo,
                    nome_arquivo=nome_arquivo,
                    ano=ano_alvo,
                    mes=mes_do_nome_arquivo,
                    registros_validos=len(registros_do_arquivo),
                    registros_invalidos=registros_invalidos
                )
                db.session.add(arquivo_salvo)
                db.session.commit()
                logger.info(f"💾 Dados de '{nome_arquivo}' salvos com sucesso.")
                total_registros_salvos += len(registros_do_arquivo)
                total_arquivos_processados += 1
            except Exception as e:
                db.session.rollback()
                logger.error(f"Erro ao salvar dados de '{nome_arquivo}': {e}")
            
            for r in registros_do_arquivo:
                if r.titulo:
                    todos_titulos.add((r.artista, r.titulo))
    
    logger.info(f"Total de arquivos processados: {total_arquivos_processados}")
    logger.info(f"Total de registros processados e salvos: {total_registros_salvos}")

    return todos_titulos

# =================================================================
# 4. Função Principal e Relatório
# =================================================================

def main(ano_alvo: int):
    """
    Função principal que orquestra o processamento e a geração do relatório.
    """
    if db is None or app is None:
        logger.error("A aplicação Flask ou o banco de dados não foram inicializados. Verifique as dependências.")
        return

    with app.app_context():
        try:
            db.create_all()
            logger.info("Tabelas de retroativos criadas/garantidas com sucesso!")
        except Exception as e:
            logger.error(f"Erro ao criar as tabelas do banco de dados: {e}")
            return
        
        # Carregar a lista de artistas para filtro antes de qualquer processamento
        artistas_para_filtrar = carregar_artistas_para_filtro(ARQUIVO_ARTISTAS_FILTRO)
        if not artistas_para_filtrar:
            logger.warning("Nenhum artista encontrado no arquivo de filtro. O script continuará sem filtrar por artista.")

        # Limpar dados antigos
        db.session.query(RetroativoCalculado).filter_by(ano=ano_alvo).delete()
        db.session.query(RetroativoArquivo).filter_by(ano=ano_alvo).delete()
        logger.info(f"Iniciando limpeza de dados antigos para o ano {ano_alvo}...")
        db.session.commit()
        logger.info(f"Limpeza de dados do ano {ano_alvo} concluída.")

        # Processar arquivos e salvar em lote
        todos_titulos = processar_arquivos_retroativos(ano_alvo, artistas_para_filtrar)

        # Buscar todos os registros do banco de dados para criar o mapeamento e o relatório
        logger.info("Iniciando a busca e consolidação dos dados para o relatório...")
        artista_mapeamento = obter_mapeamento_artistas(ano_alvo, artistas_para_filtrar)

        if todos_titulos:
            novos_titulos = []
            titulos_existentes_count = 0
            
            existentes_no_banco = set()
            for artista, titulo in db.session.query(RetroativoTitulo.artista_nome, RetroativoTitulo.titulo).all():
                existentes_no_banco.add((normalizar_nome_artista(artista), normalizar_nome_artista(titulo)))
            
            titulos_para_inserir = set()

            for artista_planilha, titulo_planilha in todos_titulos:
                nome_canonico = artista_mapeamento.get(normalizar_nome_artista(artista_planilha), artista_planilha)
                normalizado_key = (normalizar_nome_artista(nome_canonico), normalizar_nome_artista(titulo_planilha))
                
                if normalizado_key in existentes_no_banco or normalizado_key in titulos_para_inserir:
                    titulos_existentes_count += 1
                else:
                    novos_titulos.append(RetroativoTitulo(
                        artista_nome=nome_canonico,
                        titulo=titulo_planilha
                    ))
                    titulos_para_inserir.add(normalizado_key)
            
            if novos_titulos:
                try:
                    db.session.bulk_save_objects(novos_titulos)
                    db.session.commit()
                    logger.info(f"💾 Salvos {len(novos_titulos)} novos títulos")
                except Exception as e:
                    logger.error(f"Erro ao salvar novos títulos: {e}")
                    db.session.rollback()
            logger.info(f"📊 Títulos já existentes (no banco ou neste lote): {titulos_existentes_count}")
        else:
            logger.warning("Nenhum título válido encontrado nos arquivos")

        # Chama a função de relatório otimizada, que consulta o DB de forma eficiente
        consolidar_e_gerar_relatorio(ano_alvo, artista_mapeamento)
        
        logger.info("Processamento concluído com sucesso!")

def consolidar_e_gerar_relatorio(ano_alvo: int, artista_mapeamento: Dict[str, str]):
    """
    Consolida os dados processados e gera um relatório,
    usando consultas agregadas no banco de dados para otimização de memória.
    """
    logger.info("="*50)
    logger.info(f"RELATÓRIO CONSOLIDADO DO ANO {ano_alvo}")
    logger.info("="*50)
    
    # Consulta agregada no banco de dados para consolidar os dados
    consolidado_db = db.session.query(
        RetroativoCalculado.artista,
        RetroativoCalculado.mes,
        func.sum(RetroativoCalculado.lucro_liquido)
    ).filter_by(
        ano=ano_alvo
    ).group_by(
        RetroativoCalculado.artista,
        RetroativoCalculado.mes
    ).order_by(
        RetroativoCalculado.artista,
        RetroativoCalculado.mes
    ).all()

    if not consolidado_db:
        logger.info("Nenhum dado financeiro processado para o relatório.")
        logger.info("="*50)
        return

    artistas_totais = defaultdict(Decimal)
    artistas_mensal = defaultdict(lambda: defaultdict(Decimal))
    
    meses_nomes = {
        1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
        7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez"
    }

    for artista_planilha, mes, valor in consolidado_db:
        nome_planilha_norm = normalizar_nome_artista(artista_planilha)
        # Usa o mapeamento inteligente para obter o nome canônico
        nome_canonico = artista_mapeamento.get(nome_planilha_norm, artista_planilha)
        
        artistas_totais[nome_canonico] += valor
        artistas_mensal[nome_canonico][mes] = valor
        
    for artista in sorted(artistas_totais.keys()):
        # Arredonda para 4 casas decimais para manter a precisão
        total_anual_artista = artistas_totais[artista].quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
        log_mensal = []
        for mes_num in range(1, 13):
            mes_nome = meses_nomes.get(mes_num, str(mes_num))
            # Arredonda para 4 casas decimais para manter a precisão
            valor_mes = artistas_mensal[artista].get(mes_num, Decimal(0)).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
            log_mensal.append(f"{mes_nome}: €{valor_mes}")
        
        logger.info(f"- {artista}: {', '.join(log_mensal)}, Total Anual: €{total_anual_artista}")
    
    # Consulta o total geral de forma otimizada
    total_geral_full_precision = db.session.query(func.sum(RetroativoCalculado.lucro_liquido)).filter_by(ano=ano_alvo).scalar()
    if total_geral_full_precision is None:
        total_geral_full_precision = Decimal(0)
    else:
        total_geral_full_precision = Decimal(str(total_geral_full_precision))

    # Arredonda para 4 casas decimais para o relatório
    total_geral_rounded = total_geral_full_precision.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
    logger.info(f"\nTOTAL GERAL DO ANO {ano_alvo}: €{total_geral_rounded} (Precisão Total: {total_geral_full_precision})")
    
    logger.info("="*50)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        logger.error("Uso: python processar_retroativos.py <ano>")
        sys.exit(1)
    
    try:
        ano = int(sys.argv[1])
        main(ano)
    except ValueError:
        logger.error("O ano deve ser um número inteiro.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Ocorreu um erro inesperado: {e}", exc_info=True)
        sys.exit(1)
