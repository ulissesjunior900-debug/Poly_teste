# ===== Flask =====
from flask import (
    Flask, render_template, request, redirect, url_for, flash, session,
    jsonify, send_file, current_app, make_response, send_from_directory, abort
)

# ===== Extensões Flask =====
from flask_migrate import Migrate
from flask_wtf import CSRFProtect, FlaskForm
from flask import send_file, render_template_string
from flask import send_file, abort



# ===== Formulários =====
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired
from collections import defaultdict
from sqlalchemy import func

# ===== Segurança & Uploads =====
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# ===== SQLAlchemy & Sistema =====
from sqlalchemy import text
from pathlib import Path
from functools import wraps
import os
import unicodedata
import shutil
import traceback
from pathlib import Path
from pdf2image import convert_from_path
import base64
import sqlite3

# ===== Manipulação de Arquivos =====
import zipfile
from io import BytesIO
from decimal import Decimal, getcontext, ROUND_HALF_UP
import pandas as pd
from openpyxl import load_workbook
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import pythoncom
import win32com.client as win32
from PIL import Image
from jinja2 import Template
from PyPDF2 import PdfReader, PdfWriter
import pdfkit
import tempfile
import subprocess
import fitz
import json
from werkzeug.security import generate_password_hash # Certifique-se de importar isso no topo do seu arquivo
from flask import current_app
from sqlalchemy import func

# ===== RapidFuzz (fuzzy match) =====
from rapidfuzz.fuzz import token_sort_ratio
from rapidfuzz import fuzz

# ===== Pasta onde imagens convertidas das SPs serão salvas =====
IMAGEM_FOLDER = os.path.join('static', 'sp_convertidos')

POPPLER_PATH = r'C:\poppler\Library\bin'

# ===== App e Blueprints =====
from flask import Blueprint

# ===== utils_sp =====
from utils_sp import preencher_sp_dinamicamente, gerar_sp_pdf_com_preenchimento

# ===== utils.artistas_base =====
from artistas_base_utils import atualizar_base_artistas

# ===== utils =====
from utils import buscar_nome_artista, atualizar_historico_pagamentos

# ===== Helpers =====
from helpers import (
    construir_calculos_disponiveis,
    sanitize_nome,
    formatar_valor,
    calcular_data_cotacao,
    mes_nome,
    normalizar_texto,
    remover_acentos
)

# ===== Modelos =====
from models import (
    db,
    Artista,
    ArquivoImportado,
    CalculoSalvo,
    ArtistaEspecial,
    TituloEspecial,
    Cotacao,
    CalculoEspecialSalvo,
    CalculoAssisaoSalvo,
    SPImportada,
    SolicitacaoPagamento,
    PagamentoRealizado,
    Herdeiro,
    Usuario,
    Transacao,
    ArtistaInfo,
)

from retroativos_models import RetroativoCalculado, RetroativoArquivo, RetroativoTitulo, TituloPeriodoValor

# ===== forms =====
from forms import UsuarioForm

# ===== Pasta onde as SPs ficarão salvas =====
diretorio_sps = os.path.join('static', 'uploads', 'sps')
os.makedirs(diretorio_sps, exist_ok=True)

# Dicionário de meses para exibição (no singular conforme seu uso)
nome_meses = {
    '01': 'Jan', '02': 'Fev', '03': 'Mar', '04': 'Abr',
    '05': 'Mai', '06': 'Jun', '07': 'Jul', '08': 'Ago',
    '09': 'Set', '10': 'Out', '11': 'Nov', '12': 'Dez'
}

# ===== Inicialização do app =====
app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + str(Path(__file__).parent / 'instance' / 'polymusic.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')

# Caminho absoluto para garantir que funcione independente do diretório atual
# DB de retroativos via bind
retroativos_db_path = Path(__file__).parent / 'instance' / 'retroativos.db'
app.config['SQLALCHEMY_BINDS'] = {
    'retroativos': f'sqlite:///{retroativos_db_path}'
}

# ===== Inicialização de extensões =====
db.init_app(app)
migrate = Migrate(app, db)
csrf = CSRFProtect(app)

# ===== Inicialização do banco de retroativos =====
with app.app_context():

    from retroativos_models import RetroativoCalculado, RetroativoArquivo

    os.makedirs(app.instance_path, exist_ok=True)

    if not retroativos_db_path.exists():
        print("Criando banco de dados de retroativos…")
    else:
        print(" Banco de retroativos já existe, garantindo tabelas…")

    # Criação das tabelas apenas do bind 'retroativos'
    engine = db.get_engine(app, bind='retroativos')
    db.Model.metadata.create_all(bind=engine)

    print(" Tabelas de retroativos criadas/garantidas com sucesso!")

# 4. Formulário de Login
class LoginForm(FlaskForm):
    username = StringField('Usuário', validators=[DataRequired()])
    password = PasswordField('Senha', validators=[DataRequired()])
    submit = SubmitField('Entrar')

# 5. Rota de Login
@app.route('/', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        usuario = Usuario.query.filter_by(username=form.username.data).first()
        if usuario and usuario.verificar_senha(form.password.data):
            session['usuario_id'] = usuario.id
            session['usuario_nome'] = usuario.username
            return redirect(url_for('inicio'))  # Certifique-se de ter a rota 'inicio'
        else:
            flash('Usuário ou senha inválidos.', 'danger')
    return render_template('login.html', form=form)


# 4. Criação e verificação
with app.app_context():
    db_path = Path(app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', ''))

    if not db_path.exists():
        print("Criando banco de dados...")
        os.makedirs(db_path.parent, exist_ok=True)
        db.create_all()
        print(" Banco de dados criado com sucesso!")
    else:
        print(" Banco de dados já existe")
        # db.create_all() # Removido: db.create_all() dentro do else pode causar problemas com migrações
                          # Ele tenta criar tabelas que já existem. Use Alembic para atualizações.

    #  IMPORTANTE: A verificação/criação manual da tabela 'usuario' não é recomendada
    # quando se usa Flask-Migrate. O Flask-Migrate (Alembic) gerencia a criação
    # e atualização de tabelas. Se você excluiu o DB e vai usar 'flask db upgrade',
    # a tabela será criada pela migração. Se você *não* vai usar migrações, então db.create_all()
    # logo acima é o suficiente para criar todas as tabelas.
    # Vou comentar esta seção para priorizar o fluxo do Alembic.
    # if 'usuario' not in db.inspect(db.engine).get_table_names():
    #     print(" Tabela 'usuario' não existe, criando manualmente...")
    #     Usuario.__table__.create(db.engine)

    try:
        db.session.execute(text("SELECT 1"))
        print(" Conexão testada com sucesso")
    except Exception as e:
        print(f" Falha na conexão: {e}")

    try:
        # Certifique-se de que generate_password_hash está importado (ex: from werkzeug.security import generate_password_hash)
        if not Usuario.query.filter_by(username='admin').first():
            admin = Usuario(
                username='admin',
                senha=generate_password_hash('1234'), # CORRIGIDO: usa 'senha'
                funcao='admin',                     # CORRIGIDO: usa 'funcao'
                nome='Administrador',               # ADICIONADO: campo NOT NULL
                email='admin@seusite.com'           # ADICIONADO: campo NOT NULL e UNIQUE
            )
            db.session.add(admin)
            db.session.commit()
            print(" Usuário admin criado com sucesso!")
        else:
            print(" Usuário admin já existe.")
    except Exception as e:
        print(" Erro ao verificar/criar admin:", e)


ALLOWED_EXTENSIONS = {'.xlsx', '.xls', '.csv'}

@app.template_filter("format_eur")
def format_eur_filter(value):
    try:
        return f"€ {float(value):,.4f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return value

@app.template_filter("format_brl")
def format_brl_filter(value):
    try:
        return f"R$ {float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return value



def normalizar_string(texto):
    return unidecode(str(texto).strip().lower())

def fuzzy_match(a, b):
    return token_sort_ratio(normalizar_string(a), normalizar_string(b))

def carregar_planilha(caminho):
    import pandas as pd
    ext = os.path.splitext(caminho)[1].lower()

    if ext == '.csv':
        try:
            return pd.read_csv(caminho, sep=None, engine='python', encoding='utf-8', on_bad_lines='skip')
        except Exception:
            # tenta com outro encoding
            return pd.read_csv(caminho, sep=None, engine='python', encoding='latin1', on_bad_lines='skip')
    elif ext in ['.xls', '.xlsx']:
        return pd.read_excel(caminho)
    else:
        raise Exception("Formato de arquivo não suportado. Use XLSX, XLS ou CSV.")

def normalizar_texto(texto):
    if not isinstance(texto, str):
        return ""
    texto = texto.lower().strip()
    texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')
    texto = ''.join(c for c in texto if c.isalnum() or c.isspace())
    return texto.strip()

def encontrar_coluna(df, nome_alvo):
    nome_alvo = normalizar_texto(nome_alvo)
    for col in df.columns:
        if normalizar_texto(col) == nome_alvo:
            return col
    return None

def remover_acentos(texto):
    if not isinstance(texto, str):
        return texto
    return ''.join(
        c for c in unicodedata.normalize('NFKD', texto)
        if not unicodedata.combining(c)
    )

def titulo_corresponde(titulo_planilha, titulo_cadastrado):
    titulo1 = normalizar_texto(titulo_planilha)
    titulo2 = normalizar_texto(titulo_cadastrado)
    return fuzz.token_sort_ratio(titulo1, titulo2) >= 90

def nome_corresponde(nome_planilha, artista_obj):
    nome_planilha = normalizar_texto(nome_planilha)
    nomes_validos = [normalizar_texto(artista_obj.nome)] + artista_obj.obter_variacoes()

    for nome_valid in nomes_validos:
        nome_cad = normalizar_texto(nome_valid)
        if nome_planilha == nome_cad:
            return True
        if nome_cad in nome_planilha or nome_planilha in nome_cad:
            return True
        partes_plan = nome_planilha.split()
        partes_cad = nome_cad.split()
        if all(any(fuzz.ratio(p_cad, p_plan) >= 85 for p_plan in partes_plan) for p_cad in partes_cad):
            return True
        if fuzz.token_sort_ratio(nome_planilha, nome_cad) >= 90:
            return True
    return False

def converter_lucro(valor):
    try:
        return Decimal(str(valor).replace(",", ".")).quantize(Decimal("0.00000000000001"))
    except:
        return Decimal("0.00000000000000")

def calcular_valores_especiais(df, titulos_dict, cotacao_valor, limiar_fuzzy=90):
    """
    Calcula os valores com fuzzy matching nos títulos (≥ 90% de similaridade).
    Versão atualizada com precisão decimal ajustada para corresponder exatamente à planilha.
    
    Args:
        df: DataFrame com os dados
        titulos_dict: Dicionário com títulos e percentuais
        cotacao_valor: Valor da cotação EUR-BRL
        limiar_fuzzy: Limiar de similaridade (default 90)
    
    Returns:
        Tuple: (total_eur, total_brl) com precisão correta
    """
    # Configuração de precisão decimal
    getcontext().prec = 20
    getcontext().rounding = ROUND_HALF_UP

    # Verificação de colunas obrigatórias
    if 'titulo_normalizado' not in df.columns or 'lucro' not in df.columns:
        raise Exception('Colunas obrigatórias ausentes no DataFrame.')

    # Normalização dos valores de lucro para 4 casas decimais
    df['lucro'] = df['lucro'].apply(lambda x: Decimal(str(x)).quantize(Decimal('0.0001')))

    total_eur = Decimal('0')
    usados = []
    matches = []

    print("\n COMPARAÇÃO FUZZY ENTRE TÍTULOS CADASTRADOS E PLANILHA:")

    for titulo_original, percentual in titulos_dict.items():
        titulo_cad_norm = normalizar_texto(titulo_original)

        try:
            # Normalização do percentual
            percentual_str = str(percentual).replace(',', '.').strip()
            percentual_decimal = Decimal(percentual_str)
        except (InvalidOperation, ValueError):
            print(f"[ERRO] Percentual inválido para '{titulo_original}': '{percentual}' — ignorado.")
            continue

        match_encontrado = False
        for titulo_plan in df['titulo_normalizado'].unique():
            similaridade = fuzz.token_sort_ratio(titulo_cad_norm, titulo_plan)
            if similaridade >= limiar_fuzzy:
                linhas = df[df['titulo_normalizado'] == titulo_plan]
                # Soma com precisão de 4 casas decimais
                lucro_total = linhas['lucro'].sum().quantize(Decimal('0.0001'))
                # Cálculo com arredondamento preciso
                valor_aplicado = (lucro_total * (percentual_decimal / Decimal('100'))).quantize(Decimal('0.0001'))
                total_eur += valor_aplicado
                usados.append(titulo_plan)
                match_encontrado = True
                
                # Registro detalhado para verificação
                matches.append({
                    'cadastrado': titulo_original,
                    'planilha': titulo_plan,
                    'similaridade': similaridade,
                    'lucro_total': lucro_total,
                    'percentual': percentual_decimal,
                    'valor_aplicado': valor_aplicado
                })
                
                print(f"[MATCH] '{titulo_cad_norm}' ≈ '{titulo_plan}' ({similaridade}%) | " +
                      f"Lucro: €{lucro_total} | %: {percentual_decimal} | " +
                      f"Subtotal: €{valor_aplicado}")
                break

        if not match_encontrado:
            print(f"[IGNORADO] '{titulo_cad_norm}' não encontrou match ≥ {limiar_fuzzy}%")

    # Cálculo final com arredondamento preciso
    total_brl = (total_eur * Decimal(str(cotacao_valor))).quantize(Decimal('0.01'))
    total_eur_final = total_eur.quantize(Decimal('0.0001'))

    # Log de verificação decimal
    print("\n VERIFICAÇÃO DECIMAL:")
    if matches:
        primeiro_match = matches[0]
        print(f"Exemplo de cálculo: €{primeiro_match['lucro_total']} * {primeiro_match['percentual']}% = €{primeiro_match['valor_aplicado']}")
    
    print(f"\n TOTAL FINAL: €{total_eur_final} | R$ {total_brl}")
    
    return total_eur_final, total_brl

def calcular_valores_assisao(df_original, artista_obj, titulos_dict, cotacao_valor):
    df = df_original.copy()
    df['nome_artista_normalizado'] = df['nome_artista_normalizado'].astype(str).apply(normalizar_texto)
    df['titulo_normalizado'] = df['titulo_normalizado'].astype(str).apply(normalizar_texto)
    df['lucro'] = df['lucro'].apply(converter_lucro)

    # Filtra somente os nomes do artista (com variações)
    df_filtrado = df[df['nome_artista_normalizado'].apply(lambda nome: nome_corresponde(nome, artista_obj))].copy()

    resultados = []

    for titulo_original, percentual in titulos_dict.items():
        percentual_str = str(percentual).replace('%', '').replace(',', '.').strip()

        try:
            percentual_decimal = Decimal(percentual_str)
        except:
            continue

        for titulo_plan in df_filtrado['titulo_normalizado'].unique():
            if titulo_corresponde(titulo_plan, titulo_original):
                linhas = df_filtrado[df_filtrado['titulo_normalizado'] == titulo_plan]
                lucro_total = linhas['lucro'].sum().quantize(Decimal('0.00000000000001'))
                valor_aplicado = (lucro_total * percentual_decimal / Decimal('100')).quantize(Decimal('0.00000000000001'))
                valor_brl = (valor_aplicado * Decimal(str(cotacao_valor))).quantize(Decimal('0.01'))

                resultados.append({
                    'titulo': titulo_original,
                    'valor_eur': valor_aplicado,
                    'valor_brl': valor_brl,
                    'lucro_total': lucro_total,
                    'percentual': percentual_decimal,
                    'match': titulo_plan
                })
                break  # para evitar múltiplas contagens do mesmo título

    total_eur = sum([r['valor_eur'] for r in resultados]).quantize(Decimal('0.0001'))
    total_brl = (total_eur * Decimal(str(cotacao_valor))).quantize(Decimal('0.01'))

    return total_eur, total_brl, resultados

def normalizar_texto(texto):
    """
    Normaliza texto para comparação fuzzy
    """
    if not isinstance(texto, str):
        return ""
    return texto.lower().strip()

def validar_arquivo_sp(caminho):
    """Valida se o caminho do arquivo .xlsx é real e bem formatado"""
    if not caminho or not isinstance(caminho, str):
        return False, "Caminho inválido ou vazio."

    caminho_real = os.path.abspath(caminho)

    if not os.path.exists(caminho_real):
        return False, f"Arquivo não encontrado: {caminho_real}"

    if not caminho_real.lower().endswith('.xlsx'):
        return False, f"O arquivo não tem extensão .xlsx: {caminho_real}"

    nome = os.path.basename(caminho_real)
    if nome.strip() != nome:
        return False, f"Nome do arquivo possui espaços extras: [{nome}]"

    return True, caminho_real


def construir_calculos_disponiveis():
    from models import CalculoSalvo, CalculoEspecialSalvo, CalculoAssisaoSalvo

    nome_meses = {
        1: 'Janeiro', 2: 'Fevereiro', 3: 'Março',
        4: 'Abril', 5: 'Maio', 6: 'Junho',
        7: 'Julho', 8: 'Agosto', 9: 'Setembro',
        10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
    }

    calculos = []

    def processar_calculo(c, tipo):
        try:
            valor_eur = float(c.valor_eur or 0)
            valor_brl = float(c.valor_brl or 0)

            mes_int = None
            mes_str = str(c.mes).strip().capitalize() if c.mes else ''
            if mes_str.isdigit():
                mes_int = int(mes_str)
            else:
                mes_map = {
                    'Janeiro': 1, 'Fevereiro': 2, 'Março': 3,
                    'Abril': 4, 'Maio': 5, 'Junho': 6,
                    'Julho': 7, 'Agosto': 8, 'Setembro': 9,
                    'Outubro': 10, 'Novembro': 11, 'Dezembro': 12
                }
                mes_int = mes_map.get(mes_str)

            mes_nome = nome_meses.get(mes_int, '-') if mes_int else '-'

            # Pega diretamente o nome do artista associado
            artista_nome = 'Artista desconhecido'
            if hasattr(c, 'artista') and c.artista:
                artista_nome = c.artista if isinstance(c.artista, str) else getattr(c.artista, 'nome', 'Artista desconhecido')
            elif hasattr(c, 'artista_especial') and c.artista_especial:
                artista_nome = getattr(c.artista_especial, 'nome', 'Artista desconhecido')

            herdeiros = []
            if hasattr(c, 'herdeiros') and isinstance(c.herdeiros, list):
                herdeiros = [
                    {'nome': h.get('nome', 'Herdeiro'), 'valor': float(h.get('valor', 0))}
                    for h in c.herdeiros
                ]

            return {
                'id': c.id,
                'tipo': tipo,
                'origem': tipo,
                'artista': artista_nome,
                'mes': mes_int,
                'mes_nome': mes_nome,
                'ano': str(c.ano or ''),
                'valor_eur': round(valor_eur, 4),
                'valor_brl': round(valor_brl, 2),
                'cotacao': float(getattr(c, 'cotacao', 0)),
                'status': getattr(c, 'status', 'aguardando').lower(),
                'data_pagamento': c.data_pagamento.strftime('%d/%m/%Y') if getattr(c, 'data_pagamento', None) else '',
                'herdeiros': herdeiros,
                'data_calculo': getattr(c, 'data_calculo', None)
            }

        except Exception as e:
            print(f"[ERRO] ao processar cálculo ID {getattr(c, 'id', '?')}: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    for model, tipo in [
        (CalculoSalvo, 'norm'), 
        (CalculoEspecialSalvo, 'esp'),
        (CalculoAssisaoSalvo, 'ass')
    ]:
        try:
            registros = model.query.order_by(model.id.desc()).all()
            for c in registros:
                calc = processar_calculo(c, tipo)
                if calc:
                    calculos.append(calc)
        except Exception as e:
            print(f"[ERRO] ao consultar {model.__name__}: {str(e)}")

    print(f"[DEBUG] {len(calculos)} cálculos carregados.")
    return calculos

def formatar_valor(valor, casas=2):
    return f"{Decimal(valor).quantize(Decimal('1.' + '0' * casas), rounding=ROUND_HALF_UP)}"

def formatar_data(data_iso):
    if '-' in data_iso:
        partes = data_iso.split('-')
        return f"{partes[2]}/{partes[1]}/{partes[0]}"
    return data_iso

def atualizar_historico_pagamentos():
    tz_brasil = pytz.timezone('America/Sao_Paulo')
    hoje = datetime.now(tz_brasil).date()

    pagamentos = PagamentoRealizado.query.all()
    atualizados = 0

    for p in pagamentos:
        # Atualiza nome do artista (opcional)
        p.artista_nome = buscar_nome_artista(p.artista_id, p.tabela_artista) or "Artista não identificado"

        # Atualiza status se vencimento passou e status ainda não é pago
        if p.vencimento and p.vencimento <= hoje and p.status.lower() != 'pago':
            p.status = 'pago'
            p.data_pagamento = hoje
            atualizados += 1

    db.session.commit()
    return atualizados

@app.route('/usuarios')
def listar_usuarios():
    usuarios = Usuario.query.order_by(Usuario.data_criacao.desc()).all()
    return render_template('usuarios.html', usuarios=usuarios)

@app.route('/usuarios/<int:usuario_id>/editar', methods=['GET', 'POST'])
def editar_usuario(usuario_id):
    usuario = Usuario.query.get_or_404(usuario_id)
    form = UsuarioForm(obj=usuario)
    form.obj_id = usuario.id  # Para validação de email/username único

    if form.validate_on_submit():
        form.populate_obj(usuario)
        
        # Atualizar senha apenas se foi fornecida
        if form.senha.data:
            usuario.set_senha(form.senha.data)
        
        db.session.commit()
        flash('Usuário atualizado com sucesso!', 'success')
        return redirect(url_for('listar_usuarios'))

    return render_template('editar_usuario.html', form=form, usuario=usuario)

@app.route('/usuarios/novo', methods=['GET', 'POST'])
def novo_usuario():
    form = UsuarioForm()
    
    if form.validate_on_submit():
        usuario = Usuario()
        form.populate_obj(usuario)
        
        # Senha é obrigatória para novo usuário
        if not form.senha.data:
            flash('Senha é obrigatória para novo usuário', 'danger')
            return render_template('usuario_form.html', form=form)
        
        usuario.set_senha(form.senha.data)
        db.session.add(usuario)
        db.session.commit()
        
        flash('Usuário criado com sucesso!', 'success')
        return redirect(url_for('listar_usuarios'))

    return render_template('usuario_form.html', form=form)

@app.route('/usuarios/<int:usuario_id>/excluir', methods=['POST'])
def excluir_usuario(usuario_id):
    usuario = Usuario.query.get_or_404(usuario_id)
    db.session.delete(usuario)
    db.session.commit()
    flash('Usuário excluído com sucesso!', 'success')
    return redirect(url_for('listar_usuarios'))



# ROTA LOGOUT
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/inicio')
def inicio():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    try:
        total_usuarios = Usuario.query.count()

        # Corrigir contagem por tipo
        total_artistas = {
            'normais': Artista.query.count(),
            'especiais': ArtistaEspecial.query.filter_by(tipo='especial').count(),
            'assisao': ArtistaEspecial.query.filter_by(tipo='assisao').count()
        }

        # Cálculos unificados
        todos_calculos_processados = list(construir_calculos_disponiveis())

        # Top 5 artistas por royalties
        royalties_por_artista = defaultdict(float)
        for calc in todos_calculos_processados:
            if isinstance(calc, dict) and calc.get('artista') and calc.get('valor_brl') is not None:
                try:
                    royalties_por_artista[calc['artista']] += float(calc['valor_brl'] or 0)
                except (TypeError, ValueError):
                    royalties_por_artista[calc['artista']] += 0.0

        top_artistas_royalties = sorted(
            [{'artista': nome, 'total_brl': valor} for nome, valor in royalties_por_artista.items()],
            key=lambda x: x['total_brl'],
            reverse=True
        )[:5]

        # Cálculos recentes
        calculos_recentes = []
        for calc in sorted(
            [c for c in todos_calculos_processados if isinstance(c, dict) and c.get('data_calculo')],
            key=lambda x: x['data_calculo'],
            reverse=True
        )[:5]:
            calc_serializado = {}
            for k, v in calc.items():
                if v is None:
                    calc_serializado[k] = None
                elif isinstance(v, datetime):
                    calc_serializado[k] = v.strftime('%d/%m/%Y')
                elif isinstance(v, (int, float)):
                    calc_serializado[k] = v
                else:
                    calc_serializado[k] = str(v)
            calculos_recentes.append(calc_serializado)

        # Distribuição por tipo
        distribuicao_calculos = {
            'normais': sum(1 for c in todos_calculos_processados if c.get('tipo') == 'normal'),
            'especiais': sum(1 for c in todos_calculos_processados if c.get('tipo') == 'especial'),
            'assisao': sum(1 for c in todos_calculos_processados if c.get('tipo') == 'assisao')
        }

        # Totais financeiros
        def calcular_totais_gerais():
            def safe_float(val): return float(val) if val else 0.0

            soma_normal = db.session.query(
                func.sum(CalculoSalvo.valor_eur),
                func.sum(CalculoSalvo.valor_brl)
            ).first() or (0, 0)

            soma_especial = db.session.query(
                func.sum(CalculoEspecialSalvo.valor_eur),
                func.sum(CalculoEspecialSalvo.valor_brl)
            ).first() or (0, 0)

            soma_assisao = db.session.query(
                func.sum(CalculoAssisaoSalvo.valor_eur),
                func.sum(CalculoAssisaoSalvo.valor_brl)
            ).first() or (0, 0)

            return {
                'eur': safe_float(soma_normal[0]) + safe_float(soma_especial[0]) + safe_float(soma_assisao[0]),
                'brl': safe_float(soma_normal[1]) + safe_float(soma_especial[1]) + safe_float(soma_assisao[1])
            }

        totais_gerais = calcular_totais_gerais()

        return render_template('inicio.html', **{
            'total_usuarios': total_usuarios,
            'total_artistas': total_artistas,
            'top_artistas_royalties': top_artistas_royalties,
            'calculos_recentes': calculos_recentes,
            'distribuicao_calculos': distribuicao_calculos,
            'valor_total_eur': round(totais_gerais['eur'], 4),
            'valor_total_brl': round(totais_gerais['brl'], 2),
            'total_calculos': len(todos_calculos_processados),
            'data_ultima_atualizacao': datetime.now().strftime('%d/%m/%Y %H:%M')
        })

    except Exception as e:
        print(f"[ERRO CRÍTICO] em /inicio: {str(e)}")
        import traceback
        traceback.print_exc()
        return render_template('erro.html', mensagem=f"Erro ao carregar dashboard: {str(e)}"), 500


# ROTA ARTISTAS
@app.route('/artistas', methods=['GET', 'POST'])
def artistas():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        nome = request.form['nome']
        percentual = float(request.form['percentual'])
        novo = Artista(nome=nome, percentual=percentual)
        db.session.add(novo)
        db.session.commit()
        flash('Artista cadastrado com sucesso.', 'success')
        return redirect(url_for('artistas'))
    artistas = Artista.query.order_by(Artista.nome).all()
    return render_template('cadastro_artista.html', artistas=artistas)

@app.route('/artistas/editar/<int:id>', methods=['GET', 'POST'])
def editar_artista(id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    artista = Artista.query.get_or_404(id)

    if request.method == 'POST':
        artista.nome = request.form['nome']
        artista.percentual = float(request.form['percentual'])
        db.session.commit()
        flash('Artista atualizado com sucesso.', 'success')
        return redirect(url_for('artistas'))

    return render_template('editar_artista.html', artista=artista)

@app.route('/artistas/excluir/<int:id>')
def excluir_artista(id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    artista = Artista.query.get_or_404(id)
    db.session.delete(artista)
    db.session.commit()
    flash('Artista excluído com sucesso.', 'success')
    return redirect(url_for('artistas'))

# ROTA COTAÇÃO
@app.route('/cotacao', methods=['GET', 'POST'])
def cotacao():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        mes = request.form['mes']
        ano = int(request.form['ano'])
        valor = float(request.form['valor'])
        nova = Cotacao(mes=mes, ano=ano, valor=valor)
        db.session.add(nova)
        db.session.commit()
        flash('Cotação cadastrada com sucesso.', 'success')
        return redirect(url_for('cotacao'))
    cotacoes = Cotacao.query.order_by(Cotacao.ano.desc(), Cotacao.mes).all()
    return render_template('cotacao.html', cotacoes=cotacoes)

@app.route('/cotacao/excluir/<int:id>')
def excluir_cotacao(id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    cot = Cotacao.query.get_or_404(id)
    db.session.delete(cot)
    db.session.commit()
    flash('Cotação excluída com sucesso.', 'success')
    return redirect(url_for('cotacao'))

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        file = request.files.get('arquivo')
        if not file:
            flash('Nenhum arquivo selecionado.', 'danger')
            return redirect(request.url)

        filename = secure_filename(file.filename)
        ext = os.path.splitext(filename)[1].lower()

        if ext not in ALLOWED_EXTENSIONS:
            flash('Formato de arquivo inválido.', 'danger')
            return redirect(request.url)

        if len(file.read()) > 150 * 1024 * 1024:
            flash('Arquivo excede o limite de 150MB.', 'danger')
            return redirect(request.url)

        file.seek(0)  # volta ao início
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(path)

        registro = ArquivoImportado(
            nome_arquivo=filename,
            caminho=path  #  ESSENCIAL: salva o caminho real do arquivo
        )
        db.session.add(registro)
        db.session.commit()

        flash('Arquivo enviado com sucesso.', 'success')
        return redirect(url_for('upload'))

    arquivos = ArquivoImportado.query.order_by(ArquivoImportado.data_upload.desc()).all()
    return render_template('upload.html', arquivos=arquivos)

@app.route('/upload/excluir/<int:id>')
def excluir_arquivo(id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    arquivo = ArquivoImportado.query.get_or_404(id)
    caminho = os.path.join(app.config['UPLOAD_FOLDER'], arquivo.nome_arquivo)

    if os.path.exists(caminho):
        os.remove(caminho)

    db.session.delete(arquivo)
    db.session.commit()
    flash('Arquivo excluído com sucesso.', 'success')
    return redirect(url_for('upload'))


@app.route('/calcular', methods=['GET', 'POST'])
def calcular():
    from decimal import Decimal, getcontext, ROUND_HALF_UP, InvalidOperation
    import pandas as pd
    from rapidfuzz import fuzz
    import os

    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    getcontext().prec = 20
    getcontext().rounding = ROUND_HALF_UP

    artistas = Artista.query.order_by(Artista.nome.asc()).all()
    arquivos = ArquivoImportado.query.all()
    cotacoes = Cotacao.query.all()
    resultados = []

    if request.method == 'POST':
        artistas_ids = request.form.getlist('artistas[]')
        arquivos_ids = request.form.getlist('arquivos[]')
        cotacao_id = request.form.get('cotacao')
        mes = request.form.get('mes')
        ano = request.form.get('ano')

        cotacao = Cotacao.query.get(cotacao_id)
        cotacao_valor = Decimal(str(cotacao.valor))

        planilhas_dataframes = {}
        for arquivo_id in arquivos_ids:
            arquivo = ArquivoImportado.query.get(arquivo_id)
            caminho = os.path.join(app.config['UPLOAD_FOLDER'], arquivo.nome_arquivo)
            try:
                if arquivo.nome_arquivo.endswith(('.xls', '.xlsx')):
                    df = pd.read_excel(caminho)
                else:
                    df = pd.read_csv(caminho, sep=None, engine='python')
                df.columns = [c.strip() for c in df.columns]
                planilhas_dataframes[arquivo.nome_arquivo] = df
            except Exception as e:
                flash(f"Erro ao abrir a planilha {arquivo.nome_arquivo}: {e}", "danger")

        for artista_id in artistas_ids:
            artista = Artista.query.get(artista_id)
            percentual = Decimal(str(artista.percentual).replace(',', '.')) / Decimal("100")
            total_lucro_eur = Decimal("0.0000")

            nomes_equivalentes = [remover_acentos(n.strip().lower()) for n in artista.nome.split(',') if n.strip()]

            for nome_arquivo, df in planilhas_dataframes.items():
                for _, row in df.iterrows():
                    nome_raw = str(row.get("Nome do artista", "")).strip().lower()
                    nome_artista_planilha = remover_acentos(nome_raw)

                    lucro_raw = str(row.get("Lucro Líquido", "0")).replace(",", ".").replace("€", "").strip()
                    try:
                        lucro_liquido = Decimal(lucro_raw).quantize(Decimal('0.00000000000001'))
                    except (InvalidOperation, ValueError):
                        continue

                    for nome_ref in nomes_equivalentes:
                        score = fuzz.partial_ratio(nome_artista_planilha, nome_ref)
                        if score >= 88 and nome_ref in nome_artista_planilha:
                            total_lucro_eur += lucro_liquido
                            break

            valor_eur = (total_lucro_eur * percentual).quantize(Decimal('0.0001'))
            valor_brl = (valor_eur * cotacao_valor).quantize(Decimal('0.01'))

            resultados.append({
                "artista": artista.nome,
                "lucro_liquido": total_lucro_eur.quantize(Decimal('0.00000000000001')),
                "valor_eur": valor_eur,
                "valor_brl": valor_brl,
                "cotacao": float(cotacao_valor),
                "mes": mes,
                "ano": ano
            })

    # Filtros de histórico
    filtro_artista = request.args.get('filtro_artista', '').strip()
    filtro_mes = request.args.get('filtro_mes', '')
    filtro_ano = request.args.get('filtro_ano', '')

    pagina = request.args.get('pagina', 1, type=int)
    per_page = 30

    historico_query = CalculoSalvo.query
    if filtro_artista:
        historico_query = historico_query.filter(CalculoSalvo.artista.ilike(f'%{filtro_artista}%'))
    if filtro_mes:
        historico_query = historico_query.filter(CalculoSalvo.mes == filtro_mes)
    if filtro_ano:
        try:
            historico_query = historico_query.filter(CalculoSalvo.ano == int(filtro_ano))
        except:
            pass

    total_registros = historico_query.count()
    historico = (
        historico_query.order_by(CalculoSalvo.data_calculo.desc())
        .offset((pagina - 1) * per_page)
        .limit(per_page)
        .all()
    )

    return render_template('calcular.html',
                           artistas=artistas,
                           arquivos=arquivos,
                           cotacoes=cotacoes,
                           resultados=resultados,
                           historico=historico,
                           filtro_artista=filtro_artista,
                           filtro_mes=filtro_mes,
                           filtro_ano=filtro_ano,
                           total_registros=total_registros,
                           pagina_atual=pagina)


@app.route('/calcular/exportar_filtro')
def exportar_resultados_filtro():
    # Obter parâmetros de filtro da URL
    filtro_artista = request.args.get('filtro_artista', '')
    filtro_mes = request.args.get('filtro_mes', '')
    filtro_ano = request.args.get('filtro_ano', '')
    formato = request.args.get('formato', 'csv')

    # Construir query com base nos filtros
    query = CalculoSalvo.query
    
    if filtro_artista:
        query = query.filter(CalculoSalvo.artista.contains(filtro_artista))
    if filtro_mes:
        query = query.filter(CalculoSalvo.mes == filtro_mes)
    if filtro_ano:
        try:
            query = query.filter(CalculoSalvo.ano == int(filtro_ano))
        except ValueError:
            pass  # Ignorar se não for um número válido

    resultados = query.order_by(CalculoSalvo.data_calculo.desc()).all()
    
    # Preparar dados para exportação
    dados = [{
        'Data': c.data_calculo.strftime('%d/%m/%Y %H:%M'),
        'Artista': c.artista,
        'Valor EUR': round(c.valor_eur, 4),
        'Valor BRL': round(c.valor_brl, 2),
        'Cotação': round(c.cotacao, 4),
        'Mês': c.mes,
        'Ano': c.ano
    } for c in resultados]
    
    df = pd.DataFrame(dados)

    # Gerar arquivo temporário com timestamp
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    if formato == 'xls':
        caminho = f'export_calculo_{timestamp}.xlsx'
        df.to_excel(caminho, index=False)
    else:
        caminho = f'export_calculo_{timestamp}.csv'
        df.to_csv(caminho, index=False, sep=';')

    # Enviar arquivo e remover após o envio
    response = send_file(caminho, as_attachment=True)
    
    @response.call_on_close
    def remove_file():
        try:
            os.remove(caminho)
        except Exception as e:
            app.logger.error(f"Erro ao remover arquivo temporário: {str(e)}")
    
    return response

# ROTA EXCLUIR CÁLCULO
@app.route('/calcular/excluir/<int:id>', methods=['POST'])
def excluir_calculo(id):
    calculo = CalculoSalvo.query.get_or_404(id)
    db.session.delete(calculo)
    db.session.commit()
    flash('Cálculo excluído com sucesso.', 'success')
    return redirect(url_for('calcular'))

from flask import request, redirect, url_for, flash
from decimal import Decimal
import json

@app.route('/salvar_calculo', methods=['POST'])
def salvar_calculo():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    try:
        dados_json = request.form.get('dados_resultados')
        resultados = json.loads(dados_json)

        for item in resultados:
            calculo = CalculoSalvo(
                artista=item['artista'],
                valor_eur=float(Decimal(str(item['valor_eur']))),
                valor_brl=float(Decimal(str(item['valor_brl']))),
                cotacao=float(Decimal(str(item['cotacao']))),
                mes=item['mes'],
                ano=int(item['ano']),
                planilha_usada="(prévia)",
                data_calculo=datetime.now()
            )
            db.session.add(calculo)

        db.session.commit()
        flash("Cálculo salvo com sucesso!", "success")

    except Exception as e:
        flash(f"Erro ao salvar cálculo: {e}", "danger")

    return redirect(url_for('calcular'))


@app.route('/calculos_especiais', methods=['GET', 'POST'])
def calculos_especiais():
    from decimal import Decimal, InvalidOperation, getcontext, ROUND_HALF_UP
    import pandas as pd
    from rapidfuzz.fuzz import token_sort_ratio  # substitui fuzzywuzzy
    import os

    getcontext().prec = 20
    getcontext().rounding = ROUND_HALF_UP

    def converter_lucro(valor):
        try:
            valor_str = str(valor).strip().replace(',', '.').replace('€', '').replace('R$', '').strip()
            return Decimal(valor_str)
        except (InvalidOperation, ValueError):
            return Decimal('0.0000')

    def normalizar_texto(texto):
        if not isinstance(texto, str):
            return ""
        return texto.lower().strip()

    artistas = ArtistaEspecial.query.order_by(ArtistaEspecial.nome).all()
    arquivos = ArquivoImportado.query.order_by(ArquivoImportado.data_upload.desc()).all()
    cotacoes = Cotacao.query.order_by(Cotacao.ano.desc(), Cotacao.mes.desc()).all()
    historico = CalculoEspecialSalvo.query.order_by(CalculoEspecialSalvo.data_calculo.desc()).all()

    if request.method == 'POST':
        artista_id = request.form.get('artista_calculo')
        arquivo_id = request.form.get('arquivo_id')
        cotacao_id = request.form.get('cotacao_id')
        mes = request.form.get('mes')
        ano = request.form.get('ano')

        artista = ArtistaEspecial.query.get_or_404(artista_id)
        arquivo = ArquivoImportado.query.get_or_404(arquivo_id)
        cotacao = Cotacao.query.get_or_404(cotacao_id)

        try:
            # Usa o UPLOAD_FOLDER e nome_arquivo
            planilha_path = os.path.join(app.config['UPLOAD_FOLDER'], arquivo.nome_arquivo)

            if not os.path.exists(planilha_path):
                flash(f"Arquivo {arquivo.nome_arquivo} não encontrado na pasta uploads. Favor importar novamente.", "danger")
                return redirect(url_for('calculos_especiais'))

            # Tenta ler a planilha com sep padrão, depois tenta com ';' se der erro
            try:
                df = pd.read_csv(planilha_path)
            except pd.errors.ParserError:
                df = pd.read_csv(planilha_path, sep=';', engine='python')

            df.columns = [col.strip() for col in df.columns]

            col_titulo = encontrar_coluna(df, "Título do lançamento")
            col_lucro = encontrar_coluna(df, "Lucro Líquido")
            col_artista = encontrar_coluna(df, "Nome do artista")

            if not col_titulo or not col_lucro or not col_artista:
                flash("A planilha está sem as colunas obrigatórias.", "danger")
                return redirect(url_for('calculos_especiais'))

            df['titulo_normalizado'] = df[col_titulo].apply(normalizar_texto)
            df['lucro'] = df[col_lucro].apply(converter_lucro)
            df['Nome do artista'] = df[col_artista].astype(str)

            nomes_validos = [normalizar_texto(artista.nome)] + [
                normalizar_texto(v) for v in artista.obter_variacoes()
            ]

            df = df[df['Nome do artista'].apply(lambda nome: normalizar_texto(nome) in nomes_validos)]

            titulos_dict = {}
            for t in artista.titulos:
                try:
                    percentual_str = str(t.percentual).replace(',', '.').strip()
                    titulos_dict[t.titulo] = Decimal(percentual_str)
                except (InvalidOperation, ValueError):
                    flash(f"Percentual inválido para o título '{t.titulo}': '{t.percentual}'", "warning")
                    continue

            resultados_detalhados = []
            total_eur = Decimal('0')
            total_brl = Decimal('0')

            for titulo, percentual in titulos_dict.items():
                titulo_norm = normalizar_texto(titulo)

                matches = []
                for titulo_plan in df['titulo_normalizado'].unique():
                    similaridade = token_sort_ratio(titulo_norm, titulo_plan)
                    if similaridade >= 90:
                        matches.append((titulo_plan, similaridade))

                valor_titulo_eur = Decimal('0')
                linhas_match = pd.DataFrame()

                for titulo_plan, _ in matches:
                    linhas = df[df['titulo_normalizado'] == titulo_plan]
                    linhas_match = pd.concat([linhas_match, linhas])

                if not linhas_match.empty:
                    lucro_total = linhas_match['lucro'].sum()
                    valor_titulo_eur = lucro_total * (percentual / Decimal('100'))
                    total_eur += valor_titulo_eur

                valor_titulo_brl = valor_titulo_eur * Decimal(str(cotacao.valor))
                total_brl += valor_titulo_brl

                resultados_detalhados.append({
                    'titulo': titulo,
                    'titulos_match': [m[0] for m in matches],
                    'similaridades': [m[1] for m in matches],
                    'valor_eur': valor_titulo_eur.quantize(Decimal('0.0001')),
                    'valor_brl': valor_titulo_brl.quantize(Decimal('0.01')),
                    'percentual': percentual
                })

            total_eur = total_eur.quantize(Decimal('0.0001'))
            total_brl = total_brl.quantize(Decimal('0.01'))

            dados_salvar = {
                'artista': artista.nome,
                'arquivo_id': arquivo.id,
                'cotacao': float(cotacao.valor),
                'mes': mes,
                'ano': ano,
                'valor_eur': float(total_eur),
                'valor_brl': float(total_brl),
                'detalhes': [
                    {
                        'titulo': r['titulo'],
                        'valor_eur': float(r['valor_eur']),
                        'valor_brl': float(r['valor_brl'])
                    } for r in resultados_detalhados
                ]
            }

            return render_template(
                'calculos_especiais.html',
                artistas=artistas,
                arquivos=arquivos,
                cotacoes=cotacoes,
                historico=historico,
                resultados_detalhados=resultados_detalhados,
                dados_salvar=dados_salvar,
                total_eur=total_eur,
                total_brl=total_brl
            )

        except Exception as e:
            flash(f"Erro durante o processamento: {str(e)}", "danger")
            return redirect(url_for('calculos_especiais'))

    return render_template(
        'calculos_especiais.html',
        artistas=artistas,
        arquivos=arquivos,
        cotacoes=cotacoes,
        historico=historico
    )

# EXCLUIR RESULTADO SALVO
@app.route('/excluir_calculo_especial/<int:id>', methods=['POST'])
def excluir_calculo_especial(id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    calculo = CalculoEspecialSalvo.query.get(id)
    if calculo:
        db.session.delete(calculo)
        db.session.commit()
        flash('Resultado excluído com sucesso.', 'success')
    else:
        flash('Resultado não encontrado.', 'danger')
    return redirect(url_for('calculos_especiais'))

# EXPORTAR CÁLCULO ESPECIAL
from flask import send_file, request
import pandas as pd
import io
from models import CalculoEspecialSalvo  # ajuste conforme sua estrutura
from datetime import datetime, timezone, timedelta
import pytz

@app.route('/exportar_calculo_especial')
def exportar_calculo_especial():
    filtro_artista = request.args.get('filtro_artista')
    filtro_mes = request.args.get('filtro_mes')
    filtro_ano = request.args.get('filtro_ano')

    query = CalculoEspecialSalvo.query

    if filtro_artista:
        query = query.filter(CalculoEspecialSalvo.artista.ilike(f"%{filtro_artista}%"))
    if filtro_mes:
        query = query.filter(CalculoEspecialSalvo.mes == filtro_mes)
    if filtro_ano:
        query = query.filter(CalculoEspecialSalvo.ano == int(filtro_ano))

    resultados = query.order_by(CalculoEspecialSalvo.data_calculo.desc()).all()

    if not resultados:
        return "Nenhum cálculo encontrado para exportação", 404

    data = []
    for item in resultados:
        data.append({
            "Data/Hora": item.data_calculo.strftime("%d/%m/%Y %H:%M:%S"),
            "Artista": item.artista,
            "Arquivo": item.arquivo.nome_arquivo if item.arquivo else "Removido",
            "Mês": item.mes,
            "Ano": item.ano,
            "Valor EUR": round(item.valor_eur, 4),
            "Valor BRL": round(item.valor_brl, 2),
            "Cotação": round(item.cotacao, 4)
        })

    df = pd.DataFrame(data)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Cálculos Especiais')

    output.seek(0)
    nome_arquivo = f"calculos_especiais_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

    return send_file(output,
                     download_name=nome_arquivo,
                     as_attachment=True,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@app.route('/excluir_artista_especial/<int:artista_id>', methods=['POST'])
def excluir_artista_especial(artista_id):
    artista = ArtistaEspecial.query.get_or_404(artista_id)
    db.session.delete(artista)
    db.session.commit()
    flash(f'Artista "{artista.nome}" excluído com sucesso.', 'success')
    return redirect(url_for('calculos_especiais'))


# EXCLUIR TÍTULO ESPECIAL
@app.route('/excluir_resultado_especial/<int:resultado_id>', methods=['POST'])
def excluir_resultado_especial(resultado_id):
    resultado = CalculoEspecialSalvo.query.get_or_404(resultado_id)
    db.session.delete(resultado)
    db.session.commit()
    flash('Resultado excluído com sucesso!', 'success')
    return redirect(url_for('calculos_especiais'))

@app.route('/artista_especial/cadastrar', methods=['POST'])
def cadastrar_artista_especial():
    try:
        # Validação básica
        nome = request.form.get('nome', '').strip()
        if not nome:
            flash("O nome do artista é obrigatório", "danger")
            return redirect(url_for('calculos_especiais'))

        # Cria o artista PRIMEIRO para obter o ID
        novo_artista = ArtistaEspecial(
            nome=nome,
            variacoes='||'.join([v.strip() for v in request.form.getlist('variacoes[]') if v.strip()]),
            tipo='especial'
        )
        
        # Processa percentual padrão se existir
        if request.form.get('percentual_padrao'):
            try:
                novo_artista.percentual_padrao = float(
                    request.form['percentual_padrao'].replace(',', '.')
                )
            except ValueError:
                flash("Percentual padrão inválido", "danger")
                return redirect(url_for('calculos_especiais'))

        db.session.add(novo_artista)
        db.session.flush()  # Gera o ID sem commit
        
        # Processa títulos APÓS ter o artista_id
        titulos = request.form.getlist('titulos[]')
        percentuais = request.form.getlist('percentuais[]')
        
        for titulo, percentual in zip(titulos, percentuais):
            titulo = titulo.strip()
            percentual = percentual.strip()
            
            if titulo and percentual:
                try:
                    db.session.add(TituloEspecial(
                        titulo=titulo,
                        percentual=float(percentual.replace(',', '.')),
                        artista_id=novo_artista.id  # Agora temos o ID válido
                    ))
                except ValueError:
                    db.session.rollback()
                    flash(f"Percentual inválido para o título '{titulo}'", "danger")
                    return redirect(url_for('calculos_especiais'))

        db.session.commit()
        flash("Artista cadastrado com sucesso!", "success")
        
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao cadastrar artista: {str(e)}", "danger")
        app.logger.error(f"Erro no cadastro: {str(e)}", exc_info=True)
    
    return redirect(url_for('calculos_especiais'))


# EDITAR TÍTULO ESPECIAL
@app.route('/editar_titulo_especial/<int:id>', methods=['POST'])
def editar_titulo_especial(id):
    titulo = TituloEspecial.query.get_or_404(id)
    novo_titulo = request.form.get('novo_titulo')
    novo_percentual = request.form.get('novo_percentual')

    if novo_titulo:
        titulo.titulo = novo_titulo
    if novo_percentual:
        try:
            titulo.percentual = float(novo_percentual)
        except ValueError:
            flash('Percentual inválido.', 'danger')
            return redirect(url_for('calculos_especiais'))

    db.session.commit()
    flash('Título editado com sucesso!', 'success')
    return redirect(url_for('calculos_especiais'))

# EDITAR ARTISTA ESPECIAL
@app.route('/artista_especial/editar/<int:id>')
def editar_artista_especial(id):
    artista = ArtistaEspecial.query.get_or_404(id)
    titulos = TituloEspecial.query.filter_by(artista_id=id).all()

    return render_template(
        'modais/modal_editar_artista.html',
        artista=artista,
        titulos=titulos
    )



@app.route('/artista_especial/atualizar', methods=['POST'])
def atualizar_artista_especial():
    response_data = {'success': False, 'message': ''}
    
    try:
        if not request.is_json and not request.form:
            response_data['message'] = 'Formato de requisição inválido'
            return jsonify(response_data), 400

        id = request.form.get('id')
        if not id:
            response_data['message'] = 'ID do artista não fornecido'
            return jsonify(response_data), 400
            
        artista = ArtistaEspecial.query.get(id)
        if not artista:
            response_data['message'] = 'Artista não encontrado'
            return jsonify(response_data), 404

        # Validação do nome
        nome = request.form.get('nome', '').strip()
        if not nome:
            response_data['message'] = 'O nome do artista é obrigatório'
            return jsonify(response_data), 400
            
        artista.nome = nome

        # Processa variações
        variacoes = request.form.getlist('variacoes[]')
        artista.variacoes = '||'.join([v.strip() for v in variacoes if v.strip()])

        # Remove títulos antigos
        TituloEspecial.query.filter_by(artista_id=artista.id).delete()

        # Processa novos títulos
        titulos = request.form.getlist('titulos[]')
        percentuais = request.form.getlist('percentuais[]')
        
        if len(titulos) != len(percentuais):
            response_data['message'] = 'Número de títulos e percentuais não corresponde'
            return jsonify(response_data), 400

        for titulo, percentual in zip(titulos, percentuais):
            titulo = titulo.strip()
            percentual = percentual.strip()
            
            if titulo and percentual:
                try:
                    percentual_valor = float(percentual.replace(',', '.'))
                    if not (0 <= percentual_valor <= 100):
                        raise ValueError("Percentual deve estar entre 0 e 100")
                        
                    novo = TituloEspecial(
                        titulo=titulo,
                        percentual=percentual_valor,
                        artista_id=artista.id
                    )
                    db.session.add(novo)
                except ValueError as e:
                    db.session.rollback()
                    response_data['message'] = f"Percentual inválido para o título '{titulo}': {str(e)}"
                    return jsonify(response_data), 400

        db.session.commit()
        response_data['success'] = True
        response_data['message'] = 'Artista atualizado com sucesso!'
        flash(response_data['message'], 'success')
        return jsonify(response_data)

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Erro ao atualizar artista: {str(e)}", exc_info=True)
        response_data['message'] = f'Erro ao atualizar artista: {str(e)}'
        return jsonify(response_data), 500

@app.route('/artista_especial/detalhes/<int:id>')
def detalhes_artista_especial(id):
    artista = ArtistaEspecial.query.get_or_404(id)
    titulos = TituloEspecial.query.filter_by(artista_id=id).all()

    return jsonify({
        'nome': artista.nome,
        'variacoes': [v.strip() for v in (artista.variacoes or '').split('||') if v.strip()],
        'titulos': [
            {'titulo': t.titulo, 'percentual': t.percentual or 0}
            for t in titulos
        ]
    })



@app.route('/salvar_calculo_especial', methods=['POST'])
def salvar_calculo_especial():
    import json
    from datetime import datetime
    from pytz import timezone

    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    dados = request.form.get('dados')
    if not dados:
        flash("Dados do cálculo não recebidos.", "danger")
        return redirect(url_for("calculos_especiais"))

    try:
        dados_dict = json.loads(dados)
        calculo = CalculoEspecialSalvo(
            artista=dados_dict['artista'],
            valor_eur=float(dados_dict['valor_eur']),
            valor_brl=float(dados_dict['valor_brl']),
            cotacao=float(dados_dict['cotacao']),
            mes=dados_dict['mes'],
            ano=int(dados_dict['ano']),
            arquivo_id=int(dados_dict['arquivo_id']),
            data_calculo=datetime.now(timezone('America/Recife'))
        )
        db.session.add(calculo)
        db.session.commit()
        flash("Cálculo especial salvo com sucesso!", "success")
    except Exception as e:
        flash(f"Erro ao salvar cálculo: {e}", "danger")

    return redirect(url_for("calculos_especiais"))


@app.route('/calculo_assisao', methods=['GET', 'POST'], endpoint='calculo_assisao')
def calcular_assisao():
    if request.method == 'POST':
        artista_id = request.form.get('artista_id')
        planilha_id = request.form.get('planilha_id')
        cotacao_input = request.form.get('cotacao', '').replace(",", ".").strip()
        mes = request.form.get('mes')
        ano = request.form.get('ano')

        artista = ArtistaEspecial.query.get(artista_id)
        if not artista:
            flash("Artista não encontrado.", "danger")
            return redirect(url_for('calculo_assisao'))

        planilha = ArquivoImportado.query.get(planilha_id)
        if not planilha:
            flash("Planilha não encontrada.", "danger")
            return redirect(url_for('calculo_assisao'))

        try:
            df = carregar_planilha(planilha.caminho)
        except Exception as e:
            flash(f"Erro ao carregar a planilha: {str(e)}", "danger")
            return redirect(url_for('calculo_assisao'))

        # Validação de colunas esperadas
        if not all(col in df.columns for col in ["Nome do artista", "Título do lançamento", "Lucro Líquido"]):
            flash("Planilha está com colunas inválidas. Verifique os cabeçalhos.", "danger")
            return redirect(url_for('calculo_assisao'))

        try:
            cotacao_valor = Decimal(cotacao_input)
        except:
            flash("Cotação inválida ou não preenchida.", "danger")
            return redirect(url_for('calculo_assisao'))

        # Renomear colunas para padrão interno
        df = df.rename(columns={
            'Nome do artista': 'nome_artista_normalizado',
            'Título do lançamento': 'titulo_normalizado',
            'Lucro Líquido': 'lucro'
        })

        # Obter os títulos e percentuais cadastrados
        titulos = TituloEspecial.query.filter_by(artista_id=artista.id).all()
        titulos_dict = {t.titulo: t.percentual for t in titulos}

        # Chamada correta da função de cálculo com objeto artista
        from app import calcular_valores_assisao
        total_eur, total_brl, resultados_detalhados = calcular_valores_assisao(
            df_original=df,
            artista_obj=artista,
            titulos_dict=titulos_dict,
            cotacao_valor=cotacao_valor
        )

        dados_salvar = {
            "artista": artista.nome,
            "arquivo_id": planilha.id,
            "cotacao": str(cotacao_valor),
            "mes": mes,
            "ano": ano,
            "valor_eur": str(total_eur),
            "valor_brl": str(total_brl),
            "detalhes": resultados_detalhados
        }

        flash("Cálculo realizado com sucesso!", "success")
        return render_template(
            'calculo_assisao.html',
            artistas=ArtistaEspecial.query.filter_by(tipo='assisao').all(),
            planilhas=ArquivoImportado.query.all(),
            cotacoes=Cotacao.query.order_by(Cotacao.ano.desc(), Cotacao.mes.desc()).all(),
            historico=CalculoAssisaoSalvo.query.order_by(CalculoAssisaoSalvo.data_calculo.desc()).all(),
            current_year=datetime.now().year,
            current_month=datetime.now().month,
            total_eur=total_eur,
            total_brl=total_brl,
            resultados_detalhados=resultados_detalhados,
            dados_salvar=dados_salvar
        )

    # Método GET — tela inicial
    return render_template(
        'calculo_assisao.html',
        artistas=ArtistaEspecial.query.filter_by(tipo='assisao').all(),
        planilhas=ArquivoImportado.query.all(),
        cotacoes=Cotacao.query.order_by(Cotacao.ano.desc(), Cotacao.mes.desc()).all(),
        historico=CalculoAssisaoSalvo.query.order_by(CalculoAssisaoSalvo.data_calculo.desc()).all(),
        current_year=datetime.now().year,
        current_month=datetime.now().month
    )

@app.route('/artista_assisao/cadastrar', methods=['POST'])
def cadastrar_artista_assisao():
    nome = request.form['nome']
    variacoes = request.form.get('variacoes', '')
    percentual_padrao = request.form.get('percentual_padrao')

    # Processa variações: divide por linha, tira espaços e junta com ||
    variacoes_list = [v.strip() for v in variacoes.split('\n') if v.strip()]
    variacoes_formatado = '||'.join(variacoes_list)

    novo = ArtistaEspecial(
        nome=nome.strip(),
        variacoes=variacoes_formatado,
        percentual_padrao=float(percentual_padrao) if percentual_padrao else None,
        tipo='assisao'
    )
    db.session.add(novo)
    db.session.flush()  # Garante que novo.id esteja disponível

    # Captura os títulos e percentuais do form
    titulos = request.form.getlist('titulos[]')
    percentuais = request.form.getlist('percentuais[]')

    for titulo, percentual in zip(titulos, percentuais):
        if titulo.strip() and percentual.strip():
            novo_titulo = TituloEspecial(
                titulo=titulo.strip(),
                percentual=float(percentual),
                artista_id=novo.id
            )
            db.session.add(novo_titulo)

    db.session.commit()
    flash("Artista cadastrado em Cálculo Assisão.", "success")
    return redirect(url_for('calculo_assisao'))


@app.route('/artista_assisao/atualizar', methods=['POST'])
def atualizar_artista_assisao():
    id = request.form.get('id')
    artista = ArtistaEspecial.query.get_or_404(id)

    # Atualiza nome
    artista.nome = request.form.get('nome')

    # Corrigido: separa o conteúdo do textarea linha a linha
    variacoes_raw = request.form.get('variacoes', '')
    variacoes_list = [v.strip() for v in variacoes_raw.split('\n') if v.strip()]
    artista.variacoes = '||'.join(variacoes_list)

    # Remove os títulos antigos associados a esse artista
    TituloEspecial.query.filter_by(artista_id=artista.id).delete()

    # Adiciona os novos títulos e percentuais
    titulos = request.form.getlist('titulos[]')
    percentuais = request.form.getlist('percentuais[]')

    for titulo, percentual in zip(titulos, percentuais):
        if titulo.strip() and percentual.strip():
            novo_titulo = TituloEspecial(
                titulo=titulo.strip(),
                percentual=float(percentual),
                artista_id=artista.id
            )
            db.session.add(novo_titulo)

    db.session.commit()
    flash("Artista (Assisão) atualizado com sucesso!", "success")
    return redirect(url_for('calculo_assisao'))

@app.route('/editar_artista_assisao/<int:artista_id>')
def editar_artista_assisao(artista_id):
    artista = ArtistaEspecial.query.get_or_404(artista_id)
    return render_template('modais/modal_editar_artista_assisao.html', artista=artista)

@app.route('/detalhes_artista_assisao/<int:artista_id>')
def detalhes_artista_assisao(artista_id):
    artista = ArtistaEspecial.query.get_or_404(artista_id)
    return render_template('modais/modal_detalhes_artista_assisao.html', artista=artista)

@app.route('/artista_assisao/excluir/<int:artista_id>', methods=['POST'])
def excluir_artista_assisao(artista_id):
    artista = ArtistaEspecial.query.filter_by(id=artista_id, tipo='assisao').first_or_404()
    db.session.delete(artista)
    db.session.commit()
    flash(f"Artista '{artista.nome}' excluído com sucesso!", "success")
    return redirect(url_for('calculo_assisao'))

@app.route('/salvar_calculo_assisao', methods=['POST'])
def salvar_calculo_assisao():
    from datetime import datetime
    import json
    from decimal import Decimal

    dados_json = request.form.get('dados_json')
    if not dados_json:
        flash("Dados não encontrados para salvar o cálculo.", "danger")
        return redirect(url_for('calculo_assisao'))

    try:
        dados = json.loads(dados_json)

        novo = CalculoAssisaoSalvo(
            artista=dados['artista'],
            arquivo_id=dados['arquivo_id'],
            cotacao=Decimal(str(dados['cotacao'])),
            mes=int(dados['mes']),
            ano=int(dados['ano']),
            valor_eur=Decimal(str(dados['valor_eur'])),
            valor_brl=Decimal(str(dados['valor_brl'])),
            detalhes=json.dumps(dados['detalhes']),
            data_calculo=datetime.now()
        )

        db.session.add(novo)
        db.session.commit()
        flash("Cálculo Assisão salvo com sucesso!", "success")
    except Exception as e:
        flash(f"Erro ao salvar: {str(e)}", "danger")

    return redirect(url_for('calculo_assisao'))

@app.route('/excluir_calculo_assisao/<int:id>', methods=['POST'])
def excluir_calculo_assisao(id):
    calculo = CalculoAssisaoSalvo.query.get_or_404(id)
    db.session.delete(calculo)
    db.session.commit()
    flash("Cálculo Assisão excluído com sucesso!", "success")
    return redirect(url_for('calculo_assisao'))

# ======================
#  buscar_nome
# ======================


def serializar_calculo(c, tipo):
    from utils import buscar_nome_artista  # ou ajuste conforme o local da função
    nome = buscar_nome_artista(c.artista_id, c.tabela_artista) or "Artista não identificado"
    return {
        'id': c.id,
        'artista': nome,
        'valor_eur': float(c.valor_eur),
        'valor_brl': float(c.valor_brl or 0),
        'cotacao': float(c.cotacao or 0),
        'mes': c.mes,
        'ano': c.ano,
        'tipo': tipo
    }


# ======================
# ROTAS PRINCIPAIS
# ======================
def padronizar_status_pagamentos():
    pagamentos = PagamentoRealizado.query.all()
    atualizados = 0
    for p in pagamentos:
        if p.status:
            status_limpo = p.status.strip().lower()
        else:
            status_limpo = 'agendado'
        
        if p.status != status_limpo:
            p.status = status_limpo
            atualizados += 1
    if atualizados > 0:
        db.session.commit()
    return atualizados

def remover_duplicados(pagamentos):
    vistos = set()
    resultado = []
    for p in pagamentos:
        chave = (p.artista_nome, p.mes, p.ano, round(p.valor_brl, 2), p.status, p.vencimento)
        if chave not in vistos:
            vistos.add(chave)
            resultado.append(p)
    return resultado

@app.route('/pagamentos')
def pagamentos():
    try:
        from datetime import datetime
        import pytz
        from sqlalchemy import func
        
        tz_brasil = pytz.timezone('America/Sao_Paulo')
        hoje = datetime.now(tz_brasil).date()

        pagamentos = PagamentoRealizado.query.all()
        atualizados_nome = 0
        atualizados_status = 0

        print(f"[DEBUG] Total pagamentos para processar: {len(pagamentos)}")

        for p in pagamentos:
            # Padroniza status (lowercase, trim, vazio vira 'agendado')
            status_limpo = (p.status or '').strip().lower()
            if not status_limpo:
                print(f"[DEBUG] Corrigindo status vazio no pagamento ID {p.id} para 'agendado'")
                p.status = 'agendado'
                atualizados_status += 1
            elif p.status != status_limpo:
                print(f"[DEBUG] Padronizando status do pagamento ID {p.id}: '{p.status}' → '{status_limpo}'")
                p.status = status_limpo
                atualizados_status += 1

            # Atualiza para 'pago' se vencimento for menor ou igual à hoje
            if p.status == 'agendado' and p.vencimento and p.vencimento <= hoje:
                print(f"[DEBUG] Atualizando status para PAGO ID {p.id} (vencimento {p.vencimento})")
                p.status = 'pago'
                p.data_pagamento = datetime.now(tz_brasil)
                atualizados_status += 1

            # Atualiza nome do artista
            nome_correto = buscar_nome_artista(p.artista_id, p.tabela_artista)
            if nome_correto and p.artista_nome != nome_correto:
                print(f"[DEBUG] Atualizando nome ID {p.id}: '{p.artista_nome}' → '{nome_correto}'")
                p.artista_nome = nome_correto
                atualizados_nome += 1

        db.session.commit()
        print(f"[DEBUG] Atualizações realizadas: nomes={atualizados_nome}, status={atualizados_status}")

        # Carrega artistas (normais, especiais, assisão)
        artistas_normais = Artista.query.order_by(Artista.nome).all()
        artistas_especiais = ArtistaEspecial.query.filter_by(tipo='especial').order_by(ArtistaEspecial.nome).all()
        artistas_assisao = ArtistaEspecial.query.filter_by(tipo='assisao').order_by(ArtistaEspecial.nome).all()
        artistas = artistas_normais + artistas_especiais + artistas_assisao

        # Carrega SPs e cotações
        sps = SPImportada.query.order_by(SPImportada.id.desc()).all()
        cotacoes = Cotacao.query.order_by(Cotacao.ano.desc(), Cotacao.mes.desc()).all()

        # Carrega cálculos disponíveis
        calculos_disponiveis = construir_calculos_disponiveis()

        # Filtra pagamentos para exibição no histórico
        pagamentos_registrados = PagamentoRealizado.query.filter(
            PagamentoRealizado.tabela_artista.in_(['normal', 'especial', 'assisao']),
            func.lower(func.trim(PagamentoRealizado.status)).in_(["pago", "agendado"])
        ).order_by(PagamentoRealizado.vencimento.desc()).all()

        # Remove duplicados
        pagamentos_registrados = remover_duplicados(pagamentos_registrados)

        # Calcula total pago em BRL
        total_pago = sum(p.valor_brl for p in pagamentos_registrados if (p.status or '').strip().lower() == 'pago')

        meses_abreviado = [
            '', 'JAN', 'FEV', 'MAR', 'ABR', 'MAI', 'JUN',
            'JUL', 'AGO', 'SET', 'OUT', 'NOV', 'DEZ'
        ]

        return render_template(
            'pagamentos.html',
            artistas=artistas,
            sps=sps,
            cotacoes=cotacoes,
            calculos_disponiveis=calculos_disponiveis,
            pagamentos=pagamentos_registrados,
            total_pago=total_pago,
            meses_abreviado=meses_abreviado
        )
    except Exception as e:
        print(f"[ERRO] ao carregar aba Pagamentos: {e}")
        import traceback
        traceback.print_exc()
        return "Erro interno ao carregar a aba de pagamentos.", 500


# ======================
# OPERAÇÕES COM SP
# ======================

@app.route('/importar_sp', methods=['POST'])
def importar_sp():
    artista_id_bruto = request.form.get('artista_id')
    arquivo = request.files.get('arquivo')
    identificacao = request.form.get('identificacao')

    if not artista_id_bruto or not arquivo:
        flash("Artista e arquivo são obrigatórios.", "error")
        return redirect(url_for('pagamentos'))

    # Extrai tipo e ID real
    if '_' in artista_id_bruto:
        prefixo, id_str = artista_id_bruto.split('_')
        artista_id = int(id_str)

        if prefixo == 'esp':
            artista = ArtistaEspecial.query.filter_by(id=artista_id, tipo='especial').first()
        elif prefixo == 'ass':
            artista = ArtistaEspecial.query.filter_by(id=artista_id, tipo='assisao').first()
        else:
            artista = Artista.query.get(artista_id)

        tabela = prefixo
    else:
        artista_id = int(artista_id_bruto)
        artista = Artista.query.get(artista_id)
        tabela = 'norm'

    if not artista:
        flash("Artista não encontrado.", "error")
        return redirect(url_for('pagamentos'))

    filename = secure_filename(arquivo.filename)
    if not filename.lower().endswith('.xlsx'):
        flash("Somente arquivos .xlsx são permitidos.", "error")
        return redirect(url_for('pagamentos'))

    # Criar pasta única por artista + tipo
    pasta_destino = os.path.join('static', 'uploads', 'sps', f'SP_{artista_id}_{tabela}')
    os.makedirs(pasta_destino, exist_ok=True)
    caminho_completo = os.path.join(pasta_destino, filename)
    arquivo.save(caminho_completo)

    nova_sp = SPImportada(
        artista_id=artista_id,
        tabela_artista=tabela,
        nome_arquivo=filename,
        identificacao=identificacao,
        caminho=caminho_completo.replace('\\', '/')
    )
    db.session.add(nova_sp)
    db.session.commit()

    flash("SP importada com sucesso!", "success")
    return redirect(url_for('pagamentos'))

@app.route('/excluir_sp/<int:sp_id>', methods=['POST'])
def excluir_sp(sp_id):
    sp = SPImportada.query.get_or_404(sp_id)

    if sp.caminho:
        try:
            if os.path.exists(sp.caminho):
                os.remove(sp.caminho)
            else:
                flash("Aviso: o arquivo da SP já não existe no sistema.", "warning")
        except PermissionError:
            flash("Erro: não foi possível remover o arquivo. Verifique se ele está aberto em outro programa.", "danger")
            return redirect(url_for('pagamentos'))
        except Exception as e:
            flash(f"Erro ao excluir o arquivo: {e}", "danger")
            return redirect(url_for('pagamentos'))

    db.session.delete(sp)
    db.session.commit()
    flash('SP excluída com sucesso.', 'success')
    return redirect(url_for('pagamentos'))

# ======================
# GERENCIAMENTO DE PAGAMENTOS
# ======================

@app.route("/gerar_sp_pagamento", methods=["POST"])
def gerar_sp_pagamento():
    try:
        from flask import send_file, request, after_this_request
        from models import SPImportada, PagamentoRealizado, CalculoSalvo, CalculoEspecialSalvo, CalculoAssisaoSalvo
        from datetime import datetime
        import traceback, os
        import win32com.client, pythoncom
        from app import db
        atualizados = atualizar_historico_pagamentos()

        def converter_mes_para_numero(mes_str):
            meses_map = {
                'janeiro': 1, 'fevereiro': 2, 'marco': 3, 'março': 3, 'abril': 4,
                'maio': 5, 'junho': 6, 'julho': 7, 'agosto': 8, 'setembro': 9,
                'outubro': 10, 'novembro': 11, 'dezembro': 12
            }
            if isinstance(mes_str, int):
                return mes_str
            if not mes_str:
                return None
            mes_str = mes_str.strip().lower()
            mes_str = mes_str.replace('ç', 'c')
            return meses_map.get(mes_str)

        sp_id = request.form.get("sp_id")
        calculos_ids_raw = request.form.get("calculos_ids", "")
        valor_eur = request.form.get("valor_eur", "")
        cotacao = request.form.get("cotacao", "")
        vencimento = request.form.get("vencimento", "")
        retencao = request.form.get("retencao", "0")
        status_pagamento = request.form.get("status_pagamento", "aguardando")
        formato = request.form.get("formato", "excel")  # Padrão: excel, alternativa: pdf

        print(f"DEBUG - sp_id: {sp_id}")
        print(f"DEBUG - calculos_ids_raw: '{calculos_ids_raw}'")
        print(f"DEBUG - valor_eur: '{valor_eur}'")
        print(f"DEBUG - cotacao: '{cotacao}'")
        print(f"DEBUG - vencimento: '{vencimento}'")
        print(f"DEBUG - formato: '{formato}'")

        campos_faltando = []
        if not sp_id: campos_faltando.append("sp_id")
        if not calculos_ids_raw: campos_faltando.append("calculos_ids")
        if not valor_eur: campos_faltando.append("valor_eur")
        if not cotacao: campos_faltando.append("cotacao")
        if not vencimento: campos_faltando.append("vencimento")

        if campos_faltando:
            print(f"ERRO - Campos obrigatórios faltando: {', '.join(campos_faltando)}")
            return f"Dados obrigatórios faltando: {', '.join(campos_faltando)}", 400

        try:
            sp_obj = db.session.get(SPImportada, int(sp_id))
            if not sp_obj:
                return "SP não encontrada", 404
        except Exception as e:
            print(f"ERRO - Busca SP: {str(e)}")
            return f"SP inválida: {str(e)}", 400

        calculos_ids = [cid.strip() for cid in calculos_ids_raw.split(",") if cid.strip()]
        if not calculos_ids:
            return "Nenhum cálculo selecionado", 400

        mes, ano, artista = None, None, None
        calc_base = None

        for cid in calculos_ids:
            if "_" not in cid:
                continue

            try:
                tipo, id_str = cid.split("_", 1)
                id_int = int(id_str)

                if tipo == "norm":
                    calc = CalculoSalvo.query.get(id_int)
                elif tipo == "esp":
                    calc = CalculoEspecialSalvo.query.get(id_int)
                elif tipo == "ass":
                    calc = CalculoAssisaoSalvo.query.get(id_int)
                else:
                    continue

                if calc:
                    calc_base = calc
                    mes = calc.mes
                    ano = calc.ano
                    artista = calc.artista
                    break
            except Exception:
                continue

        mes_input = request.form.get("mes") or (str(mes) if mes is not None else None)
        ano = request.form.get("ano") or (str(ano) if ano is not None else None)
        artista = request.form.get("artista") or artista

        mes_num = converter_mes_para_numero(mes_input)
        if mes_num is None:
            return "Mês inválido ou não informado", 400

        if not all([mes_num, ano, artista]):
            return "Dados de mês, ano ou artista faltando", 400

        try:
            valor_eur_clean = valor_eur.replace("€", "").replace(",", ".").strip()
            valor_eur_float = float(valor_eur_clean) if valor_eur_clean else 0.0

            cotacao_clean = cotacao.replace(",", ".").strip()
            cotacao_float = float(cotacao_clean) if cotacao_clean else 0.0

            valor_brl_total = round(valor_eur_float * cotacao_float, 2)
        except ValueError as e:
            print(f"ERRO - Conversão numérica: {str(e)}")
            return f"Erro na conversão de valores: {str(e)}", 400

        resultado = preencher_sp_dinamicamente(
            sp_obj=sp_obj,
            valor_eur=valor_eur,
            cotacao=cotacao,
            vencimento=vencimento,
            retencao=retencao,
            valores_adicionais={
                "calculos_ids": calculos_ids,
                "status": status_pagamento
            },
            mes=mes_num,
            ano=ano,
            artista=artista
        )

        caminho_excel = resultado.get("caminho_excel")
        if not caminho_excel or not os.path.isfile(caminho_excel):
            return "Arquivo da SP não foi gerado corretamente", 500

        for calc_id in calculos_ids:
            if "_" not in calc_id:
                continue

            origem, id_numerico = calc_id.split("_", 1)
            tabela_artista = {
                "norm": "normal",
                "esp": "especial",
                "ass": "assisao"
            }.get(origem, "normal")

            pagamento = PagamentoRealizado(
                artista_id=sp_obj.artista_id,
                tabela_artista=tabela_artista,
                sp_id=sp_obj.id,
                mes=mes_num,
                ano=int(ano),
                valor_eur=valor_eur_float,
                valor_brl=valor_brl_total,
                cotacao=cotacao_float,
                vencimento=datetime.strptime(vencimento, "%Y-%m-%d").date(),
                data_pagamento=datetime.today().date(),
                status=status_pagamento.lower(),
                herdeiro=None,
                calculo_id=calc_id
            )
            db.session.add(pagamento)

        db.session.commit()

        if formato == "pdf":
            caminho_pdf = caminho_excel.replace(".xlsx", ".pdf")
            pythoncom.CoInitialize()
            try:
                excel = win32com.client.Dispatch("Excel.Application")
                excel.Visible = False
                excel.DisplayAlerts = False

                wb = excel.Workbooks.Open(os.path.abspath(caminho_excel))
                wb.ExportAsFixedFormat(0, os.path.abspath(caminho_pdf))
                wb.Close(False)

            except Exception as e:
                traceback.print_exc()
                return f"Erro ao converter para PDF: {str(e)}", 500
            finally:
                try:
                    excel.Quit()
                except Exception:
                    pass
                pythoncom.CoUninitialize()

            nome_download_pdf = sp_obj.nome_arquivo
            if nome_download_pdf.lower().endswith('.xlsx'):
                nome_download_pdf = nome_download_pdf[:-5] + '.pdf'
            elif not nome_download_pdf.lower().endswith('.pdf'):
                nome_download_pdf += '.pdf'

            response = send_file(
                caminho_pdf,
                as_attachment=True,
                download_name=nome_download_pdf,
                mimetype="application/pdf"
            )

            @after_this_request
            def limpar_arquivos(response):
                try:
                    if os.path.exists(caminho_excel):
                        os.remove(caminho_excel)
                    if os.path.exists(caminho_pdf):
                        os.remove(caminho_pdf)
                except Exception as e:
                    print(f"[AVISO] Falha ao limpar arquivos: {str(e)}")
                return response

            return response

        else:  # Excel
            nome_download = sp_obj.nome_arquivo
            if not nome_download.lower().endswith('.xlsx'):
                nome_download += '.xlsx'

            response = send_file(
                caminho_excel,
                as_attachment=True,
                download_name=nome_download,
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            @after_this_request
            def limpar_arquivo(response):
                try:
                    if os.path.exists(caminho_excel):
                        os.remove(caminho_excel)
                except Exception as e:
                    print(f"[AVISO] Falha ao limpar arquivo Excel: {str(e)}")
                return response

            return response

    except Exception as e:
        print(f"[ERRO CRÍTICO] {str(e)}")
        print(traceback.format_exc())
        return f"Erro interno ao processar a requisição: {str(e)}", 500

@app.route('/api/calculos_disponiveis')
def api_calculos_disponiveis():
    try:
        def parse_calculo(c, tipo):
            nome_mes = {
                1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun',
                7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'
            }
            artista = None
            if tipo == 'norm':
                artista = Artista.query.get(c.artista_id)
            else:
                artista = ArtistaEspecial.query.filter_by(id=c.artista_id, tipo=tipo).first()
            
            return {
                "id": c.id,
                "artista_id": c.artista_id,
                "artista": artista.nome if artista else f"ID {c.artista_id}",
                "tipo": tipo,
                "mes": c.mes,
                "ano": c.ano,
                "mes_nome": nome_mes.get(c.mes, str(c.mes)),
                "valor_eur": float(c.valor_eur),
                "cotacao": float(c.cotacao) if hasattr(c, 'cotacao') and c.cotacao else None,
                "status": c.status.capitalize() if hasattr(c, 'status') and c.status else "Aguardando"
            }

        resultados = []

        for model, tipo in [
            (CalculoSalvo, 'norm'),
            (CalculoEspecialSalvo, 'esp'),
            (CalculoAssisaoSalvo, 'ass')
        ]:
            registros = model.query.all()
            for c in registros:
                resultados.append(parse_calculo(c, tipo))

        return jsonify(resultados)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"erro": str(e)}), 500


# ======================
# ATUALIZAÇÃO DE STATUS
# ======================

@app.route('/api/historico/iniciar', methods=['POST'])
def iniciar_historico_pagamento():
    dados = request.json
    try:
        artista_id = dados['artista_id']
        tabela_artista = dados['tabela_artista']
        artista_nome = dados['artista_nome']  # nome enviado do front

        # Cria registro com dados mínimos e status temporário
        novo = PagamentoRealizado(
            artista_id=artista_id,
            tabela_artista=tabela_artista,
            artista_nome=artista_nome,
            status='Iniciado',
            data_pagamento=None
        )
        db.session.add(novo)
        db.session.commit()

        return jsonify({'success': True, 'id': novo.id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/historico/atualizar/<int:pagamento_id>', methods=['POST'])
def atualizar_historico_pagamento(pagamento_id):
    dados = request.json
    try:
        pagamento = PagamentoRealizado.query.get(pagamento_id)
        if not pagamento:
            return jsonify({'success': False, 'error': 'Pagamento não encontrado'})

        # Atualiza os campos
        pagamento.mes = dados.get('mes', pagamento.mes)
        pagamento.ano = dados.get('ano', pagamento.ano)
        pagamento.valor_brl = dados.get('valor_brl', pagamento.valor_brl)
        pagamento.status = dados.get('status', pagamento.status)
        pagamento.vencimento = datetime.strptime(dados['vencimento'], '%Y-%m-%d').date() if dados.get('vencimento') else pagamento.vencimento
        pagamento.herdeiro = dados.get('herdeiro', pagamento.herdeiro)

        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/salvar_calculo_pagamento', methods=['POST'])
def salvar_calculo_pagamento():
    dados = request.json
    try:
        # Obtem o nome real do artista pelo id e tabela antes de salvar
        nome_artista = buscar_nome_artista(dados['artista_id'], dados['tabela_artista']) or "Artista não identificado"

        novo = PagamentoRealizado(
            artista_id=dados['artista_id'],
            tabela_artista=dados['tabela_artista'],
            sp_id=dados.get('sp_id'),
            mes=dados['mes'],
            ano=dados['ano'],
            valor_eur=dados['valor_eur'],
            valor_brl=dados['valor_brl'],
            cotacao=dados['cotacao'],
            vencimento=datetime.strptime(dados['vencimento'], '%Y-%m-%d').date(),
            data_pagamento=datetime.now().date(),
            status='Agendado',
            herdeiro=dados.get('herdeiro'),
            calculo_id=dados.get('calculo_id'),
            artista_nome=nome_artista  # Atenção aqui!
        )
        db.session.add(novo)
        db.session.commit()

        # Atualiza nomes e status baseados em datas logo após salvar
        atualizar_e_buscar_historico()

        return jsonify({'success': True, 'id': novo.id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


def atualizar_nomes_e_status_pagamentos():
    from datetime import datetime
    import pytz

    tz_brasil = pytz.timezone('America/Sao_Paulo')
    hoje = datetime.now(tz_brasil).date()

    pagamentos = PagamentoRealizado.query.all()
    mudou = False

    for p in pagamentos:
        nome_correto = buscar_nome_artista(p.artista_id, p.tabela_artista) or "Artista não identificado"
        if p.artista_nome != nome_correto:
            p.artista_nome = nome_correto
            mudou = True
        if p.vencimento and p.vencimento <= hoje and p.status.lower() != 'pago':
            p.status = 'pago'
            p.data_pagamento = hoje
            mudou = True

    if mudou:
        db.session.commit()

@app.route('/api/historico_pagamentos', methods=['GET'])
@csrf.exempt
def api_historico_pagamentos():
    try:
        from sqlalchemy import func
        from datetime import datetime
        import pytz

        tz_brasil = pytz.timezone('America/Sao_Paulo')
        hoje = datetime.now(tz_brasil).date()

        # 1. Atualizar status e nomes no banco para manter padrão
        pagamentos = PagamentoRealizado.query.all()

        atualizados_nome = 0
        atualizados_status = 0

        for p in pagamentos:
            # Padronizar status
            status_limpo = (p.status or '').strip().lower()
            if p.status != status_limpo:
                p.status = status_limpo
                atualizados_status += 1

            # Atualizar status para pago se vencimento já passou
            if status_limpo == 'agendado' and p.vencimento and p.vencimento <= hoje:
                p.status = 'pago'
                p.data_pagamento = datetime.now(tz_brasil)
                atualizados_status += 1

            # Atualizar nome do artista
            nome_correto = buscar_nome_artista(p.artista_id, p.tabela_artista)
            if nome_correto and p.artista_nome != nome_correto:
                p.artista_nome = nome_correto
                atualizados_nome += 1

        db.session.commit()

        print(f"[DEBUG] Atualizações: nomes={atualizados_nome}, status={atualizados_status}")

        # 2. Debug dos status antes do filtro
        print("[DEBUG] Status e IDs antes do filtro:")
        for p in pagamentos:
            print(f"ID: {p.id}, status raw: '{p.status}'")

        # 3. Filtrar só os pagos e agendados padronizados
        query = PagamentoRealizado.query.filter(
            func.lower(func.trim(PagamentoRealizado.status)).in_(["pago", "agendado"])
        )

        pagamentos_filtrados = query.order_by(PagamentoRealizado.vencimento.desc()).all()

        # 4. Debug dos status após filtro
        print("[DEBUG] Status e IDs após filtro:")
        for p in pagamentos_filtrados:
            print(f"ID: {p.id}, status limpo: '{(p.status or '').strip().lower()}'")

        MESES = ['', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
                 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']

        lista = []
        for p in pagamentos_filtrados:
            mes_nome = MESES[p.mes] if p.mes and 1 <= p.mes <= 12 else ''
            lista.append({
                'id': p.id,
                'artista_nome': p.artista_nome or "Artista não identificado",
                'mes': p.mes,
                'mes_nome': mes_nome,
                'ano': p.ano,
                'status': p.status,
                'valor_brl': float(p.valor_brl or 0),
                'data_vencimento': p.vencimento.strftime('%d/%m/%Y') if p.vencimento else '',
                'herdeiro': p.herdeiro
            })

        return jsonify({"success": True, "pagamentos": lista})

    except Exception as e:
        current_app.logger.error(f"[ERRO api_historico_pagamentos] {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/atualizar_pagamentos', methods=['POST'])
def atualizar_pagamentos():
    try:
        from datetime import datetime
        import pytz
        tz_brasil = pytz.timezone('America/Sao_Paulo')
        hoje = datetime.now(tz_brasil).date()

        pagamentos = PagamentoRealizado.query.all()
        nomes_atualizados = 0
        status_atualizados = 0

        for p in pagamentos:
            # Atualiza nome do artista
            nome_correto = buscar_nome_artista(p.artista_id, p.tabela_artista)
            if nome_correto and p.artista_nome != nome_correto:
                p.artista_nome = nome_correto
                nomes_atualizados += 1

            # Atualiza status para pago se a data venceu
            if p.status and p.status.strip().lower() != 'pago' and p.vencimento and p.vencimento <= hoje:
                p.status = 'pago'
                p.data_pagamento = hoje
                status_atualizados += 1

        db.session.commit()

        return jsonify({
            'success': True,
            'nomes_atualizados': nomes_atualizados,
            'status_atualizados': status_atualizados,
            'mensagem': 'Atualização dos pagamentos realizada com sucesso.'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# ======================
# API E AUXILIARES
# ======================

@app.route("/api/calculos_por_artista")
def api_calculos_por_artista():
    artista_id = request.args.get("artista_id")

    if not artista_id:
        return jsonify([])

    lista = []
    modelos = [
        (CalculoSalvo, "normais"),
        (CalculoEspecialSalvo, "especiais"),
        (CalculoAssisaoSalvo, "assisao")
    ]

    for modelo, tipo in modelos:
        calculos = modelo.query.filter_by(artista_id=artista_id).order_by(modelo.ano.desc(), modelo.mes.desc()).all()
        for calc in calculos:
            lista.append({
                "id": calc.id,
                "artista": calc.artista.nome if hasattr(calc, 'artista') else "-",
                "mes": calc.mes,
                "ano": calc.ano,
                "valor_eur": float(calc.valor_eur),
                "mes_nome": mes_nome(calc.mes),
                "tipo": tipo
            })

    return jsonify(lista)

@app.route('/calcular_resumo_pagamento', methods=['POST'])
def calcular_resumo_pagamento():
    try:
        dados = request.get_json(force=True)
        ids = dados.get('ids', [])
        cotacao = Decimal(str(dados.get('cotacao', 0))).quantize(Decimal('0.0001'))
        retencao = Decimal(str(dados.get('retencao', 0)))
        herdeiro = Decimal(str(dados.get('herdeiro', 0)))

        if not ids:
            return jsonify({"erro": "Nenhum ID de cálculo fornecido"}), 400
        if cotacao <= 0:
            return jsonify({"erro": "Cotação inválida"}), 400

        # Somar valores dos cálculos
        valor_eur = Decimal("0.0000")
        calc_info = None

        for calc_id in ids:
            calc = db.session.get(CalculoSalvo, int(calc_id))
            if calc:
                valor_eur += Decimal(str(calc.valor_eur))
                if not calc_info:
                    artista_nome = calc.artista.nome if hasattr(calc.artista, 'nome') else calc.artista
                    calc_info = {"mes": calc.mes, "ano": calc.ano, "artista": artista_nome}

        valor_brl = (valor_eur * cotacao).quantize(Decimal('0.01'))
        valor_retencao = (valor_brl * retencao / 100).quantize(Decimal('0.01'))
        valor_final = (valor_brl - valor_retencao).quantize(Decimal('0.01'))

        return jsonify({
            "valor_eur": str(valor_eur),
            "valor_brl": str(valor_brl),
            "retencao": str(valor_retencao),
            "valor_final": str(valor_final),
            "calculo": calc_info
        })

    except Exception as e:
        return jsonify({"erro": f"Erro interno: {str(e)}"}), 500

@app.route('/api/verificar-vencimentos', methods=['POST'])
def verificar_vencimentos():
    try:
        from sqlalchemy import func
        hoje = datetime.today().date()

        registros_agendados = db.session.query(PagamentoRealizado).filter(
            func.lower(PagamentoRealizado.status) == 'agendado',
            PagamentoRealizado.data_pagamento != None,
            PagamentoRealizado.data_pagamento <= hoje
        ).all()

        atualizados = 0
        for reg in registros_agendados:
            reg.status = 'pago'
            atualizados += 1

        db.session.commit()
        return jsonify({'success': True, 'atualizados': atualizados})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

# ======================
# EXPORTAÇÃO DE DADOS
# ======================

@app.route('/exportar_royalties')
def exportar_royalties():
    try:
        # Buscar todos os artistas (normais, especiais e assisão)
        artistas_normais = Artista.query.order_by(Artista.nome).all()
        artistas_especiais = ArtistaEspecial.query.filter_by(tipo='especial').order_by(ArtistaEspecial.nome).all()
        artistas_assisao = ArtistaEspecial.query.filter_by(tipo='assisao').order_by(ArtistaEspecial.nome).all()

        # Buscar todas as planilhas importadas
        planilhas = ArquivoImportado.query.order_by(ArquivoImportado.id.desc()).all()

        return render_template(
            'Exportar_planilhas.html',
            artistas_normais=artistas_normais,
            artistas_especiais=artistas_especiais,
            artistas_assisao=artistas_assisao,
            planilhas=planilhas
        )
    except Exception as e:
        return f"Erro ao carregar a aba de exportação: {e}", 500

# ======================
# FUNÇÕES EXPORTAR 
# ======================

import traceback

def normalizar_nome(nome):
    if not nome:
        return ''
    nome = unicodedata.normalize('NFKD', str(nome))
    nome = ''.join([c for c in nome if not unicodedata.combining(c)])
    return nome.lower().strip()

@app.route('/api/artistas')
def api_artistas():
    try:
        q = request.args.get('q', '').lower()

        # === Carregar infos normalizadas ===
        infos = ArtistaInfo.query.all()
        info_dict = {
            normalizar_nome(info.nome_artista): {
                'total_catalogo': info.total_catalogo or 0,
                'total_musicas': info.total_musicas or 0
            }
            for info in infos if info.nome_artista
        }

        data = []

        # === Artistas normais ===
        artistas_normais = Artista.query.all()
        for artista in artistas_normais:
            if not artista.nome:
                continue
            nome_normalizado = normalizar_nome(artista.nome)
            if q and q not in nome_normalizado:
                continue
            info = info_dict.get(nome_normalizado, {})
            data.append({
                'id': f"norm_{artista.id}",
                'nome': artista.nome,
                'albums': info.get('total_catalogo', 0),
                'songs': info.get('total_musicas', 0),
            })

        # === Artistas especiais ===
        especiais = ArtistaEspecial.query.filter_by(tipo='especial').all()
        for artista in especiais:
            if not artista.nome:
                continue
            nome_normalizado = normalizar_nome(artista.nome)
            if q and q not in nome_normalizado:
                continue
            info = info_dict.get(nome_normalizado, {})
            data.append({
                'id': f"esp_{artista.id}",
                'nome': artista.nome,
                'albums': info.get('total_catalogo', 0),
                'songs': info.get('total_musicas', 0),
            })

        # === Artistas Assisão ===
        assisao = ArtistaEspecial.query.filter_by(tipo='assisao').all()
        for artista in assisao:
            if not artista.nome:
                continue
            nome_normalizado = normalizar_nome(artista.nome)
            if q and q not in nome_normalizado:
                continue
            info = info_dict.get(nome_normalizado, {})
            data.append({
                'id': f"ass_{artista.id}",
                'nome': artista.nome,
                'albums': info.get('total_catalogo', 0),
                'songs': info.get('total_musicas', 0),
            })

        # === Ordenar por nome ===
        data.sort(key=lambda x: x['nome'].lower())

        return jsonify(data)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Erro ao buscar artistas: {str(e)}"}), 500

@app.route('/api/relatorios')
def api_relatorios():
    try:
        artista_id = request.args.get('artista_id')

        arquivos_importados = ArquivoImportado.query

        if artista_id:
            # Remover prefixo do ID
            if '_' in artista_id:
                prefixo, real_id = artista_id.split('_', 1)
                real_id = int(real_id)
                if prefixo == 'norm':
                    arquivos_importados = arquivos_importados.filter_by(artista_id=real_id)
                elif prefixo == 'esp':
                    arquivos_importados = arquivos_importados.filter_by(artista_especial_id=real_id)
                elif prefixo == 'ass':
                    arquivos_importados = arquivos_importados.filter_by(artista_assisao_id=real_id)

        arquivos_importados = arquivos_importados.order_by(ArquivoImportado.data_upload.desc()).all()

        relatorios = [{
            'id': f"arquivo_{arquivo.id}",
            'name': arquivo.nome_arquivo,
            'description': f"Planilha importada em {arquivo.data_upload.strftime('%d/%m/%Y')}",
            'icon': 'fas fa-file-excel',
            'color': 'text-green-600',
            'requiresDate': False
        } for arquivo in arquivos_importados]

        return jsonify({'success': True, 'data': relatorios})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/exportar', methods=['POST'])
def api_exportar():
    dados = request.json
    # Implementação da exportação aqui...
    return jsonify({'error': 'Formato não suportado'}), 400

@app.route('/atualizar_base_artistas')
def route_atualizar_base_artistas():
    atualizar_base_artistas(db)
    return "Base de artistas atualizada com sucesso."

# ======================
# OUTRAS ROTAS (PDF, ETC)
# ======================

@app.route('/anexar_pdf_sp', methods=['POST'])
def anexar_pdf_sp():
    try:
        sp_id = request.form.get('sp_id')
        anexos = request.files.getlist('anexos')

        if not sp_id:
            return "sp_id obrigatório", 400

        sp = SPImportada.query.get(sp_id)
        if not sp:
            return "SP não encontrada", 400

        nome_base = os.path.splitext(os.path.basename(sp.caminho))[0]
        temp_dir = os.path.join("temp", f"{nome_base}_{sp_id}")
        os.makedirs(temp_dir, exist_ok=True)

        for anexo in anexos:
            anexo_path = os.path.join(temp_dir, secure_filename(anexo.filename))
            anexo.save(anexo_path)

        return "Anexos salvos com sucesso", 200

    except Exception as e:
        return f"Erro ao anexar PDF: {str(e)}", 500

@app.route("/gerar_sp_pagamento_pdf", methods=["POST"])
def gerar_sp_pagamento_pdf():
    try:
        from decimal import Decimal
        from flask import send_file, after_this_request, request
        import shutil, traceback, os, tempfile
        import win32com.client, pythoncom
        from PyPDF2 import PdfMerger
        from models import SPImportada, PagamentoRealizado
        from datetime import datetime
        from app import db

        atualizados = atualizar_historico_pagamentos()

        # Parâmetros do formulário
        sp_id = request.form.get("sp_id")
        calculos_ids_raw = request.form.get("calculos_ids")
        valor_eur = request.form.get("valor_eur")
        cotacao = request.form.get("cotacao")
        vencimento = request.form.get("vencimento")
        retencao = request.form.get("retencao", "0")
        status = request.form.get("status_pagamento", "aguardando")
        mes = request.form.get("mes")
        ano = request.form.get("ano")
        artista = request.form.get("artista")

        # Validação de campos obrigatórios
        if not all([sp_id, calculos_ids_raw, valor_eur, cotacao, vencimento, mes, ano, artista]):
            return "Dados obrigatórios faltando.", 400

        # Buscar SP no banco de dados
        sp_obj = db.session.get(SPImportada, int(sp_id))
        if not sp_obj:
            return "SP não encontrada.", 404

        # Processar lista de IDs de cálculos
        calculos_ids = [c.strip() for c in calculos_ids_raw.split(",") if c.strip()]
        if not calculos_ids:
            return "Nenhum cálculo selecionado.", 400

        # Converter valores numéricos
        try:
            valor_eur_float = float(valor_eur.replace("€", "").replace(",", ".").strip())
            cotacao_float = float(cotacao.replace(",", ".").strip())
            valor_brl_total = round(valor_eur_float * cotacao_float, 2)
        except ValueError as e:
            return f"Erro na conversão de valores: {str(e)}", 400

        # Preencher modelo da SP
        resultado = preencher_sp_dinamicamente(
            sp_obj=sp_obj,
            valor_eur=valor_eur,
            cotacao=cotacao,
            vencimento=vencimento,
            retencao=retencao,
            valores_adicionais={
                "calculos_ids": calculos_ids,
                "status": status
            },
            mes=mes,
            ano=ano,
            artista=artista
        )

        caminho_excel = resultado.get("caminho_excel")
        if not caminho_excel or not os.path.isfile(caminho_excel):
            return "Arquivo da SP não foi gerado corretamente.", 500

        # Converter Excel para PDF
        caminho_pdf = caminho_excel.replace(".xlsx", ".pdf")
        pythoncom.CoInitialize()
        try:
            excel = win32com.client.DispatchEx("Excel.Application")
            excel.Visible = False
            excel.DisplayAlerts = False

            wb = excel.Workbooks.Open(os.path.abspath(caminho_excel))
            wb.ExportAsFixedFormat(0, os.path.abspath(caminho_pdf))
            wb.Close(False)
            excel.Quit()
        except Exception as e:
            traceback.print_exc()
            return f"Erro ao converter para PDF: {str(e)}", 500
        finally:
            pythoncom.CoUninitialize()

        if not os.path.isfile(caminho_pdf):
            return "PDF não foi gerado corretamente.", 500

        # Processar anexos
        anexos = request.files.getlist("anexos[]")
        anexos_paths = []
        for i, anexo in enumerate(anexos):
            if anexo and anexo.filename.lower().endswith(".pdf"):
                temp_anexo_path = os.path.join(tempfile.gettempdir(), f"anexo_{sp_id}_{i}.pdf")
                anexo.save(temp_anexo_path)
                anexos_paths.append(temp_anexo_path)

        # Mesclar SP + Resumo + Anexos em ordem
        pdf_final_path = os.path.join(tempfile.gettempdir(), f"SP_FINAL_{sp_id}.pdf")
        merger = PdfMerger()
        merger.append(caminho_pdf)  # Página 1 e 2: SP + Resumo

        for anexo_path in anexos_paths:  # Página 3+
            merger.append(anexo_path)

        with open(pdf_final_path, "wb") as f_out:
            merger.write(f_out)
        merger.close()

        # Registrar pagamentos
        for calc_id in calculos_ids:
            if "_" not in calc_id:
                continue

            origem, id_numerico = calc_id.split("_", 1)
            tabela_artista = {
                "norm": "normal",
                "esp": "especial",
                "ass": "assisao"
            }.get(origem, "normal")

            pagamento = PagamentoRealizado(
                artista_id=sp_obj.artista_id,
                tabela_artista=tabela_artista,
                sp_id=sp_obj.id,
                mes=int(mes),
                ano=int(ano),
                valor_eur=valor_eur_float,
                valor_brl=valor_brl_total,
                cotacao=cotacao_float,
                vencimento=datetime.strptime(vencimento, "%Y-%m-%d").date(),
                data_pagamento=datetime.today().date(),
                status=status.lower(),
                herdeiro=None,
                calculo_id=calc_id
            )
            db.session.add(pagamento)

        db.session.commit()

        # Nome do arquivo final
        nome_download_pdf = sp_obj.nome_arquivo
        if nome_download_pdf.lower().endswith('.xlsx'):
            nome_download_pdf = nome_download_pdf[:-5] + '.pdf'
        elif not nome_download_pdf.lower().endswith('.pdf'):
            nome_download_pdf += '.pdf'

        @after_this_request
        def limpar_arquivos(response):
            try:
                arquivos = [caminho_excel, caminho_pdf, pdf_final_path] + anexos_paths
                for arquivo in arquivos:
                    if os.path.exists(arquivo):
                        os.remove(arquivo)
            except Exception as e:
                print(f"[AVISO] Falha ao limpar arquivos: {str(e)}")
            return response

        return send_file(
            pdf_final_path,
            as_attachment=True,
            download_name=nome_download_pdf,
            mimetype="application/pdf"
        )

    except Exception as e:
        print(f"[ERRO CRÍTICO] {str(e)}")
        print(traceback.format_exc())
        return f"Erro interno ao processar a requisição: {str(e)}", 500

# ======================
# ROTAS PAG RETROATIVOS
# ======================

from sqlalchemy import or_, func
import unicodedata
from sqlalchemy import extract
import logging
app.logger.setLevel(logging.DEBUG)

@app.route('/retroativos')
def retroativos():
    # Importações necessárias para a rota.
    from sqlalchemy import func
    from retroativos_models import RetroativoCalculado
    import unicodedata
    from datetime import datetime
    from collections import defaultdict
    from flask import request, render_template

    # Função auxiliar para normalizar texto, caso necessário.
    # Note: A importação unidecode não é usada aqui, mas está no código principal.
    def normalizar(texto):
        return unicodedata.normalize("NFKD", texto).encode("ASCII", "ignore").decode("utf-8").strip().lower()

    # Parâmetros de entrada para paginação e busca.
    page = request.args.get('page', 1, type=int)
    per_page = 20
    search_query = request.args.get('search', '').strip()
    
    # Query base para obter artistas distintos.
    # Usamos distinct() para garantir que cada artista apareça apenas uma vez.
    query_artistas = db.session.query(RetroativoCalculado.artista).distinct()

    # Aplica o filtro de busca se houver uma query de pesquisa.
    if search_query:
        query_artistas = query_artistas.filter(func.lower(RetroativoCalculado.artista).like(f"%{search_query.lower()}%"))

    # Conta o total de artistas para a paginação. Esta operação ainda pode ser lenta em grandes volumes,
    # mas é necessária para determinar o número de páginas.
    total_artistas = query_artistas.count()
    
    # Busca apenas os artistas da página atual.
    # A ordenação é importante para garantir que a paginação seja consistente.
    artistas_pagina = (
        query_artistas.order_by(RetroativoCalculado.artista)
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    nomes_artistas = [a[0] for a in artistas_pagina]

    # =================================================================================
    # OTIMIZAÇÃO CRÍTICA: Evitar N+1 queries.
    # Em vez de fazer uma query por artista, fazemos UMA SÓ query para todos eles.
    # =================================================================================
    
    # Obter anos disponíveis
    min_max_anos = db.session.query(
        func.min(RetroativoCalculado.ano),
        func.max(RetroativoCalculado.ano)
    ).first()

    min_ano = int(min_max_anos[0]) if min_max_anos[0] else datetime.now().year
    max_ano = int(min_max_anos[1]) if min_max_anos[1] else datetime.now().year
    anos_disponiveis = list(range(min_ano, max_ano + 1))
    anos_tabela = anos_disponiveis

    # Query única para buscar todos os totais de lucro para os artistas da página.
    # Agrupa por artista e ano para obter a soma de 'lucro_liquido'.
    if nomes_artistas:
        resultados_consolidados = (
            db.session.query(
                RetroativoCalculado.artista,
                RetroativoCalculado.ano,
                func.sum(RetroativoCalculado.lucro_liquido).label('total')
            )
            .filter(RetroativoCalculado.artista.in_(nomes_artistas))
            .group_by(RetroativoCalculado.artista, RetroativoCalculado.ano)
            .all()
        )
    else:
        resultados_consolidados = []

    # Processa os resultados em uma estrutura de dados eficiente para o template.
    # Agora passamos o valor Decimal diretamente para o dicionário, sem convertê-lo para float.
    artistas_tabela_dict = defaultdict(lambda: defaultdict(Decimal))
    for r in resultados_consolidados:
        artistas_tabela_dict[r.artista][int(r.ano)] = r.total

    artistas_tabela = []
    for nome in nomes_artistas:
        artistas_tabela.append({
            'id': nome,
            'nome': nome,
            'valores': artistas_tabela_dict.get(nome, {})
        })

    # Renderiza o template com os dados agora pré-processados e otimizados.
    return render_template(
        'Retroativos.html',
        artistas=nomes_artistas,
        min_ano=min_ano,
        max_ano=max_ano,
        anos_disponiveis=anos_disponiveis,
        anos_tabela=anos_tabela,
        artistas_tabela=artistas_tabela,
        current_page=page,
        total_pages=(total_artistas + per_page - 1) // per_page,
        search_query=search_query,
        cotacoes=Cotacao.query.all()
    )

titulos_cache = {}

# Função de normalização de nome (copiada de processar_retroativos.py para consistência)
def normalizar_nome_artista(nome):
    """
    Normaliza o nome do artista para um formato consistente, removendo
    acentos, caracteres especiais, e variações comuns como "e ou".
    """
    if not nome:
        return ""
    nome_normalizado = unidecode(nome).lower().strip()
    nome_normalizado = re.sub(r'\s+e\s+ou\s+|\s+ou\s+', ' ', nome_normalizado)
    nome_normalizado = re.sub(r'[^a-z0-9 ]', '', nome_normalizado)
    return ' '.join(nome_normalizado.split()).strip()

@app.route('/api/relatorio_retroativo', methods=['POST'])
def api_relatorio_retroativo():
    """
    Endpoint de API para retornar dados de retroativos consolidados em JSON.
    Recebe os filtros do frontend e retorna os resultados agregados.
    """
    try:
        getcontext().prec = 28
        getcontext().rounding = ROUND_HALF_UP

        data = request.get_json()
        if not data:
            current_app.logger.error("API Relatório: Nenhum dado JSON recebido.")
            return jsonify({"erro": "Nenhum dado JSON recebido"}), 400

        artistas_selecionados = data.get('artistas', [])
        ano_inicial = int(data.get('ano_inicial'))
        mes_inicial = int(data.get('mes_inicial'))
        ano_final = int(data.get('ano_final'))
        mes_final = int(data.get('mes_final'))
        titulos_selecionados = data.get('titulos', [])

        current_app.logger.debug(f"API Relatório: Artistas selecionados (frontend): {artistas_selecionados}")
        current_app.logger.debug(f"API Relatório: Período: {mes_inicial}/{ano_inicial} a {mes_final}/{ano_final}")
        current_app.logger.debug(f"API Relatório: Títulos selecionados (frontend): {titulos_selecionados}")

        if not artistas_selecionados:
            return jsonify({"erro": "Nenhum artista selecionado"}), 400

        # ====================================================================
        # Consulta AGREGADA: Soma os valores por Artista, Título e Ano no Período
        # CORRIGIDO: Agora consulta diretamente RetroativoCalculado, que é onde os dados são salvos.
        # ====================================================================
        query = db.session.query(
            RetroativoCalculado.artista, # Usar artista de RetroativoCalculado
            RetroativoCalculado.titulo,  # Usar titulo de RetroativoCalculado
            RetroativoCalculado.ano, 
            func.sum(RetroativoCalculado.lucro_liquido).label('lucro_total') # Usar lucro_liquido
        ).filter(
            RetroativoCalculado.artista.in_(artistas_selecionados)
        )

        # Lógica para filtrar por período (abrange múltiplos anos se necessário)
        if ano_inicial == ano_final:
            query = query.filter(
                RetroativoCalculado.ano == ano_inicial,
                RetroativoCalculado.mes.between(mes_inicial, mes_final)
            )
        else:
            conditions_period = []
            conditions_period.append(
                (RetroativoCalculado.ano == ano_inicial) & (RetroativoCalculado.mes >= mes_inicial)
            )
            for interm_year in range(ano_inicial + 1, ano_final):
                conditions_period.append(RetroativoCalculado.ano == interm_year)
            if ano_final > ano_inicial:
                conditions_period.append(
                    (RetroativoCalculado.ano == ano_final) & (RetroativoCalculado.mes <= mes_final)
                )
            query = query.filter(or_(*conditions_period))

        # Aplica filtro por títulos selecionados, se houver
        if titulos_selecionados:
            query = query.filter(RetroativoCalculado.titulo.in_(titulos_selecionados))

        # Agrupa os resultados por Artista, Título e Ano
        query = query.group_by(
            RetroativoCalculado.artista,
            RetroativoCalculado.titulo,
            RetroativoCalculado.ano 
        ).order_by(RetroativoCalculado.artista, RetroativoCalculado.titulo, RetroativoCalculado.ano)

        current_app.logger.debug(f"API Relatório: SQL Query gerada: {query}")

        aggregated_records = query.all()
        current_app.logger.debug(f"API Relatório: Registros agregados do DB: {aggregated_records}")

        # Prepara os dados para o JSON response
        results = []
        if aggregated_records: 
            for rec in aggregated_records:
                results.append({
                    'artista': rec.artista, 
                    'titulo': rec.titulo,   
                    'ano': rec.ano, 
                    'lucro_liquido': str(rec.lucro_total) # Converte Decimal para string para JSON
                })
        
        current_app.logger.debug(f"API Relatório: Dados enviados ao frontend: {results}")
        return jsonify({"dados": results})

    except Exception as e:
        current_app.logger.error(f"Erro na API de relatório: {str(e)}", exc_info=True)
        return jsonify({"erro": f"Erro interno do servidor: {str(e)}"}), 500

@app.route('/api/titulos_por_nome/<nome_artista>')
def api_titulos_por_nome(nome_artista):
    import unicodedata

    def normalizar(texto):
        return unicodedata.normalize("NFKD", texto).encode("ASCII", "ignore").decode("utf-8").strip().lower()

    nome_normalizado = normalizar(nome_artista)

    # Verifica se o nome normalizado está no cache
    if nome_normalizado in titulos_cache:
        return jsonify(titulos_cache[nome_normalizado])

    titulos_encontrados = []
    todos_titulos = db.session.query(RetroativoTitulo.artista_nome, RetroativoTitulo.titulo).all()

    for artista_nome_db, titulo in todos_titulos:
        # Usa fuzzy matching para encontrar artistas com nomes semelhantes
        if fuzz.ratio(normalizar(artista_nome_db), nome_normalizado) >= 90:
            titulos_encontrados.append(titulo)

    # Armazena os resultados no cache antes de retornar
    titulos_cache[nome_normalizado] = titulos_encontrados
    return jsonify(titulos_encontrados)

@app.route("/api/titulos_por_artista/<int:id>")
def titulos_por_artista(id):
    artista = Artista.query.get(id)
    if not artista:
        return jsonify([])
    
    titulos = RetroativoTitulo.query.filter_by(artista=artista.nome).all()
    return jsonify([t.titulo for t in titulos])


# A sua rota de exportação completa e corrigida
@csrf.exempt
@app.route('/exportar_retroativo', methods=['POST'])
def exportar_retroativo():
    try:
        import json
        from io import BytesIO
        from datetime import datetime
        from decimal import Decimal, getcontext, ROUND_HALF_UP
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm, mm
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from sqlalchemy import func, or_, case, Integer, cast

        getcontext().prec = 28
        getcontext().rounding = ROUND_HALF_UP

        # --- Função para ler campos ocultos que vêm como JSON ---
        def parse_lista_hidden(value: str):
            value = (value or "").strip()
            if not value:
                return []
            try:
                data = json.loads(value)
                if isinstance(data, list):
                    return [str(x).strip() for x in data if str(x).strip()]
                elif isinstance(data, str):
                    return [data.strip()]
            except Exception:
                return [s.strip() for s in value.split(",") if s.strip()]
            return []

        # --- Leitura dos campos do formulário ---
        percentual_geral_str = (request.form.get('percentual', '0') or '0').replace(",", ".")
        cotacao_id = request.form.get('cotacao_id')
        ano_inicial = request.form.get('anoInicialHidden')
        mes_inicial = request.form.get('mesInicialHidden')
        ano_final = request.form.get('anoFinalHidden')
        mes_final = request.form.get('mesFinalHidden')
        artistas_hidden = request.form.get('artistasHidden', '[]')
        titulos_hidden = request.form.get('titulosHidden', '[]')
        percentuais_json = request.form.get('percentuais_titulos', '{}')

        # --- Parse ---
        percentual_geral = Decimal(percentual_geral_str)
        artistas_selecionados = parse_lista_hidden(artistas_hidden)
        titulos_selecionados = sorted(set(parse_lista_hidden(titulos_hidden)))

        try:
            percentuais_por_titulo_raw = json.loads(percentuais_json or '{}')
        except Exception:
            percentuais_por_titulo_raw = {}
        percentuais_por_titulo = {}
        for k, v in percentuais_por_titulo_raw.items():
            val = str(v).replace(",", ".")
            try:
                percentuais_por_titulo[k] = Decimal(val)
            except:
                continue

        if not artistas_selecionados:
            return "Nenhum artista válido", 400

        # --- Cotação ---
        cotacao = db.session.get(Cotacao, cotacao_id)
        if not cotacao:
            return "Cotação não encontrada", 400
        cotacao.valor = Decimal(str(cotacao.valor))

        ano_inicial = int(ano_inicial)
        mes_inicial = int(mes_inicial)
        ano_final = int(ano_final)
        mes_final = int(mes_final)

        # --- Mapeamento de mês textual para número ---
        mes_col = RetroativoCalculado.mes
        mes_case = case(
            (func.lower(mes_col) == 'janeiro', 1),
            (func.lower(mes_col) == 'fevereiro', 2),
            (func.lower(mes_col) == 'março', 3),
            (func.lower(mes_col) == 'marco', 3),
            (func.lower(mes_col) == 'abril', 4),
            (func.lower(mes_col) == 'maio', 5),
            (func.lower(mes_col) == 'junho', 6),
            (func.lower(mes_col) == 'julho', 7),
            (func.lower(mes_col) == 'agosto', 8),
            (func.lower(mes_col) == 'setembro', 9),
            (func.lower(mes_col) == 'outubro', 10),
            (func.lower(mes_col) == 'novembro', 11),
            (func.lower(mes_col) == 'dezembro', 12),
            else_=cast(mes_col, Integer)
        )

        # --- Query ---
        query = db.session.query(
            RetroativoCalculado.artista,
            RetroativoCalculado.titulo,
            RetroativoCalculado.ano,
            func.sum(RetroativoCalculado.lucro_liquido).label('lucro_total'),
        ).filter(
            func.lower(RetroativoCalculado.artista).in_([a.lower() for a in artistas_selecionados])
        )

        if titulos_selecionados:
            query = query.filter(
                func.lower(RetroativoCalculado.titulo).in_([t.lower() for t in titulos_selecionados])
            )

        if ano_inicial == ano_final:
            query = query.filter(
                RetroativoCalculado.ano == ano_inicial,
                mes_case.between(mes_inicial, mes_final)
            )
        else:
            conditions_period = [
                (RetroativoCalculado.ano == ano_inicial) & (mes_case >= mes_inicial)
            ]
            for interm_year in range(ano_inicial + 1, ano_final):
                conditions_period.append(RetroativoCalculado.ano == interm_year)
            conditions_period.append(
                (RetroativoCalculado.ano == ano_final) & (mes_case <= mes_final)
            )
            query = query.filter(or_(*conditions_period))

        query = query.group_by(
            RetroativoCalculado.artista,
            RetroativoCalculado.titulo,
            RetroativoCalculado.ano
        ).order_by(
            RetroativoCalculado.artista,
            RetroativoCalculado.titulo,
            RetroativoCalculado.ano
        )

        aggregated_records = query.all()

        # --- Preparar dados para PDF ---
        data_for_table = []
        total_lucro_liquido = Decimal('0')
        total_aplicado = Decimal('0')
        total_convertido = Decimal('0')
        
        for rec in aggregated_records:
            lucro_liquido_decimal = Decimal(str(rec.lucro_total))
            percentual = percentuais_por_titulo.get(rec.titulo, percentual_geral)
            aplicado = (lucro_liquido_decimal * (percentual / Decimal('100')))
            convertido = (aplicado * cotacao.valor)
            
            total_lucro_liquido += lucro_liquido_decimal
            total_aplicado += aplicado
            total_convertido += convertido
            
            data_for_table.append([
                rec.artista,
                rec.ano,
                rec.titulo,
                f"€ {lucro_liquido_decimal:,.2f}",
                f"{percentual:.2f}%",
                f"€ {aplicado:,.2f}",
                f"R$ {convertido:,.2f}"
            ])
        
        # Adicionar linha de total
        data_for_table.append([
            "TOTAL GERAL:",
            "",
            "",
            f"€ {total_lucro_liquido:,.2f}",
            "",
            f"€ {total_aplicado:,.2f}",
            f"R$ {total_convertido:,.2f}"
        ])

        # --- Criar PDF ---
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=A4,
            leftMargin=1.5*cm,
            rightMargin=1.5*cm,
            topMargin=1.5*cm,
            bottomMargin=1.5*cm
        )
        elements = []
        
        # Estilos
        styles = getSampleStyleSheet()
        
        # Estilo para título principal
        style_title = ParagraphStyle(
            'Title',
            parent=styles["Title"],
            fontSize=16,
            alignment=1,  # Centro
            spaceAfter=6,
            fontName="Helvetica-Bold"
        )
        
        # Estilo para subtítulo
        style_subtitle = ParagraphStyle(
            'Subtitle',
            parent=styles["Heading2"],
            fontSize=12,
            alignment=1,
            spaceAfter=12,
            fontName="Helvetica"
        )
        
        # Estilo para informações
        style_info = ParagraphStyle(
            'Info',
            parent=styles["Normal"],
            fontSize=10,
            spaceAfter=4,
            fontName="Helvetica"
        )
        
        # Estilo para cabeçalhos da tabela
        style_table_header = ParagraphStyle(
            'TableHeader',
            parent=styles["Normal"],
            fontSize=9,
            fontName="Helvetica-Bold",
            textColor=colors.white,
            alignment=1
        )
        
        # Estilo para células da tabela
        style_table_cell = ParagraphStyle(
            'TableCell',
            parent=styles["Normal"],
            fontSize=8,
            fontName="Helvetica",
            alignment=1
        )
        
        # Estilo para total
        style_total = ParagraphStyle(
            'Total',
            parent=styles["Normal"],
            fontSize=12,
            textColor=colors.black,
            spaceBefore=20,
            fontName="Helvetica-Bold",
            alignment=2  # Direita
        )
        
        # Cabeçalho
        elements.append(Paragraph("Believe®", style_title))
        elements.append(Paragraph("Distribution services", style_subtitle))
        elements.append(Spacer(2, 0.5*cm))
        
        # Informações do relatório
        periodo = f"<b>Período:</b> {mes_inicial}/{ano_inicial} a {mes_final}/{ano_final}"
        artistas = f"<b>Artistas:</b> {', '.join(artistas_selecionados)}"
        cotacao_info = f"<b>Cotação:</b> R$ {cotacao.valor:.4f}"
        
        elements.append(Paragraph(periodo, style_info))
        elements.append(Paragraph(artistas, style_info))
        elements.append(Paragraph(cotacao_info, style_info))
        elements.append(Spacer(1, 0.8*cm))
        
        # Tabela de dados - converter todos os dados para Paragraphs para melhor controle
        headers = [
            Paragraph("Artista", style_table_header),
            Paragraph("Ano", style_table_header),
            Paragraph("Título", style_table_header),
            Paragraph("Lucro Líquido (€)", style_table_header),
            Paragraph("Percentual (%)", style_table_header),
            Paragraph("Lucro Artis (€)", style_table_header),
            Paragraph("Valor Convertido (R$)", style_table_header)
        ]
        
        table_data = [headers]
        
        for row in data_for_table[:-1]:  # Todas as linhas exceto o total
            table_row = []
            for cell in row:
                table_row.append(Paragraph(str(cell), style_table_cell))
            table_data.append(table_row)
        
        # Linha de total (estilo diferente)
        total_row = []
        for cell in data_for_table[-1]:
            if cell.startswith("TOTAL GERAL:"):
                total_row.append(Paragraph(cell, ParagraphStyle(
                    'TotalCell',
                    parent=style_table_cell,
                    fontName="Helvetica-Bold"
                )))
            else:
                total_row.append(Paragraph(cell, ParagraphStyle(
                    'TotalCell',
                    parent=style_table_cell,
                    fontName="Helvetica-Bold",
                    alignment=2  # Direita para valores
                )))
        table_data.append(total_row)
        
        # Criar tabela com dimensões precisas
        table = Table(
            table_data, 
            colWidths=[
                3.0*cm,  # Artista
                1.2*cm,  # Ano
                5.0*cm,  # Título
                2.0*cm,  # Lucro Líquido
                1.8*cm,  # Percentual
                2.0*cm,  # Lucro x %
                2.5*cm   # Valor Convertido
            ],
            repeatRows=1  # Repetir cabeçalho em quebras de página
        )
        
        table.setStyle(TableStyle([
            # Estilo do cabeçalho
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#4f46e5")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('ALIGN', (0,0), (-1,0), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('FONTSIZE', (0,0), (-1,0), 9),
            ('BOTTOMPADDING', (0,0), (-1,0), 6),
            ('TOPPADDING', (0,0), (-1,0), 6),
            
            # Estilo das linhas de dados
            ('FONTSIZE', (0,1), (-2,-2), 8),
            ('ALIGN', (0,1), (-1,-2), 'CENTER'),
            ('ALIGN', (3,1), (6,-2), 'RIGHT'),  # Alinhar valores à direita
            
            # Linhas divisórias
            ('GRID', (0,0), (-1,-2), 0.5, colors.lightgrey),
            
            # Estilo da linha de total
            ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor("#e5e7eb")),
            ('FONTSIZE', (0,-1), (-1,-1), 9),
            ('LINEABOVE', (0,-1), (-1,-1), 1, colors.black),
            ('LINEBELOW', (0,-1), (-1,-1), 1, colors.black),
            
            # Espaçamento interno
            ('PADDING', (0,0), (-1,-1), 3),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.5*cm))
        
        # Total em destaque
        total_convertido_str = f"<b>Valor Total Convertido (R$): R$ {total_convertido:,.2f}</b>"
        elements.append(Paragraph(total_convertido_str, style_total))
        
        # Rodapé
        elements.append(Spacer(1, 1*cm))
        elements.append(Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 
                                ParagraphStyle(
                                    'Footer',
                                    parent=styles["Normal"],
                                    fontSize=8,
                                    textColor=colors.grey,
                                    alignment=2
                                )))
        
        # Construir PDF
        doc.build(elements)
        buffer.seek(0)
        
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'relatorio_retroativos_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        )

    except Exception as e:
        current_app.logger.error(f"Erro ao exportar relatório: {str(e)}", exc_info=True)
        return "Erro interno ao gerar relatório", 500

@app.route('/admin/limpar_cache_titulos')
def limpar_cache_titulos():
    titulos_cache.clear()
    return "Cache de títulos limpo com sucesso", 200

@app.route('/sua-rota')
def sua_view():
    return render_template('seu_template.html',
        current_year=datetime.now().year,  # Já é inteiro
        current_month=datetime.now().month,
        # ... outros parâmetros
    )


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')