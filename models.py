
from datetime import datetime, date
from extensions import db
from werkzeug.security import generate_password_hash, check_password_hash

class Usuario(db.Model):
    __tablename__ = 'usuario'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=True)
    nome = db.Column(db.String(100), nullable=False, default='Admin')
    email = db.Column(db.String(100), unique=True, nullable=False)
    senha = db.Column(db.String(128), nullable=False) # Armazena o hash da senha
    cpf = db.Column(db.String(14))
    funcao = db.Column(db.String(50))
    ativo = db.Column(db.Boolean, default=True)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    foto = db.Column(db.String(200))

    # NOVO MÉTODO PARA VERIFICAR A SENHA
    def verificar_senha(self, senha_texto_claro):
        """
        Verifica se a senha em texto claro corresponde ao hash armazenado.
        """
        return check_password_hash(self.senha, senha_texto_claro)

    # Opcional: Um método para definir a senha (gerar o hash)
    def set_senha(self, senha_texto_claro):
        self.senha = generate_password_hash(senha_texto_claro)

    def __repr__(self):
        return f'<Usuario {self.username}>'

class Artista(db.Model):
    __tablename__ = 'artista'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    percentual = db.Column(db.Float, nullable=False)


class ArquivoImportado(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome_arquivo = db.Column(db.String(200), nullable=False)
    caminho = db.Column(db.String(300), nullable=False, default='uploads/sem_caminho')
    data_upload = db.Column(db.DateTime, default=datetime.utcnow)


class CalculoSalvo(db.Model):
    __tablename__ = 'calculo_salvo'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    artista = db.Column(db.String(100), nullable=False)
    artista_id = db.Column(db.Integer, db.ForeignKey('artista.id'), nullable=True)
    valor_eur = db.Column(db.Float, nullable=False)
    valor_brl = db.Column(db.Float, nullable=False)
    cotacao = db.Column(db.Float, nullable=False)
    mes = db.Column(db.String(20), nullable=False)
    ano = db.Column(db.Integer, nullable=False)
    planilha_usada = db.Column(db.String(200))
    data_calculo = db.Column(db.DateTime, default=datetime.utcnow)


class ArtistaEspecial(db.Model):
    __tablename__ = 'artista_especial'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    variacoes = db.Column(db.Text, nullable=True)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    percentual_padrao = db.Column(db.Float, nullable=True)
    tipo = db.Column(db.String(50), nullable=False)

    titulos = db.relationship(
        'TituloEspecial',
        backref='artista',
        cascade="all, delete-orphan"
    )

    def obter_variacoes(self):
        return self.variacoes.split('||') if self.variacoes else []


class TituloEspecial(db.Model):
    __tablename__ = 'titulo_especial'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    percentual = db.Column(db.Float, nullable=False)
    artista_id = db.Column(db.Integer, db.ForeignKey('artista_especial.id'), nullable=False)


class Cotacao(db.Model):
    __tablename__ = 'cotacao'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    mes = db.Column(db.String(10), nullable=False)
    ano = db.Column(db.String(4), nullable=False)
    valor = db.Column(db.Float, nullable=False)


class CalculoEspecialSalvo(db.Model):
    __tablename__ = 'calculo_especial_salvo'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    artista = db.Column(db.String(100), nullable=False)
    artista_id = db.Column(db.Integer, db.ForeignKey('artista_especial.id'), nullable=True)
    arquivo_id = db.Column(db.Integer, db.ForeignKey('arquivo_importado.id'))
    cotacao = db.Column(db.Float, nullable=False)
    mes = db.Column(db.String(10), nullable=False)
    ano = db.Column(db.String(4), nullable=False)
    valor_eur = db.Column(db.Float, nullable=False)
    valor_brl = db.Column(db.Float, nullable=False)
    data_calculo = db.Column(db.DateTime, default=datetime.now)
    arquivo = db.relationship('ArquivoImportado', backref='calculos_especiais')

    arquivo = db.relationship('ArquivoImportado', backref='calculos_especiais')

    artista_especial = db.relationship('ArtistaEspecial', backref='calculos_especiais')


class CalculoAssisaoSalvo(db.Model):
    __tablename__ = 'calculo_assisao_salvo'

    id = db.Column(db.Integer, primary_key=True)
    artista = db.Column(db.String(120), nullable=False)
    artista_id = db.Column(db.Integer, db.ForeignKey('artista_especial.id'), nullable=True)
    arquivo_id = db.Column(db.Integer, db.ForeignKey('arquivo_importado.id'), nullable=False)
    cotacao = db.Column(db.Float, nullable=False)
    mes = db.Column(db.Integer, nullable=False)
    ano = db.Column(db.Integer, nullable=False)
    valor_eur = db.Column(db.Float, nullable=False)
    valor_brl = db.Column(db.Float, nullable=False)
    detalhes = db.Column(db.Text)
    data_calculo = db.Column(db.DateTime, nullable=False)

    arquivo = db.relationship('ArquivoImportado', backref='calculos_assisao')


from datetime import datetime

class SPImportada(db.Model):
    __tablename__ = 'sp_importada'

    id = db.Column(db.Integer, primary_key=True)
    artista_id = db.Column(db.Integer, nullable=False)  # Sem ForeignKey
    nome_arquivo = db.Column(db.String(200), nullable=False)
    caminho = db.Column(db.String(300), nullable=False)
    identificacao = db.Column(db.String(100), nullable=True)
    data_upload = db.Column(db.DateTime, default=datetime.utcnow)
    para_herdeiros = db.Column(db.Boolean, default=False)
    tabela_artista = db.Column(db.String(10), nullable=False, default='norm')  # 🔹 AQUI

    def __repr__(self):
        return f"<SP {self.nome_arquivo} - {self.identificacao}>"

    def to_dict(self, include_artista=False):
        data = {
            'id': self.id,
            'artista_id': self.artista_id,
            'nome_arquivo': self.nome_arquivo,
            'caminho': self.caminho,
            'identificacao': self.identificacao,
            'data_upload': self.data_upload.isoformat() if self.data_upload else None,
            'data_upload_formatada': self.data_upload.strftime('%d/%m/%Y %H:%M') if self.data_upload else None,
            'para_herdeiros': self.para_herdeiros,
            'tabela_artista': self.tabela_artista  # incluir na dict
        }
        return data

    @property
    def caminho_arquivo(self):
        return self.caminho

class SolicitacaoPagamento(db.Model):
    __tablename__ = 'solicitacao_pagamento'

    id = db.Column(db.Integer, primary_key=True)
    artista_id = db.Column(db.Integer, nullable=False)
    tipo = db.Column(db.String(20), nullable=False)
    sp_id = db.Column(db.Integer, nullable=False)
    calculos_ids = db.Column(db.String, nullable=False)
    cotacao = db.Column(db.Float, nullable=False)
    valor_eur = db.Column(db.Float, nullable=False)
    valor_brl = db.Column(db.Float, nullable=False)
    mes = db.Column(db.String(2), nullable=False)
    ano = db.Column(db.String(4), nullable=False)
    vencimento = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='aguardando')
    data_pagamento = db.Column(db.Date, nullable=True)

class PagamentoRealizado(db.Model):
    __tablename__ = 'pagamento_realizado'

    id = db.Column(db.Integer, primary_key=True)
    artista_id = db.Column(db.Integer, nullable=False)
    tabela_artista = db.Column(db.String(10), nullable=False)
    sp_id = db.Column(db.Integer, db.ForeignKey('sp_importada.id'))
    mes = db.Column(db.Integer, nullable=False)
    ano = db.Column(db.Integer, nullable=False)
    valor_eur = db.Column(db.Float, nullable=False)
    valor_brl = db.Column(db.Float, nullable=False)
    cotacao = db.Column(db.Float, nullable=False)
    vencimento = db.Column(db.Date)
    data_pagamento = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False)
    herdeiro = db.Column(db.String(100), nullable=True)
    calculo_id = db.Column(db.String(50), nullable=True)
    
    artista_nome = db.Column(db.String(255), nullable=True)  # só declare a coluna

    sp = db.relationship('SPImportada', backref='pagamentos')

    def __repr__(self):
        return f'<Pagamento {self.id} - ID:{self.artista_id} - €{self.valor_eur}>'


class Herdeiro(db.Model):
    __tablename__ = 'herdeiros'
    
    id = db.Column(db.Integer, primary_key=True)
    artista_id = db.Column(db.Integer, nullable=False)
    nome = db.Column(db.String(100), nullable=False)
    percentual = db.Column(db.Float, nullable=False)
    documento = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Herdeiro {self.nome} ({self.percentual}%) do artista {self.artista_id}>'


class Transacao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    artista_id = db.Column(db.Integer, db.ForeignKey('artista.id'))
    valor = db.Column(db.Float)
    data = db.Column(db.DateTime)

class ArtistaInfo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome_artista = db.Column(db.String(255), nullable=False, unique=True)
    total_catalogo = db.Column(db.Integer, default=0)  # total de "Album" distintos
    total_musicas = db.Column(db.Integer, default=0)
    total_music_release = db.Column(db.Integer, default=0)  # total de lançamentos Music Release
    total_videos = db.Column(db.Integer, default=0)  # total de lançamentos Music Video + Packshot Video
