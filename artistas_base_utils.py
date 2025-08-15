import pandas as pd
import unicodedata
import os
import re
from thefuzz import fuzz
from models import Artista, ArtistaInfo


# Função para remover acentos
def remover_acentos(txt):
    if not isinstance(txt, str):
        return txt
    return ''.join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')


# Função auxiliar para deduplicação fuzzy dos títulos
def fuzzy_dedupe(titulos, threshold=85):
    unique = []
    for t in titulos:
        if not any(fuzz.token_sort_ratio(t.lower(), u.lower()) >= threshold for u in unique):
            unique.append(t)
    return unique

# Função principal
def atualizar_base_artistas(db):
    import pandas as pd
    import os
    import re
    from thefuzz import fuzz
    from models import Artista, ArtistaEspecial, ArtistaInfo
    from unidecode import unidecode

    try:
        path_planilha = os.path.join('static', 'uploads', 'artistas_base', 'Catalogo_2025.xlsx')
        if not os.path.exists(path_planilha):
            print("❌ Planilha Catalogo_2025.xlsx não encontrada.")
            return

        df = pd.read_excel(path_planilha)
        df.columns = [col.strip().lower() for col in df.columns]

        column_map = {
            'nome do artista': 'nome do artista',
            'álbum': 'album',
            'album': 'album',
            'tipo de lançamento': 'tipo de lançamento',
            'título da faixa': 'título da faixa',
            'titulo da faixa': 'titulo da faixa',
        }
        df = df.rename(columns={col: column_map.get(col, col) for col in df.columns})

        required_columns = {'nome do artista', 'album', 'tipo de lançamento'}
        if not required_columns.issubset(df.columns):
            raise ValueError(f"❌ A planilha deve conter as colunas: {required_columns}")

        db.session.query(ArtistaInfo).delete()

        def normalizar(texto):
            return unidecode(str(texto).lower().strip())

        artistas_normais = Artista.query.all()
        artistas_especiais = ArtistaEspecial.query.filter_by(tipo='especial').all()
        artistas_assisao = ArtistaEspecial.query.filter_by(tipo='assisao').all()

        artistas_cadastrados = []

        for artista in artistas_normais + artistas_especiais + artistas_assisao:
            nome_principal = artista.nome.strip()
            nomes = [nome_principal]

            if hasattr(artista, 'variacoes') and artista.variacoes:
                nomes += [v.strip() for v in artista.variacoes.split("||")]

            titulos = []
            if hasattr(artista, 'titulos'):
                for t in artista.titulos:
                    if t.titulo:
                        titulos.append(normalizar(t.titulo))

            artistas_cadastrados.append({
                'nome_principal': nome_principal,
                'nomes_comparacao': [normalizar(n) for n in nomes],
                'titulos': set(titulos)
            })

        print(f"[INFO] Total de artistas cadastrados para comparação: {len(artistas_cadastrados)}")

        for artista in artistas_cadastrados:
            nome_principal = artista['nome_principal']
            nomes_comparacao = artista['nomes_comparacao']
            titulos_cadastrados = artista['titulos']
            linhas_match = []

            # Se for agrupamento (contém vírgula), dividir
            nomes_agrupados = [n.strip() for n in nome_principal.split(',') if n.strip()]
            nomes_agrupados_normalizados = [normalizar(n) for n in nomes_agrupados]

            for _, row in df.iterrows():
                nome_planilha = row.get('nome do artista', '')
                album = row.get('album', '')
                tipo = row.get('tipo de lançamento', '')
                faixa = row.get('título da faixa') or row.get('titulo da faixa')

                faixa = str(faixa).strip() if isinstance(faixa, str) else ''
                album = str(album).strip() if isinstance(album, str) else ''
                tipo = str(tipo).strip().lower() if isinstance(tipo, str) else ''
                nome_parts = re.split(r",| e | ft\. | feat\. | & ", nome_planilha, flags=re.IGNORECASE)
                nome_parts = [normalizar(p) for p in nome_parts]

                album_normalizado = normalizar(album)

                # Match simples com nomes principais ou variações
                match_nome = any(
                    any(fuzz.token_sort_ratio(p, n) >= 85 or n in p for n in nomes_comparacao)
                    for p in nome_parts
                )

                # Match de título do álbum
                match_album = album_normalizado in titulos_cadastrados

                # Match por sub-nomes agrupados (ex: Banda Carícias, Jorge Silva do Recife)
                match_grupo = any(
                    any(fuzz.token_sort_ratio(p, n) >= 85 or n in p for p in nome_parts)
                    for n in nomes_agrupados_normalizados
                )

                if match_nome or match_album or match_grupo:
                    linhas_match.append(row)

            if not linhas_match:
                print(f"[IGNORADO] {nome_principal} – nenhum match encontrado na planilha.")
                continue

            df_artista = pd.DataFrame(linhas_match)
            albuns_contados = set()
            musicas_unicas = set()
            musicas_por_album = set()

            for _, row in df_artista.iterrows():
                faixa = row.get('título da faixa') or row.get('titulo da faixa')
                album = row.get('album', '')
                tipo = row.get('tipo de lançamento', '')

                faixa = str(faixa).strip() if isinstance(faixa, str) else ''
                album = str(album).strip() if isinstance(album, str) else ''
                tipo = str(tipo).strip().lower() if isinstance(tipo, str) else ''

                if faixa:
                    musicas_unicas.add(faixa)

                if tipo == 'music release':
                    key = (album, faixa)
                    if key not in musicas_por_album:
                        albuns_contados.add(album)
                        musicas_por_album.add(key)

            total_albuns = len(albuns_contados)
            total_musicas = len(musicas_unicas)
            total_music_release = df_artista[df_artista['tipo de lançamento'].str.lower() == 'music release'].shape[0]
            total_videos = df_artista[df_artista['tipo de lançamento'].str.lower().isin(['music video', 'packshot video'])].shape[0]

            info = ArtistaInfo.query.filter(ArtistaInfo.nome_artista.ilike(nome_principal)).first()
            if not info:
                info = ArtistaInfo(nome_artista=nome_principal)
                db.session.add(info)

            info.total_catalogo = total_albuns
            info.total_musicas = total_musicas
            info.total_music_release = total_music_release
            info.total_videos = total_videos

            print(f"[Atualizado] {nome_principal} → {total_albuns} álbuns | {total_musicas} músicas | {total_music_release} Music Release | {total_videos} Vídeos")

        db.session.commit()
        print("✅ Base de artistas atualizada com sucesso.")

    except Exception as e:
        print(f"❌ Erro ao atualizar base de artistas: {e}")
