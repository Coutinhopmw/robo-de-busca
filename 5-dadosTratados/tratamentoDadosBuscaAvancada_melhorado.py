import pandas as pd
import logging
import os
import re
from typing import Optional, Tuple, Dict, Any
import numpy as np
from pathlib import Path

# --- CONFIGURAÇÕES ---
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Configurações de caminhos
DIR_DADOS_AVANCADOS = Path(__file__).parent.parent / '4-dados_avancados_seguidores'
ARQUIVO_ENTRADA = DIR_DADOS_AVANCADOS / "dados_avancados_seguidores_enriquecido_bjjtocantins.csv"

# Arquivo de saída
NOME_ARQUIVO_ENTRADA = ARQUIVO_ENTRADA.name
ARQUIVO_SAIDA = Path(__file__).parent / f"dados_tratados_{NOME_ARQUIVO_ENTRADA}"

# --- CONSTANTES DE VALIDAÇÃO ---
class LimitesValidacao:
    """Constantes para validação de dados."""
    MAX_SEGUIDORES = 100_000_000  # 100 milhões
    MAX_SEGUINDO = 10_000  # 10 mil
    MAX_PUBLICACOES = 50_000  # 50 mil
    MAX_NOME_CHARS = 100
    MAX_BIO_CHARS = 500
    
    # Padrões regex compilados para performance
    EMOJI_PATTERN = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags (iOS)
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "\U0001FA70-\U0001FAFF"  # Symbols & Pictographs Extended-A
        "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
        "]+", 
        flags=re.UNICODE
    )
    
    RUIDO_BIO_PATTERNS = [
        re.compile(r'http\S+|www\.\S+'),  # Links
        re.compile(r'@\w+'),              # Menções
        re.compile(r'\b\d{2,}\b'),        # Números isolados
        re.compile(r'\s+')                # Espaços extras
    ]


class TratadorDados:
    """Classe principal para tratamento e limpeza de dados."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.estatisticas = {
            'duplicatas_removidas': 0,
            'outliers_corrigidos': 0,
            'bios_duplicadas_removidas': 0,
            'problemas_consistencia': []
        }
    
    def converter_para_numero_vetorizado(self, serie: pd.Series) -> pd.Series:
        """Versão vetorizada da conversão de números."""
        # Primeiro, trata valores nulos
        serie = serie.fillna('0')
        
        # Converte para string e normaliza
        serie_str = serie.astype(str).str.lower().str.strip()
        serie_str = serie_str.str.replace('.', '', regex=False)
        serie_str = serie_str.str.replace(',', '.', regex=False)
        
        # Trata valores com K e M
        mask_k = serie_str.str.contains('k', na=False)
        mask_m = serie_str.str.contains('m', na=False)
        
        # Para valores com K
        if mask_k.any():
            valores_k = serie_str[mask_k].str.replace('k', '', regex=False)
            valores_k = pd.to_numeric(valores_k, errors='coerce').fillna(0) * 1000
            serie_str[mask_k] = valores_k.astype(int).astype(str)
        
        # Para valores com M
        if mask_m.any():
            valores_m = serie_str[mask_m].str.replace('m', '', regex=False)
            valores_m = pd.to_numeric(valores_m, errors='coerce').fillna(0) * 1000000
            serie_str[mask_m] = valores_m.astype(int).astype(str)
        
        # Remove caracteres não numéricos e converte
        serie_numerica = serie_str.str.extract(r'(\d+)')[0]
        serie_numerica = pd.to_numeric(serie_numerica, errors='coerce').fillna(0)
        
        return serie_numerica.astype(int)
    
    def remover_emojis_vetorizado(self, serie: pd.Series) -> pd.Series:
        """Remove emojis de uma série de forma vetorizada."""
        # Filtra apenas strings não vazias
        mask_string = serie.notna() & (serie != '')
        
        if not mask_string.any():
            return serie
        
        # Aplica remoção de emoji apenas onde necessário
        serie_limpa = serie.copy()
        textos_com_emoji = serie[mask_string].astype(str)
        textos_limpos = textos_com_emoji.str.replace(
            LimitesValidacao.EMOJI_PATTERN, '', regex=True
        )
        # Remove espaços extras
        textos_limpos = textos_limpos.str.replace(r'\s+', ' ', regex=True).str.strip()
        
        serie_limpa[mask_string] = textos_limpos
        return serie_limpa
    
    def limpar_bio_contaminada_vetorizada(self, serie: pd.Series) -> pd.Series:
        """Limpa ruídos da bio de forma vetorizada."""
        if serie.empty:
            return serie
        
        serie_limpa = serie.astype(str).copy()
        
        # Aplica cada padrão de limpeza
        for pattern in LimitesValidacao.RUIDO_BIO_PATTERNS[:-1]:  # Exclui o último (espaços)
            serie_limpa = serie_limpa.str.replace(pattern, '', regex=True)
        
        # Trata espaços extras separadamente
        serie_limpa = serie_limpa.str.replace(r'\s+', ' ', regex=True).str.strip()
        
        return serie_limpa
    
    def validar_dados_numericos(self, df: pd.DataFrame) -> pd.DataFrame:
        """Valida e corrige outliers em dados numéricos."""
        self.logger.info("   [VALIDAÇÃO] Verificando outliers em dados numéricos...")
        
        outliers_corrigidos = 0
        
        # Validação de seguidores
        if 'n_seguidores' in df.columns:
            mask_outlier = df['n_seguidores'] > LimitesValidacao.MAX_SEGUIDORES
            outliers_corrigidos += mask_outlier.sum()
            df.loc[mask_outlier, 'n_seguidores'] = LimitesValidacao.MAX_SEGUIDORES
        
        # Validação de seguindo
        if 'n_seguindo' in df.columns:
            mask_outlier = df['n_seguindo'] > LimitesValidacao.MAX_SEGUINDO
            outliers_corrigidos += mask_outlier.sum()
            df.loc[mask_outlier, 'n_seguindo'] = LimitesValidacao.MAX_SEGUINDO
        
        # Validação de publicações
        if 'n_publicacoes' in df.columns:
            mask_outlier = df['n_publicacoes'] > LimitesValidacao.MAX_PUBLICACOES
            outliers_corrigidos += mask_outlier.sum()
            df.loc[mask_outlier, 'n_publicacoes'] = LimitesValidacao.MAX_PUBLICACOES
        
        self.estatisticas['outliers_corrigidos'] = outliers_corrigidos
        
        if outliers_corrigidos > 0:
            self.logger.info(f"   [VALIDAÇÃO] {outliers_corrigidos} outliers corrigidos.")
        else:
            self.logger.info("   [VALIDAÇÃO] Nenhum outlier encontrado.")
        
        return df
    
    def validar_consistencia_dados(self, df: pd.DataFrame) -> pd.DataFrame:
        """Valida consistência dos dados e identifica problemas."""
        self.logger.info("   [VALIDAÇÃO] Verificando consistência dos dados...")
        
        problemas = []
        
        # Verifica usernames vazios
        if 'username' in df.columns:
            usernames_vazios = df['username'].str.strip().eq('').sum()
            if usernames_vazios > 0:
                problemas.append(f"{usernames_vazios} usernames vazios")
        
        # Verifica nomes muito longos
        if 'nome_completo' in df.columns:
            nomes_longos = df['nome_completo'].str.len() > LimitesValidacao.MAX_NOME_CHARS
            if nomes_longos.sum() > 0:
                problemas.append(f"{nomes_longos.sum()} nomes muito longos (>{LimitesValidacao.MAX_NOME_CHARS} chars)")
                # Trunca nomes muito longos
                df.loc[nomes_longos, 'nome_completo'] = df.loc[nomes_longos, 'nome_completo'].str[:LimitesValidacao.MAX_NOME_CHARS]
        
        # Verifica bios muito longas
        if 'bio' in df.columns:
            bios_longas = df['bio'].str.len() > LimitesValidacao.MAX_BIO_CHARS
            if bios_longas.sum() > 0:
                problemas.append(f"{bios_longas.sum()} bios muito longas (>{LimitesValidacao.MAX_BIO_CHARS} chars)")
                # Trunca bios muito longas
                df.loc[bios_longas, 'bio'] = df.loc[bios_longas, 'bio'].str[:LimitesValidacao.MAX_BIO_CHARS]
        
        self.estatisticas['problemas_consistencia'] = problemas
        
        if problemas:
            self.logger.warning(f"   [VALIDAÇÃO] Problemas encontrados e corrigidos: {'; '.join(problemas)}")
        else:
            self.logger.info("   [VALIDAÇÃO] Dados consistentes.")
        
        return df
    
    def tratar_dados_ausentes(self, df: pd.DataFrame) -> pd.DataFrame:
        """Trata dados ausentes de forma otimizada."""
        # Colunas de texto
        colunas_texto = ["username", "nome_completo", "bio"]
        for col in colunas_texto:
            if col in df.columns:
                df[col] = df[col].fillna('')
        
        # Colunas numéricas
        colunas_numericas = ["n_publicacoes", "n_seguidores", "n_seguindo"]
        for col in colunas_numericas:
            if col in df.columns:
                df[col] = df[col].fillna('0')
        
        return df
    
    def remover_duplicatas_inteligente(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove duplicatas com estratégia inteligente."""
        contagem_inicial = len(df)
        
        # Remove duplicatas por username, mantendo o registro com mais informações
        if 'username' in df.columns:
            # Cria score baseado na quantidade de informações não vazias
            colunas_info = ['nome_completo', 'bio', 'n_seguidores', 'n_seguindo', 'n_publicacoes']
            colunas_existentes = [col for col in colunas_info if col in df.columns]
            
            if colunas_existentes:
                # Calcula score de completude para cada linha
                df['_score_completude'] = 0
                for col in colunas_existentes:
                    df['_score_completude'] += (~df[col].astype(str).str.strip().eq('')).astype(int)
                
                # Ordena por score (maior primeiro) e remove duplicatas
                df = df.sort_values('_score_completude', ascending=False)
                df = df.drop_duplicates(subset=['username'], keep='first')
                df = df.drop(columns=['_score_completude'])
            else:
                df = df.drop_duplicates(subset=['username'], keep='first')
        
        duplicatas_removidas = contagem_inicial - len(df)
        self.estatisticas['duplicatas_removidas'] = duplicatas_removidas
        
        return df
    
    def processar_colunas_numericas(self, df: pd.DataFrame) -> pd.DataFrame:
        """Processa colunas numéricas de forma vetorizada."""
        colunas_numericas = ['n_publicacoes', 'n_seguidores', 'n_seguindo']
        
        for col in colunas_numericas:
            if col in df.columns:
                df[col] = self.converter_para_numero_vetorizado(df[col])
        
        return df
    
    def padronizar_textos(self, df: pd.DataFrame) -> pd.DataFrame:
        """Padroniza textos de forma vetorizada."""
        # Padroniza nome completo
        if 'nome_completo' in df.columns:
            df['nome_completo'] = (
                df['nome_completo']
                .astype(str)
                .str.strip()
                .str.title()
            )
        
        # Limpa bio
        if 'bio' in df.columns:
            df['bio'] = df['bio'].astype(str).str.strip()
            df['bio'] = self.remover_emojis_vetorizado(df['bio'])
            df['bio'] = self.limpar_bio_contaminada_vetorizada(df['bio'])
        
        return df
    
    def remover_bios_duplicadas(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove perfis com bios duplicadas (mantendo bios vazias)."""
        if 'bio' not in df.columns:
            return df
        
        contagem_inicial = len(df)
        
        # Separa bios vazias e não vazias
        mask_bio_vazia = df['bio'].str.strip().eq('')
        df_bios_vazias = df[mask_bio_vazia].copy()
        df_bios_nao_vazias = df[~mask_bio_vazia].copy()
        
        # Remove duplicatas apenas de bios não vazias
        if not df_bios_nao_vazias.empty:
            df_bios_nao_vazias = df_bios_nao_vazias.drop_duplicates(subset=['bio'], keep='first')
        
        # Reconstitui o DataFrame
        df = pd.concat([df_bios_nao_vazias, df_bios_vazias], ignore_index=True)
        
        bios_duplicadas_removidas = contagem_inicial - len(df)
        self.estatisticas['bios_duplicadas_removidas'] = bios_duplicadas_removidas
        
        return df
    
    def reorganizar_colunas(self, df: pd.DataFrame) -> pd.DataFrame:
        """Reorganiza colunas na ordem ideal."""
        colunas_ideais = ["username", "nome_completo", "bio", "n_publicacoes", "n_seguidores", "n_seguindo"]
        colunas_presentes = [col for col in colunas_ideais if col in df.columns]
        outras_colunas = [col for col in df.columns if col not in colunas_presentes]
        
        return df[colunas_presentes + outras_colunas]
    
    def tratar_e_limpar_csv(self, df: pd.DataFrame) -> pd.DataFrame:
        """Pipeline principal de limpeza e tratamento de dados."""
        self.logger.info("Iniciando pipeline de limpeza e tratamento de dados...")
        
        # ETAPA 1: Tratamento de dados ausentes
        df = self.tratar_dados_ausentes(df)
        self.logger.info("   [1/9] Dados ausentes (NaN) preenchidos.")
        
        # ETAPA 2: Remoção inteligente de duplicatas
        df = self.remover_duplicatas_inteligente(df)
        duplicatas = self.estatisticas['duplicatas_removidas']
        if duplicatas > 0:
            self.logger.info(f"   [2/9] {duplicatas} perfis duplicados foram removidos.")
        else:
            self.logger.info("   [2/9] Nenhuma duplicata de perfil encontrada.")
        
        # ETAPA 3: Processamento de colunas numéricas
        df = self.processar_colunas_numericas(df)
        self.logger.info("   [3/9] Colunas numéricas limpas e convertidas.")
        
        # ETAPA 4: Validação de outliers
        df = self.validar_dados_numericos(df)
        self.logger.info("   [4/9] Validação de outliers concluída.")
        
        # ETAPA 5: Padronização de textos
        df = self.padronizar_textos(df)
        self.logger.info("   [5/9] Textos padronizados e emojis removidos.")
        
        # ETAPA 6: Limpeza específica da bio já está incluída na padronização
        self.logger.info("   [6/9] Ruídos (stats, nomes) removidos da coluna 'bio'.")
        
        # ETAPA 7: Validação de consistência
        df = self.validar_consistencia_dados(df)
        self.logger.info("   [7/9] Validação de consistência concluída.")
        
        # ETAPA 8: Remoção de bios duplicadas
        df = self.remover_bios_duplicadas(df)
        bios_dup = self.estatisticas['bios_duplicadas_removidas']
        if bios_dup > 0:
            self.logger.info(f"   [8/9] {bios_dup} perfis com bio duplicada foram removidos.")
        else:
            self.logger.info("   [8/9] Nenhuma bio duplicada encontrada.")
        
        # ETAPA 9: Reorganização final
        df = self.reorganizar_colunas(df)
        self.logger.info("   [9/9] Colunas reorganizadas.")
        
        self.logger.info("✅ Pipeline de limpeza concluído com sucesso!")
        return df
    
    def imprimir_relatorio_final(self, df_final: pd.DataFrame) -> None:
        """Imprime relatório final com estatísticas."""
        self.logger.info("=" * 60)
        self.logger.info("📊 RELATÓRIO FINAL DO TRATAMENTO")
        self.logger.info("=" * 60)
        self.logger.info(f"📈 Total de perfis únicos e limpos: {len(df_final)}")
        self.logger.info(f"🔄 Duplicatas removidas: {self.estatisticas['duplicatas_removidas']}")
        self.logger.info(f"⚠️  Outliers corrigidos: {self.estatisticas['outliers_corrigidos']}")
        self.logger.info(f"📝 Bios duplicadas removidas: {self.estatisticas['bios_duplicadas_removidas']}")
        
        if self.estatisticas['problemas_consistencia']:
            self.logger.info(f"🔧 Problemas corrigidos: {'; '.join(self.estatisticas['problemas_consistencia'])}")
        
        self.logger.info("=" * 60)


def normalizar_nomes_colunas(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza nomes de colunas para o padrão esperado."""
    mapeamento_colunas = {
        'username_curtiu': 'username',
        'nome_completo_curtiu': 'nome_completo'
    }
    
    df_normalizado = df.rename(columns=mapeamento_colunas)
    
    # Log das alterações
    for col_antiga, col_nova in mapeamento_colunas.items():
        if col_antiga in df.columns:
            logging.info(f"Coluna '{col_antiga}' renomeada para '{col_nova}'.")
    
    return df_normalizado


def validar_colunas_obrigatorias(df: pd.DataFrame) -> bool:
    """Valida se as colunas obrigatórias estão presentes."""
    if 'username' not in df.columns:
        logging.critical(
            f"❌ Nenhuma coluna de username encontrada! "
            f"Colunas disponíveis: {list(df.columns)}"
        )
        return False
    return True


def main():
    """Função principal do script."""
    logger = logging.getLogger(__name__)
    
    # Verifica se o arquivo existe
    if not ARQUIVO_ENTRADA.exists():
        logger.error(f"❌ O arquivo de entrada '{ARQUIVO_ENTRADA}' não foi encontrado!")
        return
    
    try:
        # Carrega os dados
        logger.info(f"Lendo o arquivo de dados: {ARQUIVO_ENTRADA}")
        df_original = pd.read_csv(ARQUIVO_ENTRADA)
        logger.info(f"Arquivo carregado com {len(df_original)} registros.")
        logger.info(f"Colunas encontradas: {list(df_original.columns)}")
        
        # Normaliza nomes das colunas
        df_normalizado = normalizar_nomes_colunas(df_original)
        
        # Valida colunas obrigatórias
        if not validar_colunas_obrigatorias(df_normalizado):
            return
        
        # Processa os dados
        tratador = TratadorDados()
        df_limpo = tratador.tratar_e_limpar_csv(df_normalizado.copy())
        
        # Garante que a pasta de saída existe
        ARQUIVO_SAIDA.parent.mkdir(parents=True, exist_ok=True)
        
        # Salva o arquivo
        df_limpo.to_csv(ARQUIVO_SAIDA, index=False, encoding='utf-8')
        
        # Relatório final
        tratador.imprimir_relatorio_final(df_limpo)
        logger.info(f"🎉 SUCESSO! Arquivo salvo em: {ARQUIVO_SAIDA}")
        
    except pd.errors.EmptyDataError:
        logger.error("❌ O arquivo está vazio ou corrompido!")
    except pd.errors.ParserError as e:
        logger.error(f"❌ Erro ao analisar o arquivo CSV: {e}")
    except MemoryError:
        logger.error("❌ Arquivo muito grande para a memória disponível!")
    except Exception as e:
        logger.critical(f"❌ Erro inesperado durante o processo: {e}")


if __name__ == "__main__":
    main()
