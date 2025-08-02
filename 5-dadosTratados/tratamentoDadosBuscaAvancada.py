import pandas as pd
import logging
import os
import re

# --- CONFIGURAÇÕES ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Caminho absoluto da pasta de dados avançados
DIR_DADOS_AVANCADOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '4-dados_avancados_seguidores')

# Nome do arquivo CSV de entrada (ajustado para o nome correto da pasta)
ARQUIVO_ENTRADA = os.path.join(DIR_DADOS_AVANCADOS, "dados_avancados_seguidores_enriquecido_bjjtocantins.csv")

# Nome do arquivo de saída: dadosTratados + nome do csv lido (salva na mesma pasta do script)
NOME_ARQUIVO_ENTRADA = os.path.basename(ARQUIVO_ENTRADA)
ARQUIVO_SAIDA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dados_tratados_" + NOME_ARQUIVO_ENTRADA)

# --- FUNÇÕES AUXILIARES DE LIMPEZA ---

def converter_para_numero(valor):
    if pd.isna(valor): return 0
    if isinstance(valor, (int, float)): return int(valor)
    if not isinstance(valor, str): return 0
    
    valor = valor.lower().strip().replace('.', '').replace(',', '.')
    if 'k' in valor:
        return int(float(valor.replace('k', '')) * 1000)
    if 'm' in valor:
        return int(float(valor.replace('m', '')) * 1000000)
    
    valor_numerico = re.sub(r'\D', '', valor)
    return int(valor_numerico) if valor_numerico else 0

def remover_emojis(texto):
    if not isinstance(texto, str):
        return texto
    
    emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
        u"\U00002702-\U000027B0"
        u"\U000024C2-\U0001F251"
        u"\U0001FA70-\U0001FAFF"  # Symbols & Pictographs Extended-A (inclui 🫀)
        u"\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
        "]+", flags=re.UNICODE)
    texto_limpo = emoji_pattern.sub(r'', texto)
    return re.sub(r'\s+', ' ', texto_limpo).strip()

def validar_dados_numericos(df):
    logging.info("   [VALIDAÇÃO] Verificando outliers em dados numéricos...")
    
    # Define limites razoáveis para as métricas
    LIMITE_MAX_SEGUIDORES = 100000000  # 100 milhões
    LIMITE_MAX_SEGUINDO = 10000  # 10 mil
    LIMITE_MAX_PUBLICACOES = 50000  # 50 mil
    
    # Corrige outliers
    outliers_removidos = 0
    
    if 'n_seguidores' in df.columns:
        outliers = df['n_seguidores'] > LIMITE_MAX_SEGUIDORES
        df.loc[outliers, 'n_seguidores'] = LIMITE_MAX_SEGUIDORES
        outliers_removidos += outliers.sum()
    
    if 'n_seguindo' in df.columns:
        outliers = df['n_seguindo'] > LIMITE_MAX_SEGUINDO
        df.loc[outliers, 'n_seguindo'] = LIMITE_MAX_SEGUINDO
        outliers_removidos += outliers.sum()
    
    if 'n_publicacoes' in df.columns:
        outliers = df['n_publicacoes'] > LIMITE_MAX_PUBLICACOES
        df.loc[outliers, 'n_publicacoes'] = LIMITE_MAX_PUBLICACOES
        outliers_removidos += outliers.sum()
    

    if outliers_removidos > 0:
        logging.info(f"   [VALIDAÇÃO] {outliers_removidos} outliers corrigidos.")
    else:
        logging.info("   [VALIDAÇÃO] Nenhum outlier encontrado.")
    return df


def validar_consistencia_dados(df):
    logging.info("   [VALIDAÇÃO] Verificando consistência dos dados...")
    
    problemas = []
    
    # Verifica usernames vazios
    usernames_vazios = df['username'].str.strip().eq('').sum()
    if usernames_vazios > 0:
        problemas.append(f"{usernames_vazios} usernames vazios")
    
    # Verifica nomes muito longos (possível contaminação)
    if 'nome_completo' in df.columns:
        nomes_longos = df['nome_completo'].str.len() > 100
        if nomes_longos.sum() > 0:
            problemas.append(f"{nomes_longos.sum()} nomes muito longos (>100 chars)")
    
    # Verifica bios muito longas (possível contaminação)
    if 'bio' in df.columns:
        bios_longas = df['bio'].str.len() > 500
        if bios_longas.sum() > 0:
            problemas.append(f"{bios_longas.sum()} bios muito longas (>500 chars)")
    
    if problemas:
        logging.warning(f"   [VALIDAÇÃO] Problemas encontrados: {'; '.join(problemas)}")
    else:
        logging.info("   [VALIDAÇÃO] Dados consistentes.")
    
    return df

# --- FUNÇÃO PARA LIMPAR BIO CONTAMINADA ---
def limpar_bio_contaminada(row):
    """
    Remove possíveis ruídos, como estatísticas ou nomes, da coluna 'bio'.
    Exemplo de ruídos: números de seguidores, nomes de usuário, links, etc.
    """
    bio = row.get("bio", "")
    if not isinstance(bio, str):
        return bio

    # Remove padrões comuns de ruído
    # Remove links
    bio = re.sub(r'http\S+|www\.\S+', '', bio)
    # Remove menções de usernames
    bio = re.sub(r'@\w+', '', bio)
    # Remove números isolados (possíveis stats)
    bio = re.sub(r'\b\d{2,}\b', '', bio)
    # Remove excesso de espaços
    bio = re.sub(r'\s+', ' ', bio).strip()
    return bio

# --- PIPELINE PRINCIPAL DE LIMPEZA E TRATAMENTO ---

def tratar_e_limpar_csv(df):
    logging.info("Iniciando pipeline de limpeza e tratamento de dados...")
    
    # ETAPA 1: Tratamento de Dados Ausentes
    for col in ["username", "nome_completo", "bio"]:
        if col in df.columns:
            df[col] = df[col].fillna('')
    for col in ["n_publicacoes", "n_seguidores", "n_seguindo"]:
        if col in df.columns:
            df[col] = df[col].fillna('0')
    logging.info("   [1/9] Dados ausentes (NaN) preenchidos.")

    # ETAPA 2: Remoção de Duplicatas de Perfis
    contagem_antes = len(df)
    df.drop_duplicates(subset=["username"], keep='first', inplace=True)
    contagem_depois = len(df)
    if contagem_antes > contagem_depois:
        logging.info(f"   [2/9] {contagem_antes - contagem_depois} perfis duplicados foram removidos.")
    else:
        logging.info("   [2/9] Nenhuma duplicata de perfil encontrada.")

    # ETAPA 3: Limpeza e Conversão de Colunas Numéricas
    if 'n_publicacoes' in df.columns:
        df["n_publicacoes"] = df["n_publicacoes"].apply(converter_para_numero)
    if 'n_seguidores' in df.columns:
        df["n_seguidores"] = df["n_seguidores"].apply(converter_para_numero)
    if 'n_seguindo' in df.columns:
        df["n_seguindo"] = df["n_seguindo"].apply(converter_para_numero)
    logging.info("   [3/9] Colunas numéricas limpas e convertidas.")

    # ETAPA 4: Validação de Dados Numéricos (Outliers)
    df = validar_dados_numericos(df)
    logging.info("   [4/9] Validação de outliers concluída.")

    # ETAPA 5: Padronização de Textos e Remoção de Emojis
    if 'nome_completo' in df.columns:
        df["nome_completo"] = df["nome_completo"].astype(str).str.strip().str.title()
    if 'bio' in df.columns:
        df["bio"] = df["bio"].astype(str).str.strip().apply(remover_emojis)
    logging.info("   [5/9] Textos padronizados e emojis removidos.")

    # ETAPA 6: Limpeza Profunda da Bio (REMOÇÃO DE RUÍDOS)
    if 'bio' in df.columns:
        df["bio"] = df.apply(limpar_bio_contaminada, axis=1)
    logging.info("   [6/9] Ruídos (stats, nomes) removidos da coluna 'bio'.")

    # ETAPA 7: Validação de Consistência
    df = validar_consistencia_dados(df)
    logging.info("   [7/9] Validação de consistência concluída.")

    # ETAPA 8: Remoção de Bios Duplicadas
    if 'bio' in df.columns:
        bios_nao_vazias = df[df["bio"] != '']
        bios_vazias = df[df["bio"] == '']
        contagem_antes_bio = len(bios_nao_vazias)
        bios_nao_vazias.drop_duplicates(subset=["bio"], keep='first', inplace=True)
        contagem_depois_bio = len(bios_nao_vazias)
        if contagem_antes_bio > contagem_depois_bio:
            logging.info(f"   [8/9] {contagem_antes_bio - contagem_depois_bio} perfis com bio duplicada foram removidos.")
        else:
            logging.info("   [8/9] Nenhuma bio duplicada encontrada.")
        df = pd.concat([bios_nao_vazias, bios_vazias], ignore_index=True)
    else:
        logging.info("   [8/9] Coluna 'bio' não encontrada, pulando remoção de bios duplicadas.")

    # ETAPA 9: Reorganização final
    colunas_ideais = ["username", "nome_completo", "bio", "n_publicacoes", "n_seguidores", "n_seguindo"]
    colunas_presentes = [col for col in colunas_ideais if col in df.columns]
    outras_colunas = [col for col in df.columns if col not in colunas_presentes]
    df = df[colunas_presentes + outras_colunas]
    logging.info("   [9/9] Colunas reorganizadas.")

    logging.info("✅ Pipeline de limpeza concluído com sucesso!")
    return df

# --- FLUXO PRINCIPAL ---
if __name__ == "__main__":
    if not os.path.exists(ARQUIVO_ENTRADA):
        logging.error(f"❌ O arquivo de entrada \'{ARQUIVO_ENTRADA}\' não foi encontrado!")
        exit()
    try:
        logging.info(f"Lendo o arquivo de dados: {ARQUIVO_ENTRADA}")
        dataframe_original = pd.read_csv(ARQUIVO_ENTRADA)
        logging.info(f"Colunas encontradas no arquivo: {list(dataframe_original.columns)}")

        # Verifica se existe 'username' ou 'username_curtiu'
        if 'username' in dataframe_original.columns:
            pass  # já está correto
        elif 'username_curtiu' in dataframe_original.columns:
            dataframe_original = dataframe_original.rename(columns={'username_curtiu': 'username'})
            logging.info("Coluna 'username_curtiu' encontrada e renomeada para 'username'.")
        else:
            logging.critical(f"❌ Nenhuma coluna de username encontrada! Colunas disponíveis: {list(dataframe_original.columns)}")
            exit(1)

        # Renomeia 'nome_completo_curtiu' para 'nome_completo' se existir
        if 'nome_completo_curtiu' in dataframe_original.columns:
            dataframe_original = dataframe_original.rename(columns={'nome_completo_curtiu': 'nome_completo'})
            logging.info("Coluna 'nome_completo_curtiu' encontrada e renomeada para 'nome_completo'.")

        dataframe_limpo = tratar_e_limpar_csv(dataframe_original.copy())

        # Garante que a pasta de saída existe
        pasta_saida = os.path.dirname(ARQUIVO_SAIDA)
        if not os.path.exists(pasta_saida):
            os.makedirs(pasta_saida)
        dataframe_limpo.to_csv(ARQUIVO_SAIDA, index=False, encoding='utf-8')

        logging.info("="*60)
        logging.info(f"🎉 SUCESSO! O arquivo com os dados tratados foi salvo em:")
        logging.info(f"   👉 {ARQUIVO_SAIDA}")
        logging.info(f"   Total de perfis únicos e limpos: {len(dataframe_limpo)}")
        logging.info("="*60)
        logging.info(f"   Total de perfis únicos e limpos: {len(dataframe_limpo)}")
        logging.info("="*60)

    except Exception as e:
        logging.critical(f"❌ Um erro inesperado ocorreu durante o processo: {e}")

