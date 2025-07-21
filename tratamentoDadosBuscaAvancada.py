import pandas as pd
import logging
import os
import re

# --- CONFIGURAÇÕES ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# Nome do arquivo CSV de entrada (agora lendo da pasta 'dadosAvancados')
ARQUIVO_ENTRADA = os.path.join("dadosAvancados", "dados_avancados_seguidores_enriquecido_edianemarinho_.csv")

# Nome do arquivo de saída: dadosTratados + nome do csv lido
NOME_ARQUIVO_ENTRADA = os.path.basename(ARQUIVO_ENTRADA)
ARQUIVO_SAIDA = os.path.join("dadosTratados", NOME_ARQUIVO_ENTRADA)


# --- FUNÇÕES AUXILIARES DE LIMPEZA ---

def converter_para_numero(valor):
    """Converte valores como '1.234', '1,5k' ou '2m' para um número inteiro."""
    if pd.isna(valor): return 0
    if isinstance(valor, (int, float)): return int(valor)
    if not isinstance(valor, str): return 0
    
    valor = valor.lower().strip().replace(',', '.')
    if 'k' in valor:
        return int(float(valor.replace('k', '')) * 1000)
    if 'm' in valor:
        return int(float(valor.replace('m', '')) * 1000000)
    
    valor_numerico = re.sub(r'\D', '', valor)
    return int(valor_numerico) if valor_numerico else 0

def remover_emojis(texto):
    """Remove emojis e outros símbolos comuns de uma string."""
    if not isinstance(texto, str):
        return texto
    
    emoji_pattern = re.compile("["
                           u"\U0001F600-\U0001F64F"  # emoticons
                           u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                           u"\U0001F680-\U0001F6FF"  # transport & map symbols
                           u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                           u"\U00002702-\U000027B0"
                           u"\U000024C2-\U0001F251"
                           "]+", flags=re.UNICODE)
    texto_limpo = emoji_pattern.sub(r'', texto)
    return re.sub(r'\s+', ' ', texto_limpo).strip()

# ======================= NOVA FUNÇÃO PARA LIMPEZA DA BIO =======================
def limpar_bio_contaminada(row):
    """Remove dados de stats, username e nome completo da coluna bio."""
    bio = str(row.get('bio', ''))
    if not bio:
        return ""

    # Pega os outros dados da linha para usar como "ruído" a ser removido
    username = str(row.get('username', ''))
    nome_completo = str(row.get('nome_completo', ''))
    n_publicacoes = str(row.get('n_publicacoes', ''))
    n_seguidores = str(row.get('n_seguidores', ''))
    n_seguindo = str(row.get('n_seguindo', ''))

    # Lista de ruídos a serem removidos
    ruidos = [
        username, nome_completo,
        n_publicacoes, n_seguidores, n_seguindo,
        'publicações', 'seguidores', 'seguindo', 'Ver tradução'
    ]
    
    # Remove cada ruído da bio (ignorando maiúsculas/minúsculas)
    bio_limpa = bio
    for ruido in ruidos:
        if ruido: # Garante que o ruído não é uma string vazia
            bio_limpa = re.sub(re.escape(ruido), '', bio_limpa, flags=re.IGNORECASE)

    # Remove múltiplos espaços e espaços no início/fim
    bio_limpa = re.sub(r'\s+', ' ', bio_limpa).strip()
    
    return bio_limpa
# ==============================================================================


# --- PIPELINE PRINCIPAL DE LIMPEZA E TRATAMENTO ---

def tratar_e_limpar_csv(df):
    """Aplica um pipeline completo de limpeza e sanitização em um DataFrame."""
    logging.info("Iniciando pipeline de limpeza e tratamento de dados...")
    
    # ETAPA 1: Tratamento de Dados Ausentes
    for col in ['username', 'nome_completo', 'bio']:
        if col in df.columns: df[col] = df[col].fillna('')
    for col in ['n_publicacoes', 'n_seguidores', 'n_seguindo']:
        if col in df.columns: df[col] = df[col].fillna('0')
    logging.info("   [1/7] Dados ausentes (NaN) preenchidos.")

    # ETAPA 2: Remoção de Duplicatas de Perfis
    contagem_antes = len(df)
    df.drop_duplicates(subset=['username'], keep='first', inplace=True)
    contagem_depois = len(df)
    if contagem_antes > contagem_depois:
        logging.info(f"   [2/7] {contagem_antes - contagem_depois} perfis duplicados foram removidos.")
    else:
        logging.info("   [2/7] Nenhuma duplicata de perfil encontrada.")

    # ETAPA 3: Limpeza e Conversão de Colunas Numéricas
    df['n_publicacoes'] = df['n_publicacoes'].apply(converter_para_numero)
    df['n_seguidores'] = df['n_seguidores'].apply(converter_para_numero)
    df['n_seguindo'] = df['n_seguindo'].apply(converter_para_numero)
    logging.info("   [3/7] Colunas numéricas limpas e convertidas.")

    # ETAPA 4: Padronização de Textos e Remoção de Emojis
    df['nome_completo'] = df['nome_completo'].astype(str).str.strip().str.title()
    df['bio'] = df['bio'].astype(str).str.strip().apply(remover_emojis)
    logging.info("   [4/7] Textos padronizados e emojis removidos.")

    # ETAPA 5: Limpeza Profunda da Bio (REMOÇÃO DE RUÍDOS)
    df['bio'] = df.apply(limpar_bio_contaminada, axis=1)
    logging.info("   [5/7] Ruídos (stats, nomes) removidos da coluna 'bio'.")

    # ETAPA 6: Remoção de Bios Duplicadas
    bios_nao_vazias = df[df['bio'] != '']
    bios_vazias = df[df['bio'] == '']
    contagem_antes_bio = len(bios_nao_vazias)
    bios_nao_vazias.drop_duplicates(subset=['bio'], keep='first', inplace=True)
    contagem_depois_bio = len(bios_nao_vazias)
    if contagem_antes_bio > contagem_depois_bio:
        logging.info(f"   [6/7] {contagem_antes_bio - contagem_depois_bio} perfis com bio duplicada foram removidos.")
    else:
        logging.info("   [6/7] Nenhuma bio duplicada encontrada.")
    df = pd.concat([bios_nao_vazias, bios_vazias])

    # ETAPA 7: Reorganização final
    colunas_ideais = ['username', 'nome_completo', 'bio', 'n_publicacoes', 'n_seguidores', 'n_seguindo']
    colunas_presentes = [col for col in colunas_ideais if col in df.columns]
    outras_colunas = [col for col in df.columns if col not in colunas_presentes]
    df = df[colunas_presentes + outras_colunas]
    logging.info("   [7/7] Colunas reorganizadas.")

    logging.info("✅ Pipeline de limpeza concluído com sucesso!")
    return df

# --- FLUXO PRINCIPAL ---
if __name__ == "__main__":
    if not os.path.exists(ARQUIVO_ENTRADA):
        logging.error(f"❌ O arquivo de entrada '{ARQUIVO_ENTRADA}' não foi encontrado!")
        exit()
    try:
        logging.info(f"Lendo o arquivo de dados: {ARQUIVO_ENTRADA}")
        dataframe_original = pd.read_csv(ARQUIVO_ENTRADA)
        
        dataframe_limpo = tratar_e_limpar_csv(dataframe_original.copy())
        
        dataframe_limpo.to_csv(ARQUIVO_SAIDA, index=False, encoding='utf-8')
        
        logging.info("="*60)
        logging.info(f"🎉 SUCESSO! O arquivo com os dados tratados foi salvo em:")
        logging.info(f"   👉 {ARQUIVO_SAIDA}")
        logging.info(f"   Total de perfis únicos e limpos: {len(dataframe_limpo)}")
        logging.info("="*60)

    except Exception as e:
        logging.critical(f"❌ Um erro inesperado ocorreu durante o processo: {e}")