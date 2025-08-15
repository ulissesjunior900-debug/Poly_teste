CREATE TABLE usuario (
	id INTEGER NOT NULL, 
	username VARCHAR(80), 
	nome VARCHAR(100) NOT NULL, 
	email VARCHAR(100) NOT NULL, 
	senha VARCHAR(128) NOT NULL, 
	cpf VARCHAR(14), 
	funcao VARCHAR(50), 
	ativo BOOLEAN, 
	data_criacao DATETIME, 
	foto VARCHAR(200), 
	PRIMARY KEY (id), 
	UNIQUE (username), 
	UNIQUE (email)
)

CREATE TABLE artista (
	id INTEGER NOT NULL, 
	nome VARCHAR(100) NOT NULL, 
	percentual FLOAT NOT NULL, 
	PRIMARY KEY (id)
)

CREATE TABLE arquivo_importado (
	id INTEGER NOT NULL, 
	nome_arquivo VARCHAR(200) NOT NULL, 
	caminho VARCHAR(300) NOT NULL, 
	data_upload DATETIME, 
	PRIMARY KEY (id)
)

CREATE TABLE artista_especial (
	id INTEGER NOT NULL, 
	nome VARCHAR(100) NOT NULL, 
	variacoes TEXT, 
	data_criacao DATETIME, 
	percentual_padrao FLOAT, 
	tipo VARCHAR(50) NOT NULL, 
	PRIMARY KEY (id)
)

CREATE TABLE cotacao (
	id INTEGER NOT NULL, 
	mes VARCHAR(10) NOT NULL, 
	ano VARCHAR(4) NOT NULL, 
	valor FLOAT NOT NULL, 
	PRIMARY KEY (id)
)

CREATE TABLE sp_importada (
	id INTEGER NOT NULL, 
	artista_id INTEGER NOT NULL, 
	nome_arquivo VARCHAR(200) NOT NULL, 
	caminho VARCHAR(300) NOT NULL, 
	identificacao VARCHAR(100), 
	data_upload DATETIME, 
	para_herdeiros BOOLEAN, 
	tabela_artista VARCHAR(10) NOT NULL, 
	PRIMARY KEY (id)
)

CREATE TABLE solicitacao_pagamento (
	id INTEGER NOT NULL, 
	artista_id INTEGER NOT NULL, 
	tipo VARCHAR(20) NOT NULL, 
	sp_id INTEGER NOT NULL, 
	calculos_ids VARCHAR NOT NULL, 
	cotacao FLOAT NOT NULL, 
	valor_eur FLOAT NOT NULL, 
	valor_brl FLOAT NOT NULL, 
	mes VARCHAR(2) NOT NULL, 
	ano VARCHAR(4) NOT NULL, 
	vencimento DATE NOT NULL, 
	status VARCHAR(20), 
	data_pagamento DATE, 
	PRIMARY KEY (id)
)

CREATE TABLE herdeiros (
	id INTEGER NOT NULL, 
	artista_id INTEGER NOT NULL, 
	nome VARCHAR(100) NOT NULL, 
	percentual FLOAT NOT NULL, 
	documento VARCHAR(50), 
	created_at DATETIME, 
	updated_at DATETIME, 
	PRIMARY KEY (id)
)

CREATE TABLE artista_info (
	id INTEGER NOT NULL, 
	nome_artista VARCHAR(255) NOT NULL, 
	total_catalogo INTEGER, 
	total_musicas INTEGER, 
	total_music_release INTEGER, 
	total_videos INTEGER, 
	PRIMARY KEY (id), 
	UNIQUE (nome_artista)
)

CREATE TABLE calculo_salvo (
	id INTEGER NOT NULL, 
	artista VARCHAR(100) NOT NULL, 
	artista_id INTEGER, 
	valor_eur FLOAT NOT NULL, 
	valor_brl FLOAT NOT NULL, 
	cotacao FLOAT NOT NULL, 
	mes VARCHAR(20) NOT NULL, 
	ano INTEGER NOT NULL, 
	planilha_usada VARCHAR(200), 
	data_calculo DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(artista_id) REFERENCES artista (id)
)

CREATE TABLE titulo_especial (
	id INTEGER NOT NULL, 
	titulo VARCHAR(200) NOT NULL, 
	percentual FLOAT NOT NULL, 
	artista_id INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(artista_id) REFERENCES artista_especial (id)
)

CREATE TABLE calculo_especial_salvo (
	id INTEGER NOT NULL, 
	artista VARCHAR(100) NOT NULL, 
	artista_id INTEGER, 
	arquivo_id INTEGER, 
	cotacao FLOAT NOT NULL, 
	mes VARCHAR(10) NOT NULL, 
	ano VARCHAR(4) NOT NULL, 
	valor_eur FLOAT NOT NULL, 
	valor_brl FLOAT NOT NULL, 
	data_calculo DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(artista_id) REFERENCES artista_especial (id), 
	FOREIGN KEY(arquivo_id) REFERENCES arquivo_importado (id)
)

CREATE TABLE calculo_assisao_salvo (
	id INTEGER NOT NULL, 
	artista VARCHAR(120) NOT NULL, 
	artista_id INTEGER, 
	arquivo_id INTEGER NOT NULL, 
	cotacao FLOAT NOT NULL, 
	mes INTEGER NOT NULL, 
	ano INTEGER NOT NULL, 
	valor_eur FLOAT NOT NULL, 
	valor_brl FLOAT NOT NULL, 
	detalhes TEXT, 
	data_calculo DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(artista_id) REFERENCES artista_especial (id), 
	FOREIGN KEY(arquivo_id) REFERENCES arquivo_importado (id)
)

CREATE TABLE pagamento_realizado (
	id INTEGER NOT NULL, 
	artista_id INTEGER NOT NULL, 
	tabela_artista VARCHAR(10) NOT NULL, 
	sp_id INTEGER, 
	mes INTEGER NOT NULL, 
	ano INTEGER NOT NULL, 
	valor_eur FLOAT NOT NULL, 
	valor_brl FLOAT NOT NULL, 
	cotacao FLOAT NOT NULL, 
	data_pagamento DATE NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	herdeiro VARCHAR(100), vencimento DATE, calculo_id VARCHAR(50), artista_nome VARCHAR(255), 
	PRIMARY KEY (id), 
	FOREIGN KEY(sp_id) REFERENCES sp_importada (id)
)

CREATE TABLE transacao (
	id INTEGER NOT NULL, 
	artista_id INTEGER, 
	valor FLOAT, 
	data DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(artista_id) REFERENCES artista (id)
)

CREATE TABLE alembic_version (
	version_num VARCHAR(32) NOT NULL, 
	CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
)

CREATE TABLE sqlite_sequence(name,seq)

CREATE TABLE retroativos_titulos (
	id INTEGER NOT NULL, 
	artista_nome VARCHAR(255) NOT NULL, 
	titulo VARCHAR(255) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uix_artista_titulo UNIQUE (artista_nome, titulo)
)

CREATE TABLE titulo_periodo_valor (
	id INTEGER NOT NULL, 
	artista VARCHAR(100) NOT NULL, 
	titulo VARCHAR(255) NOT NULL, 
	valor FLOAT NOT NULL, 
	ano INTEGER NOT NULL, 
	mes INTEGER, 
	origem_planilha VARCHAR(255), 
	criado_em DATETIME, 
	PRIMARY KEY (id)
)