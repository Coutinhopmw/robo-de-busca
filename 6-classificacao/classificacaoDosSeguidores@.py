import pandas as pd
import logging
import os
import re
from datetime import datetime

# --- CONFIGURAÇÕES GERAIS ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# Caminho absoluto do diretório do script
DIR_SCRIPT = os.path.dirname(os.path.abspath(__file__))

# Nome do arquivo CSV de entrada (gerado pelo script de tratamento de dados avançados)
ARQUIVO_ENTRADA = os.path.join(DIR_SCRIPT, "..", "5-dadosTratados", "dados_tratados_dados_avancados_seguidores_enriquecido_bjjtocantins.csv")

# ======================= CONFIGURAÇÕES PARA ANÁLISE E SEGMENTAÇÃO =======================
# 1. Defina as colunas que você quer usar para criar as pastas e segmentar os arquivos CSV.
COLUNAS_PARA_SEGMENTAR = [
    'tipo_perfil',
    'estado',
    'cidade',
    'eh_estudante',
    'curso_inferido',
    'area_profissional_inferida',
    'genero_inferido',
    'nivel_influencia',
    'profissao',
    'instituicao_ensino'
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
PALAVRAS_CHAVE_ESTUDANTE = {"TERMOS_GENERICOS": ["estudante", "aluno", "aluna", "acadêmico", "cursando", "formando"], "INSTITUICOES": ["faculdade", "universidade", "escola", "instituto", "uf", "ue", "puc", "uft", "unitins", "ifto"], "CURSOS": ["direito", "medicina", "engenharia", "administração", "adm", "odontologia", "psicologia", "arquitetura", "contabilidade", "jornalismo", "marketing", "ti", "computação", "enfermagem", "farmácia", "fisioterapia", "nutrição", "pedagogia", "veterinária"], "PADROES_REGEX": [r"\dº\s?período", r"\d\s?semestre", r"turma\s?\d+"]}
PALAVRAS_CHAVE_PROFISSAO = {"SAUDE": ["médico", "medica", "doutor", "doutora", "enfermeiro", "enfermeira", "fisioterapeuta", "nutricionista", "psicólogo", "psicóloga", "dentista", "farmacêutico", "farmacêutica", "veterinário", "veterinária"], "DIREITO": ["advogado", "advogada", "jurídico", "juiz", "juíza", "promotor", "promotora"], "ENGENHARIA": ["engenheiro", "engenheira", "arquiteto", "arquiteta"], "TI": ["desenvolvedor", "programador", "analista de sistemas", "especialista em ti", "cientista de dados"], "EDUCACAO": ["professor", "professora", "pedagogo", "pedagoga"], "NEGOCIOS": ["administrador", "administradora", "contador", "contadora", "empreendedor", "empresário", "empresária", "consultor", "consultora", "vendedor", "vendedora", "gerente"], "OUTROS": ["jornalista", "designer", "artista", "atleta", "chef", "cozinheiro", "cozinheira", "fotógrafo", "fotógrafa", "influenciador", "influenciadora"]}
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
            if re.search(r'\\b' + sigla.lower() + r'\\b', texto): estado = sigla; break
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
        if any(re.search(r'\\b' + p + r'\\b', texto) for p in PALAVRAS_CHAVE_ESTUDANTE["TERMOS_GENERICOS"]): return "Sim"
        if any(re.search(r'\\b' + p + r'\\b', texto) for p in PALAVRAS_CHAVE_ESTUDANTE["INSTITUICOES"]): return "Sim"
        if any(re.search(r'\\b' + p + r'\\b', texto) for p in PALAVRAS_CHAVE_ESTUDANTE["CURSOS"]): return "Sim"
        return "Não"
    df['eh_estudante'] = df.apply(identificar_estudante, axis=1)
    
    def identificar_curso_e_profissao(row):
        texto = f"{row.get('bio', '')} {row.get('categoria', '')}".lower()
        curso = 'Não identificado'
        profissao = 'Não identificado'

        # Identificar Curso
        for c in PALAVRAS_CHAVE_ESTUDANTE["CURSOS"]:
            if re.search(r'\b' + c + r'\b', texto):
                curso = c.title()
                break

        # Identificar Profissão
        for area, profissoes in PALAVRAS_CHAVE_PROFISSAO.items():
            for p in profissoes:
                if re.search(r'\b' + p + r'\b', texto):
                    profissao = p.title()
                    break
            if profissao != 'Não identificado':
                break
        
        return curso, profissao

    df[['curso_inferido', 'area_profissional_inferida']] = df.apply(identificar_curso_e_profissao, axis=1, result_type='expand')
    

    def inferir_genero(row):
        primeiro_nome = str(row.get('nome_completo', '')).lower().split(' ')[0]
        if primeiro_nome in NOMES_FEMININOS: return "Feminino"
        if primeiro_nome in NOMES_MASCULINOS: return "Masculino"
        return "Indefinido"
    df['genero_inferido'] = df.apply(inferir_genero, axis=1)

    # --- NOVO: Extração de profissão e instituição de ensino ---
    # Lista de profissões comuns (pode ser expandida conforme necessário)
    LISTA_PROFISSOES = [
        'advogado', 'advogada', 'médico', 'médica', 'engenheiro', 'engenheira', 'professor', 'professora',
        'arquiteto', 'arquiteta', 'designer', 'contador', 'contadora', 'nutricionista', 'psicólogo', 'psicóloga',
        'dentista', 'enfermeiro', 'enfermeira', 'fisioterapeuta', 'veterinário', 'veterinária', 'administrador',
        'administradora', 'empresário', 'empresária', 'coach', 'personal trainer', 'fotógrafo', 'fotógrafa',
        'artista', 'cantor', 'cantora', 'ator', 'atriz', 'jornalista', 'publicitário', 'publicitária', 'analista',
        'programador', 'programadora', 'desenvolvedor', 'desenvolvedora', 'cientista', 'pesquisador', 'pesquisadora',
        'consultor', 'consultora', 'gerente', 'diretor', 'diretora', 'esteticista', 'manicure', 'maquiadora',
        'barbeiro', 'cozinheiro', 'cozinheira', 'chefe', 'chef', 'motorista', 'vendedor', 'vendedora', 'corretor',
        'corretora', 'biomédico', 'biomédica', 'farmacêutico', 'farmacêutica', 'fisiologista', 'coach', 'influencer',
        'blogueiro', 'blogueira', 'youtuber', 'tiktoker', 'criador de conteúdo', 'criadora de conteúdo'
    ]
    # Lista de palavras-chave para instituições de ensino
    LISTA_INSTITUICOES = [
        'universidade', 'faculdade', 'instituto', 'escola', 'colégio', 'uf', 'ue', 'puc', 'uft', 'unitins', 'ifto',
        'unip', 'unopar', 'uninter', 'unicesumar', 'unifeso', 'unifor', 'unb', 'usp', 'unicamp', 'ufrj', 'ufmg', 'ufba',
        'ufpe', 'ufpr', 'ufsc', 'ufes', 'ufpa', 'ufc', 'ufal', 'ufma', 'ufpb', 'ufrn', 'ufrr', 'ufam', 'ufac', 'ufmt',
        'ufms', 'ufpi', 'ufro', 'ufop', 'ufla', 'ufv', 'ufsj', 'ufjf', 'ufabc', 'ufscar', 'ufpel', 'ufsm', 'ufrgs',
        'ufes', 'ufra', 'ufrb', 'ufersa', 'ufvjm', 'ufersa', 'ufca', 'ufape', 'ufersa', 'ufersa', 'if', 'ifsp', 'ifba',
        'ifce', 'ifmg', 'ifpb', 'ifrn', 'ifrs', 'ifsc', 'ifpr', 'ifro', 'ifam', 'ifac', 'ifmt', 'ifms', 'ifpa', 'ifal',
        'ifma', 'ifpi', 'ifto', 'ifap', 'ifrr', 'ifgoiano', 'ifg', 'ifnmg', 'ifes', 'ifes', 'ifb', 'ifc', 'iffar', 'ifrs',
        'ifsp', 'ifbaiano', 'ifba', 'ifce', 'ifmg', 'ifpb', 'ifrn', 'ifrs', 'ifsc', 'ifpr', 'ifro', 'ifam', 'ifac', 'ifmt',
        'ifms', 'ifpa', 'ifal', 'ifma', 'ifpi', 'ifto', 'ifap', 'ifrr', 'ifgoiano', 'ifg', 'ifnmg', 'ifes', 'ifes', 'ifb',
        'ifc', 'iffar', 'ifrs', 'ifsp', 'ifbaiano', 'unitins', 'uft', 'unirg', 'ulbra', 'católica', 'mackenzie', 'senai', 'senac'
    ]

    def extrair_profissao(texto):
        texto = texto.lower()
        for prof in LISTA_PROFISSOES:
            if re.search(r'\\b' + re.escape(prof) + r'\\b', texto):
                return prof.title()
        return ''

    def extrair_instituicao(texto):
        texto = texto.lower()
        for inst in LISTA_INSTITUICOES:
            if re.search(r'\\b' + re.escape(inst) + r'\\b', texto):
                return inst.upper()
        return ''

    # Extrai profissão e instituição de ensino da bio/categoria
    df['profissao'] = df.apply(lambda row: extrair_profissao(f"{row.get('bio', '')} {row.get('categoria', '')}"), axis=1)
    df['instituicao_ensino'] = df.apply(lambda row: extrair_instituicao(f"{row.get('bio', '')} {row.get('categoria', '')}"), axis=1)

    logging.info("✅ Análise concluída.")
    return df
# --- FLUXO PRINCIPAL ---
if __name__ == "__main__":
    # Ajusta o ARQUIVO_ENTRADA para o caminho correto do arquivo enviado pelo usuário
    ARQUIVO_ENTRADA = "/home/ubuntu/upload/dados_avancados_seguidores_enriquecido_acipparaisocopy.csv"

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
        def salvar_segmentos(df, dir_saida, colunas_para_segmentar):
            """
            Salva arquivos CSV segmentados por combinações únicas das colunas especificadas.
            """
            for _, grupo in df.groupby(colunas_para_segmentar):
                # Cria um nome de arquivo baseado nos valores das colunas de segmentação
                valores = [str(grupo.iloc[0][col]) if pd.notna(grupo.iloc[0][col]) and str(grupo.iloc[0][col]).strip() != '' else 'indefinido' for col in colunas_para_segmentar]
                nome_arquivo = "segmento_" + "_".join([re.sub(r'\W+', '', v.lower().replace(' ', '_')) for v in valores]) + ".csv"
                caminho_saida = os.path.join(dir_saida, nome_arquivo)
                grupo.to_csv(caminho_saida, index=False, encoding='utf-8')
                logging.info(f"Segmento salvo: {caminho_saida}")

        salvar_segmentos(df_analisado, DIR_SCRIPT, COLUNAS_PARA_SEGMENTAR)

    except Exception as e:
        logging.critical(f"❌ Um erro inesperado ocorreu durante a análise: {e}")


