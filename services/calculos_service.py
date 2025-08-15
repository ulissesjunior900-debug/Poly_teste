# services/calculos_service.py
from models import CalculoSalvo, CalculoEspecialSalvo, CalculoAssisaoSalvo, Artista, ArtistaEspecial
from typing import List, Dict, Any, Optional
from flask import current_app
from datetime import datetime

def construir_calculos_disponiveis() -> List[Dict[str, Any]]:
    """
    Constroi lista de cálculos serializáveis para JSON com tratamento de erros robusto.
    
    Returns:
        List[Dict]: Dados no formato:
        {
            'id': int,
            'artista': str,
            'artista_id': Optional[int],
            'valor_eur': float,
            'mes': str,
            'ano': str,
            'status': str,
            'tipo': str,
            'data_criacao': Optional[str]
        }
    """
    def safe_serialize(value, default=None) -> Any:
        """Converte valores para tipos serializáveis com fallback seguro"""
        if value is None:
            return default
        if isinstance(value, (int, float, str, bool)):
            return value
        if isinstance(value, datetime):
            return value.isoformat()
        try:
            return str(value)
        except Exception:
            return default

    def get_artist_id(artista_obj) -> Optional[int]:
        """Obtém ID do artista com verificação de atributos"""
        try:
            return int(artista_obj.id) if hasattr(artista_obj, 'id') else None
        except (ValueError, TypeError):
            return None

    def encontrar_artista(nome: Optional[str], modelo) -> Any:
        """Busca artista com tratamento completo para valores inválidos"""
        if not nome:
            return None
            
        try:
            nome_busca = str(nome).strip().lower()
            for artista in modelo.query.all():
                if not hasattr(artista, 'nome'):
                    continue
                    
                # Verifica nome principal
                if str(getattr(artista, 'nome', '')).strip().lower() == nome_busca:
                    return artista
                
                # Verifica variações
                if hasattr(artista, 'variacoes') and artista.variacoes:
                    try:
                        variacoes = [
                            str(v).strip().lower() 
                            for v in artista.variacoes.split("||") 
                            if v and str(v).strip()
                        ]
                        if nome_busca in variacoes:
                            return artista
                    except AttributeError:
                        continue
            return None
        except Exception as e:
            current_app.logger.error(f"Erro ao buscar artista: {str(e)}")
            return None

    try:
        calculos = []
        
        # Processa cada tipo de cálculo
        for model, tipo in [
            (CalculoSalvo, 'regular'),
            (CalculoEspecialSalvo, 'especial'),
            (CalculoAssisaoSalvo, 'assessoria')
        ]:
            for calculo in model.query.all():
                try:
                    artista = encontrar_artista(
                        getattr(calculo, 'artista', None),
                        Artista if tipo == 'regular' else ArtistaEspecial
                    )
                    
                    calculos.append({
                        'id': safe_serialize(getattr(calculo, 'id', 0), 0),
                        'artista': safe_serialize(getattr(calculo, 'artista', ''), ''),
                        'artista_id': get_artist_id(artista),
                        'valor_eur': safe_serialize(getattr(calculo, 'valor_eur', 0.0), 0.0),
                        'mes': safe_serialize(getattr(calculo, 'mes', ''), ''),
                        'ano': safe_serialize(getattr(calculo, 'ano', ''), ''),
                        'status': 'aguardando',
                        'tipo': tipo,
                        'data_criacao': safe_serialize(getattr(calculo, 'data_criacao', None))
                    })
                except Exception as e:
                    current_app.logger.error(f"Erro ao processar cálculo {calculo.id}: {str(e)}")
                    continue

        return calculos

    except Exception as e:
        current_app.logger.error(f"Erro geral ao construir cálculos: {str(e)}", exc_info=True)
        return []