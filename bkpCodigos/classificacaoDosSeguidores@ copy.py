import pandas as pd
import logging
import os
import re
from datetime import datetime

# --- CONFIGURAÇÕES GERAIS ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Nome do arquivo CSV de entrada (gerado pelo script de coleta de dados avançados)
ARQUIVO_ENTRADA = "dados_avancados_seguidores_enriquecido_edianemarinho_.csv"

# Nome do arquivo CSV final que será gerado com TODAS as análises
ARQUIVO_SAIDA = "perfis_analise_completa.csv"

# ======================= CONFIGURAções PARA ANÁLISE (SUA VERSÃO EXPANDIDA) =======================
# (As suas listas de palavras-chave, cidades, nomes, etc., estão mantidas aqui)
PALAVRAS_CHAVE_BIO_GERAL = [
    'agendamento', 'whatsapp', 'delivery', 'promoção', 'desconto',
    'online', 'link na bio', 'contato', 'orçamento', 'horário'
]
PALAVRAS_CHAVE_EMPRESA = [
    'salão', 'beleza', 'estética', 'barbearia', 'loja', 'restaurante', 'delivery',
    'oficial', 'store', 'shop', 'boutique', 'studio', 'clínica', 'consultório',
    'agência', 'serviços', 'encomendas', 'pedidos', 'agendamento', 'orçamento',
    'atacado', 'varejo', 'imóveis', 'advocacia', 'contabilidade', 'empresa'
]
PALAVRAS_CHAVE_PESSOA = [
    'blogueira', 'blogger', 'influencer', 'criador de conteúdo', 'atleta',
    'artista', 'pessoal', 'public figure', 'figura pública', 'digital creator',
    'modelo', 'creator', 'vida real', 'sobre mim'
]
CAPITAIS_E_CIDADES_IMPORTANTES = [
    'palmas', 'goiânia', 'brasilia', 'são paulo', 'rio de janeiro', 'belo horizonte',
    'salvador', 'fortaleza', 'recife', 'curitiba', 'porto alegre', 'manaus', 'belém',
    'gurupi', 'araguaína', 'porto nacional', 'paraíso do tocantins'
]
ESTADOS = {'AC': 'Acre', 'AL': 'Alagoas', 'AP': 'Amapá', 'AM': 'Amazonas', 'BA': 'Bahia', 'CE': 'Ceará', 'DF': 'Distrito Federal', 'ES': 'Espírito Santo', 'GO': 'Goiás', 'MA': 'Maranhão', 'MT': 'Mato Grosso', 'MS': 'Mato Grosso do Sul', 'MG': 'Minas Gerais', 'PA': 'Pará', 'PB': 'Paraíba', 'PR': 'Paraná', 'PE': 'Pernambuco', 'PI': 'Piauí', 'RJ': 'Rio de Janeiro', 'RN': 'Rio Grande do Norte', 'RS': 'Rio Grande do Sul', 'RO': 'Rondônia', 'RR': 'Roraima', 'SC': 'Santa Catarina', 'SP': 'São Paulo', 'SE': 'Sergipe', 'TO': 'Tocantins'}
CIDADES_POR_ESTADO = { 'palmas': 'TO', 'gurupi': 'TO', 'araguaína': 'TO', 'porto nacional': 'TO', 'paraíso do tocantins': 'TO', 'goiânia': 'GO', 'brasilia': 'DF' }
NOMES_MASCULINOS = ['josé', 'joão', 'antônio', 'francisco', 'carlos', 'paulo', 'pedro', 'lucas', 'luiz', 'marcos', 'luís', 'gabriel', 'rafael', 'daniel', 'marcelo', 'bruno', 'eduardo', 'felipe', 'andré', 'fernando', 'rodrigo', 'gustavo', 'guilherme', 'ricardo', 'tiago', 'sérgio', 'vinícius']
NOMES_FEMININOS = ['maria', 'ana', 'francisca', 'antônia', 'adriana', 'juliana', 'márcia', 'fernanda', 'patrícia', 'aline', 'sandra', 'camila', 'amanda', 'bruna', 'jéssica', 'letícia', 'júlia', 'luciana', 'vanessa', 'mariana', 'gabriela', 'vera', 'vitória', 'larissa', 'cláudia', 'beatriz']
INTERESSES_E_PROFISSOES = {
    "Saúde & Bem-estar": ['médica', 'médico', 'nutri', 'nutricionista', 'psicóloga', 'psicólogo', 'dentista', 'fisio', 'fisioterapeuta', 'enfermeira', 'bem-estar', 'saúde'],
    "Direito": ['advogada', 'advogado', 'advocacia', 'direito', 'oab'],
    "Beleza & Estética": ['beleza', 'estética', 'maquiadora', 'makeup', 'cabelo', 'nail', 'designer de sobrancelhas'],
    "Fitness & Esportes": ['fitness', 'fit', 'musculação', 'crossfit', 'personal trainer', 'educador físico', 'atleta'],
    "Marketing & Digital": ['marketing', 'mkt', 'social media', 'conteúdo digital', 'influencer', 'publicidade'],
    "Moda": ['moda', 'fashion', 'look', 'estilo', 'consultora de imagem'],
    "Educação": ['professora', 'professor', 'educadora', 'pedagoga', 'licenciatura'],
    "Tecnologia": ['programador', 'desenvolvedor', 'dev', 'analista de sistemas', 'engenheiro de software', 'ti', 'dados'],
    "Negócios & Finanças": ['empreendedora', 'empreendedor', 'consultora', 'coach', 'mentor', 'negócios', 'investimentos'],
    "Artes & Criatividade": ['artista', 'artesã', 'pintora', 'ilustradora', 'fotógrafa', 'designer', 'arquitetura', 'música']
}
PALAVRAS_CHAVE_ESTUDANTE = {"TERMOS_GENERICOS": ['estudante', 'aluno', 'aluna', 'acadêmico', 'cursando', 'formando'], "INSTITUICOES": ['faculdade', 'universidade', 'escola', 'instituto', 'uf', 'ue', 'puc', 'uft', 'unitins', 'ifto'], "CURSOS": ['direito', 'medicina', 'engenharia', 'administração', 'adm'], "PADROES_REGEX": [r'\dº\s?período', r'\d\s?semestre', r'turma\s?\d+']}

# --- FUNÇÕES DE ANÁLISE ---

def limpar_e_padronizar_dataframe(df):
    logging.info("Iniciando pipeline de sanitização dos dados...")
    for col in ['username', 'nome_completo', 'bio', 'email', 'telefone']:
        if col not in df.columns: df[col] = ''
    df.fillna({'username': '', 'nome_completo': '', 'bio': '', 'email': '', 'telefone': ''}, inplace=True)
    contagem_antes = len(df)
    df.drop_duplicates(subset=['username'], keep='first', inplace=True)
    if len(df) < contagem_antes:
        logging.info(f"   - {contagem_antes - len(df)} perfis duplicados foram removidos.")
    df['nome_completo'] = df['nome_completo'].str.strip().str.title()
    emoji_pattern = re.compile("[" u"\U0001F600-\U0001F64F" u"\U0001F300-\U0001F5FF" "]+", flags=re.UNICODE)
    df['bio'] = df['bio'].astype(str).apply(lambda x: emoji_pattern.sub(r'', x).strip())
    logging.info("✅ Sanitização concluída!")
    return df

def converter_para_numero(valor):
    if pd.isna(valor): return 0
    if isinstance(valor, (int, float)): return int(valor)
    if not isinstance(valor, str): return 0
    valor = valor.lower().strip().replace(',', '.')
    if 'k' in valor: return int(float(valor.replace('k', '')) * 1000)
    if 'm' in valor: return int(float(valor.replace('m', '')) * 1000000)
    return int(re.sub(r'\D', '', valor)) if re.sub(r'\D', '', valor) else 0

def extrair_localizacao(row):
    texto_busca = f"{str(row.get('bio', ''))} {str(row.get('nome_completo', ''))}".lower()
    cidade, estado = "", ""
    for sigla in ESTADOS:
        if re.search(r'\b' + sigla.lower() + r'\b', texto_busca): estado = sigla; break
    for cid in CAPITAIS_E_CIDADES_IMPORTANTES:
        if cid in texto_busca:
            cidade = cid.title()
            if not estado and cid in CIDADES_POR_ESTADO: estado = CIDADES_POR_ESTADO[cid]
            break
    return cidade, estado

def extrair_caracteristicas_demograficas(row):
    texto_busca = f"{str(row.get('bio', ''))} {str(row.get('username', ''))}".lower()
    nome_completo = str(row.get('nome_completo', '')).lower()
    idade_aprox, genero_inferido = None, "Indefinido"
    try:
        match_anos = re.search(r'\b(1[8-9]|[2-9]\d)\s?anos\b', texto_busca)
        if match_anos: idade_aprox = int(match_anos.group(1))
        else:
            match_ano4 = re.search(r'\b(19[5-9]\d|200[0-5])\b', texto_busca)
            if match_ano4: idade_aprox = datetime.now().year - int(match_ano4.group(1))
    except: pass
    try:
        primeiro_nome = nome_completo.split(' ')[0]
        if primeiro_nome in NOMES_FEMININOS: genero_inferido = "Feminino"
        elif primeiro_nome in NOMES_MASCULINOS: genero_inferido = "Masculino"
    except: pass
    return idade_aprox, genero_inferido

def identificar_estudante(row):
    texto_busca = f"{str(row.get('bio', ''))} {str(row.get('categoria', ''))}".lower()
    if not texto_busca.strip(): return "Não", ""
    for padrao in PALAVRAS_CHAVE_ESTUDANTE["PADROES_REGEX"]:
        if re.search(padrao, texto_busca): return "Sim", re.search(padrao, texto_busca).group(0)
    palavras_chaves = PALAVRAS_CHAVE_ESTUDANTE["TERMOS_GENERICOS"] + PALAVRAS_CHAVE_ESTUDANTE["INSTITUICOES"] + PALAVRAS_CHAVE_ESTUDANTE["CURSOS"]
    encontradas = [p.title() for p in palavras_chaves if re.search(r'\b' + p + r'\b', texto_busca)]
    return ("Sim", ", ".join(encontradas)) if encontradas else ("Não", "")

def detectar_bot_ou_fake(row):
    motivos = []
    if row.get('n_publicacoes_num', 0) <= 3: motivos.append('Poucos posts')
    if row.get('n_seguindo_num', 0) > 2500 and (row.get('n_seguindo_num', 0) / max(1, row.get('n_seguidores_num', 1))) > 2: motivos.append('Segue muito mais do que é seguido')
    if not row.get('nome_completo') or row.get('nome_completo').lower() == row.get('username').lower(): motivos.append('Nome ausente ou igual ao username')
    if not row.get('bio'): motivos.append('Bio vazia')
    return 'Suspeito' if len(motivos) >= 2 else 'Normal', "; ".join(motivos)

# ======================= NOVA FUNÇÃO DE ANÁLISE =======================
def categorizar_profissoes_interesses(row):
    """Busca por palavras-chave de interesse/profissão na bio, nome e categoria do perfil."""
    texto_busca = f"{str(row.get('bio', ''))} {str(row.get('nome_completo', ''))} {str(row.get('categoria', ''))}".lower()
    categorias_encontradas = []
    if not texto_busca.strip():
        return ""
    for categoria, palavras_chave in INTERESSES_E_PROFISSOES.items():
        if any(re.search(r'\b' + re.escape(palavra) + r'\b', texto_busca) for palavra in palavras_chave):
            categorias_encontradas.append(categoria)
    return ", ".join(categorias_encontradas)
# =======================================================================

def executar_analise_completa(df):
    """Aplica todas as funções de análise e classificação ao DataFrame."""
    logging.info("Iniciando pipeline de análise completa...")
    
    df = limpar_e_padronizar_dataframe(df.copy())

    for col in ['n_publicacoes', 'n_seguidores', 'n_seguindo', 'link_externo', 'categoria', 'endereco']:
        if col not in df.columns: df[col] = ''
    df.fillna({'n_publicacoes': '0', 'n_seguidores': '0', 'n_seguindo': '0'}, inplace=True)
    
    # --- ANÁLISE BÁSICA ---
    df['n_seguidores_num'] = df['n_seguidores'].apply(converter_para_numero)
    df['n_seguindo_num'] = df['n_seguindo'].apply(converter_para_numero)
    df['nivel_influencia'] = df['n_seguidores_num'].apply(lambda x: 'Iniciante' if x < 1000 else 'Nano' if x < 10000 else 'Micro' if x < 100000 else 'Médio' if x < 1000000 else 'Macro/Mega')
    df['ratio_seguidores_seguindo'] = round(df['n_seguidores_num'] / df['n_seguindo_num'].apply(lambda x: max(1, x)), 2)
    df['potencial_contato'] = df.apply(lambda row: 'Sim' if row.get('email') or row.get('telefone') else 'Não', axis=1)
    df['possui_link_externo'] = df['link_externo'].apply(lambda x: 'Sim' if pd.notna(x) and x else 'Não')

    # --- CLASSIFICAÇÃO DE PERFIL ---
    df['tipo_perfil'] = df.apply(lambda row: "Empresa / Comércio" if (sum(p in str(row.get('categoria','')).lower() for p in PALAVRAS_CHAVE_EMPRESA)*5 + sum(p in f"{row.get('bio','')} {row.get('nome_completo','')}".lower() for p in PALAVRAS_CHAVE_EMPRESA)*3 + (2 if row.get('potencial_contato') == 'Sim' else 0) + (1 if row.get('possui_link_externo') == 'Sim' else 0) - (2 if sum(p in str(row.get('categoria','')).lower() for p in PALAVRAS_CHAVE_PESSOA) else 0)) >= 4 else "Pessoa / Criador", axis=1)

    # --- OUTRAS ANÁLISES ---
    df[['cidade', 'estado']] = df.apply(extrair_localizacao, axis=1, result_type='expand')
    df[['idade_aprox', 'genero_inferido']] = df.apply(extrair_caracteristicas_demograficas, axis=1, result_type='expand')
    df[['eh_estudante', 'detalhe_estudo']] = df.apply(identificar_estudante, axis=1, result_type='expand')
    
    # ======================= NOVA ETAPA DE ANÁLISE =======================
    logging.info("Categorizando profissões e interesses...")
    df['profissoes_interesses'] = df.apply(categorizar_profissoes_interesses, axis=1)
    # =====================================================================

    df[['perfil_suspeito', 'motivo_suspeita']] = df.apply(detectar_bot_ou_fake, axis=1, result_type='expand')
    
    df.drop(columns=['n_seguidores_num', 'n_seguindo_num'], inplace=True, errors='ignore')
    logging.info("✅ Pipeline de análise concluído!")
    return df

# --- FLUXO PRINCIPAL ---
if __name__ == "__main__":
    if not os.path.exists(ARQUIVO_ENTRADA):
        logging.error(f"❌ O arquivo de entrada '{ARQUIVO_ENTRADA}' não foi encontrado!")
        exit()
    try:
        logging.info(f"Lendo o arquivo de dados: {ARQUIVO_ENTRADA}")
        dataframe_original = pd.read_csv(ARQUIVO_ENTRADA)
        
        dataframe_analisado = executar_analise_completa(dataframe_original)

        # Filtra apenas perfis classificados como Empresa / Comércio, se desejado
        # dataframe_analisado = dataframe_analisado[dataframe_analisado['tipo_perfil'] == 'Empresa / Comércio']

        colunas_principais = ['username', 'nome_completo', 'tipo_perfil', 'profissoes_interesses', 'cidade', 'estado', 'genero_inferido', 'idade_aprox', 'nivel_influencia', 'n_seguidores', 'potencial_contato', 'eh_estudante', 'detalhe_estudo', 'perfil_suspeito']
        outras_colunas = [col for col in dataframe_analisado.columns if col not in colunas_principais]
        dataframe_final = dataframe_analisado[colunas_principais + outras_colunas]
        
        dataframe_final.to_csv(ARQUIVO_SAIDA, index=False, encoding='utf-8')
        
        logging.info("="*60)
        logging.info(f"🎉 SUCESSO! O arquivo com a análise COMPLETA foi salvo em: '{ARQUIVO_SAIDA}'")
        logging.info("="*60)

        logging.info("RESUMO DA ANÁLISE:")
        print("\n--- Classificação de Tipo de Perfil ---")
        print(dataframe_final['tipo_perfil'].value_counts())
        
        # Resumo de interesses
        interesses = dataframe_final['profissoes_interesses'].str.split(', ').explode().dropna()
        if not interesses.empty:
            print("\n--- Resumo de Profissões/Interesses ---")
            print(interesses.value_counts().head(10))

    except Exception as e:
        logging.critical(f"❌ Um erro inesperado ocorreu durante a análise: {e}")