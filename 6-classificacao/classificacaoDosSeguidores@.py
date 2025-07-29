import pandas as pd
import logging
import os
import re
from datetime import datetime

# --- CONFIGURAÇÕES GERAIS ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# Caminho absoluto do diretório do script
DIR_SCRIPT = os.path.dirname(os.path.abspath(__file__))

# Nome do arquivo CSV de entrada (gerado pelo script de coleta de dados avançados)
ARQUIVO_ENTRADA = os.path.join(DIR_SCRIPT, "..", "5-dadosTratados", "dados_avancados_curtidas_completo_sebraeto.csv")

# ======================= CONFIGURAÇÕES PARA ANÁLISE E SEGMENTAÇÃO =======================
# 1. Defina as colunas que você quer usar para criar as pastas e segmentar os arquivos CSV.
COLUNAS_PARA_SEGMENTAR = [
    'tipo_perfil',
    'estado',
    'cidade',
    'estudante',
    'genero_inferido',
    'nivel_influencia'
]

# 2. (Opcional) Personalize as listas de palavras-chave para refinar a precisão da análise.
# Mantive as listas expandidas que você criou, pois são excelentes.
PALAVRAS_CHAVE_EMPRESA = [
    'salão', 'beleza', 'estética', 'barbearia', 'loja', 'restaurante', 'delivery', 'oficial', 'store', 
    'shop', 'boutique', 'studio', 'clínica', 'consultório', 'agência', 'serviços', 'encomendas', 
    'pedidos', 'agendamento', 'orçamento', 'atacado', 'varejo', 'imóveis', 'advocacia', 'contabilidade',
    'empresa', 'corporativo', 'negócios', 'ecommerce', 'marketplace', 'consultoria', 'academia', 'escola'
]
PALAVRAS_CHAVE_PESSOA = [
    'blogueira', 'blogger', 'influencer', 'criador de conteúdo', 'atleta', 'artista', 'pessoal', 
    'public figure', 'figura pública', 'digital creator', 'modelo', 'creator', 'youtuber', 'tiktoker'
]
CAPITAIS_E_CIDADES_IMPORTANTES = ['palmas', 'goiânia', 'brasilia', 'são paulo', 'rio de janeiro', 'belo horizonte', 'salvador', 'fortaleza', 'recife', 'curitiba', 'porto alegre', 'manaus', 'belém', 'gurupi', 'araguaína', 'porto nacional', 'paraíso do tocantins']
ESTADOS = {'AC': 'Acre', 'AL': 'Alagoas', 'AP': 'Amapá', 'AM': 'Amazonas', 'BA': 'Bahia', 'CE': 'Ceará', 'DF': 'Distrito Federal', 'ES': 'Espírito Santo', 'GO': 'Goiás', 'MA': 'Maranhão', 'MT': 'Mato Grosso', 'MS': 'Mato Grosso do Sul', 'MG': 'Minas Gerais', 'PA': 'Pará', 'PB': 'Paraíba', 'PR': 'Paraná', 'PE': 'Pernambuco', 'PI': 'Piauí', 'RJ': 'Rio de Janeiro', 'RN': 'Rio Grande do Norte', 'RS': 'Rio Grande do Sul', 'RO': 'Rondônia', 'RR': 'Roraima', 'SC': 'Santa Catarina', 'SP': 'São Paulo', 'SE': 'Sergipe', 'TO': 'Tocantins'}
CIDADES_POR_ESTADO = { 'palmas': 'TO', 'gurupi': 'TO', 'araguaína': 'TO', 'porto nacional': 'TO', 'paraíso do tocantins': 'TO', 'goiânia': 'GO', 'brasilia': 'DF' }
NOMES_MASCULINOS = ['josé', 'joão', 'antônio', 'francisco', 'carlos', 'paulo', 'pedro', 'lucas', 'luiz', 'marcos', 'luís', 'gabriel', 'rafael', 'daniel', 'marcelo', 'bruno', 'eduardo', 'felipe', 'andré', 'fernando', 'rodrigo', 'gustavo', 'guilherme', 'ricardo', 'tiago', 'sérgio', 'vinícius']
NOMES_FEMININOS = ['maria', 'ana', 'francisca', 'antônia', 'adriana', 'juliana', 'márcia', 'fernanda', 'patrícia', 'aline', 'sandra', 'camila', 'amanda', 'bruna', 'jéssica', 'letícia', 'júlia', 'luciana', 'vanessa', 'mariana', 'gabriela', 'vera', 'vitória', 'larissa', 'cláudia', 'beatriz']
PALAVRAS_CHAVE_ESTUDANTE = {"TERMOS_GENERICOS": ['estudante', 'aluno', 'aluna', 'acadêmico', 'cursando', 'formando'], "INSTITUICOES": ['faculdade', 'universidade', 'escola', 'instituto', 'uf', 'ue', 'puc', 'uft', 'unitins', 'ifto'], "CURSOS": ['direito', 'medicina', 'engenharia', 'administração', 'adm'], "PADROES_REGEX": [r'\dº\s?período', r'\d\s?semestre', r'turma\s?\d+']}

# =======================================================================================


# --- FUNÇÕES ---

def converter_para_numero(valor):
    if pd.isna(valor): return 0
    if isinstance(valor, (int, float)): return int(valor)
    if not isinstance(valor, str): return 0
    valor = valor.lower().strip().replace(',', '.')
    if 'k' in valor: return int(float(valor.replace('k', '')) * 1000)
    if 'm' in valor: return int(float(valor.replace('m', '')) * 1000000)
    return int(re.sub(r'\D', '', valor)) if re.sub(r'\D', '', valor) else 0

def analisar_e_classificar(df):
    """Aplica o pipeline completo de análise e classificação ao DataFrame."""
    logging.info("Iniciando pipeline de análise e classificação...")
    
    # Sanitização básica
    df.drop_duplicates(subset=['username'], keep='first', inplace=True)
    for col in ['bio', 'categoria', 'nome_completo', 'endereco']:
        if col in df.columns: df[col] = df[col].fillna('')

    # Aplica análises de influência apenas se as colunas existirem
    if 'n_seguidores' in df.columns:
        df['n_seguidores_num'] = df['n_seguidores'].apply(converter_para_numero)
        df['nivel_influencia'] = df['n_seguidores_num'].apply(lambda x: 'Iniciante' if x < 1000 else 'Nano' if x < 10000 else 'Micro' if x < 100000 else 'Médio' if x < 1000000 else 'Macro/Mega')
    if 'n_seguindo' in df.columns:
        df['n_seguindo_num'] = df['n_seguindo'].apply(converter_para_numero)
    
    def extrair_local(row):
        texto = f"{row.get('bio', '')} {row.get('nome_completo', '')}".lower()
        cidade, estado = "", ""
        for sigla in ESTADOS:
            if re.search(r'\b' + sigla.lower() + r'\b', texto): estado = sigla; break
        for cid in CAPITAIS_E_CIDADES_IMPORTANTES:
            if cid in texto:
                cidade = cid.title()
                if not estado and cid in CIDADES_POR_ESTADO: estado = CIDADES_POR_ESTADO[cid]
                break
        return cidade, estado
    df[['cidade', 'estado']] = df.apply(extrair_local, axis=1, result_type='expand')

    def classificar_tipo(row):
        score = 0
        texto = f"{row.get('categoria', '')} {row.get('bio', '')} {row.get('nome_completo', '')}".lower()
        if any(p in texto for p in PALAVRAS_CHAVE_EMPRESA): score += 1
        if any(p in texto for p in PALAVRAS_CHAVE_PESSOA): score -= 1
        return "Empresa / Comércio" if score > 0 else "Pessoa / Criador"
    df['tipo_perfil'] = df.apply(classificar_tipo, axis=1)

    def identificar_estudante(row):
        texto = f"{row.get('bio', '')} {row.get('categoria', '')}".lower()
        if any(re.search(p, texto) for p in PALAVRAS_CHAVE_ESTUDANTE["PADROES_REGEX"]): return "Sim"
        if any(re.search(r'\b' + p + r'\b', texto) for p in PALAVRAS_CHAVE_ESTUDANTE["TERMOS_GENERICOS"]): return "Sim"
        if any(re.search(r'\b' + p + r'\b', texto) for p in PALAVRAS_CHAVE_ESTUDANTE["INSTITUICOES"]): return "Sim"
        if any(re.search(r'\b' + p + r'\b', texto) for p in PALAVRAS_CHAVE_ESTUDANTE["CURSOS"]): return "Sim"
        return "Não"
    df['eh_estudante'] = df.apply(identificar_estudante, axis=1)
    
    def inferir_genero(row):
        primeiro_nome = str(row.get('nome_completo', '')).lower().split(' ')[0]
        if primeiro_nome in NOMES_FEMININOS: return "Feminino"
        if primeiro_nome in NOMES_MASCULINOS: return "Masculino"
        return "Indefinido"
    df['genero_inferido'] = df.apply(inferir_genero, axis=1)

    logging.info("✅ Análise concluída.")
    return df

def salvar_segmentos(df, base_path, colunas_para_segmentar):
    """Salva o DataFrame em múltiplos arquivos CSV segmentados por colunas específicas."""
    logging.info("Iniciando salvamento dos segmentos...")
    for coluna in colunas_para_segmentar:
        if coluna not in df.columns:
            logging.warning(f"Coluna '{coluna}' não encontrada para segmentação. Pulando.")
            continue
        
        # Agrupa o dataframe pelos valores únicos da coluna
        grupos = df.groupby(coluna)
        
        for nome_grupo, df_grupo in grupos:
            if pd.isna(nome_grupo) or not nome_grupo:
                continue # Ignora grupos com nome vazio ou NaN
            
            # Limpa o nome do grupo para criar um nome de arquivo/pasta válido
            nome_limpo = re.sub(r'[^\w\s-]', '', str(nome_grupo)).strip().replace(' ', '_')
            
            # Cria a pasta para a categoria (ex: /Tipo de Perfil/)
            pasta_categoria = os.path.join(base_path, coluna.replace('_', ' ').title())
            os.makedirs(pasta_categoria, exist_ok=True)
            
            # Define o caminho final do arquivo CSV
            caminho_csv = os.path.join(pasta_categoria, f"{nome_limpo}.csv")
            
            logging.info(f"   - Salvando segmento: {caminho_csv} ({len(df_grupo)} registros)")
            df_grupo.to_csv(caminho_csv, index=False, encoding='utf-8')
    logging.info("✅ Salvamento dos segmentos concluído.")

# --- FLUXO PRINCIPAL ---
if __name__ == "__main__":
    if not os.path.exists(ARQUIVO_ENTRADA):
        logging.error(f"❌ O arquivo de entrada '{ARQUIVO_ENTRADA}' não foi encontrado!")
        exit()
    try:
        logging.info(f"Lendo o arquivo de dados: {ARQUIVO_ENTRADA}")
        df_original = pd.read_csv(ARQUIVO_ENTRADA)

        # Roda o pipeline completo de análise
        df_analisado = analisar_e_classificar(df_original.copy())


        # Salva o arquivo completo e unificado na mesma pasta do script
        arquivo_completo_saida = os.path.join(DIR_SCRIPT, "analise_completa.csv")
        df_analisado.to_csv(arquivo_completo_saida, index=False, encoding='utf-8')
        logging.info(f"🎉 SUCESSO! O arquivo com a análise COMPLETA foi salvo em: {arquivo_completo_saida}")

        # Salva os arquivos segmentados na mesma pasta do script
        salvar_segmentos(df_analisado, DIR_SCRIPT, COLUNAS_PARA_SEGMENTAR)

    except Exception as e:
        logging.critical(f"❌ Um erro inesperado ocorreu durante a análise: {e}")