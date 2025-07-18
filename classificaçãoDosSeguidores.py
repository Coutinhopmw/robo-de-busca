import pandas as pd
import logging
import os
import re
from datetime import datetime

# --- CONFIGURAÇÕES GERAIS ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Nome do arquivo CSV de entrada (gerado pelo script de coleta de dados avançados)
ARQUIVO_ENTRADA = "leads_detalhados.csv" 

# Nome do arquivo CSV final que será gerado com TODAS as análises
ARQUIVO_SAIDA = "perfis_analise_completa.csv"

# ======================= CONFIGURAÇÕES PARA ANÁLISE =======================
# Você pode personalizar estas listas para refinar a precisão da análise

# Palavras-chave para buscar na bio
PALAVRAS_CHAVE_BIO_GERAL = [
    'agendamento', 'whatsapp', 'delivery', 'promoção', 'desconto',
    'online', 'link na bio', 'contato', 'orçamento', 'horário',
    'envio', 'pedidos', 'retirada', 'loja', 'frete grátis',
    'novidades', 'lançamento', 'clique', 'confira', 'direto',
    'site', 'portfolio', 'fale conosco', 'reserva', 'serviços',
    'parcerias', 'atendimento', 'comprar', 'visite', 'bio atualizada'
]
# Palavras-chave para classificar o tipo de perfil
PALAVRAS_CHAVE_EMPRESA = [
    'salão', 'beleza', 'estética', 'barbearia', 'loja', 'restaurante', 'delivery',
    'oficial', 'store', 'shop', 'boutique', 'studio', 'clínica', 'consultório',
    'agência', 'serviços', 'encomendas', 'pedidos', 'agendamento', 'orçamento',
    'atacado', 'varejo', 'imóveis', 'advocacia', 'contabilidade',
    'empresa', 'corporativo', 'negócios', 'ecommerce', 'marketplace',
    'indústria', 'fábrica', 'representações', 'franquia', 'distribuidora',
    'importadora', 'exportadora', 'assistência técnica', 'manutenção', 'oficina',
    'consultoria', 'academia', 'escola', 'educação', 'eventos', 'buffet'
]
PALAVRAS_CHAVE_PESSOA = [
    'blogueira', 'blogger', 'influencer', 'criador de conteúdo', 'atleta',
    'artista', 'pessoal', 'public figure', 'figura pública',
    'digital creator', 'modelo', 'creator', 'apresentador', 'ator', 'atriz',
    'músico', 'cantor', 'cantora', 'youtuber', 'tiktoker', 'streamer',
    'comunicador', 'escritor', 'fotógrafo', 'coach', 'mentor',
    'profissional liberal', 'autônomo', 'portfólio', 'vida real', 'diário',
    'minha vida', 'reflexões', 'bio pessoal', 'sobre mim'
]
# Listas para análise de localização
CAPITAIS_E_CIDADES_IMPORTANTES = [
    # Capitais e principais cidades do Brasil (continua a lista anterior…)
    'palmas', 'goiânia', 'brasilia', 'são paulo', 'rio de janeiro', 'belo horizonte',
    'salvador', 'fortaleza', 'recife', 'curitiba', 'porto alegre', 'manaus', 'belém',
    'gurupi', 'araguaína', 'porto nacional', 'paraíso do tocantins',
    'campinas', 'ribeirão preto', 'santos', 'são josé dos campos', 'são luís',
    'teresina', 'maceió', 'joão pessoa', 'natal', 'vitória', 'cuiabá', 'campo grande',
    'florianópolis', 'joinville', 'londrina', 'maringá', 'uberlândia', 'feira de santana',
    'serra', 'jundiaí', 'anapolis', 'itabuna', 'barueri', 'caruaru', 'ilhéus',
    'blumenau', 'niterói', 'duque de caxias', 'nova iguaçu', 'osasco', 'diadema',
    # Todos os municípios do Tocantins
    'abreuândia', 'aguiarnópolis', 'aliança do tocantins', 'almas', 'alvorada',
    'ananás', 'angico', 'aparecida do rio negro', 'aragominas', 'araguacema',
    'araguaçu', 'araguaína', 'araguanã', 'araguatins', 'arapoeima', 'arraias',
    'augustinópolis', 'aurora do tocantins', 'axixá do tocantins', 'babaçulândia',
    'bandeirantes do tocantins', 'barra do ouro', 'barrolândia', 'bernardo sayão',
    'bom jesus do tocantins', 'brasilândia do tocantins', 'brejinho de nazaré',
    'buriti do tocantins', 'cachoeirinha', 'campinas do tocantins',
    'campo lindos', 'cariri do tocantins', 'carmolândia', 'carrasco bonito',
    'caseara', 'centenário', 'chapada da arei a', 'chapada de natividade',
    'colinas do tocantins', 'colméia', 'combinado', 'conceição do tocantins',
    'couto magalhães', 'cristalândia', 'crixás do tocantins', 'darcinópolis',
    'dianópolis', 'divinópolis do tocantins', 'dois irmãos do tocantins',
    'dueré', 'esperantina', 'fatima', 'figueirópolis', 'filadélfia',
    'formoso do araguaia', 'fortaleza do tabocão', 'goianorte', 'goiatins',
    'guaraí', 'gurupi', 'ipueiras', 'itacajá', 'itaguatins', 'itapiratins',
    'itaporã do tocantins', 'jaú do tocantins', 'juarana', 'juarina', 'lagoa da confusão',
    'lagoa do tocantins', 'lajeado', 'lavandeira', 'lizarda', 'luzinópolis',
    'marianópolis', 'mateiros', 'miracema do tocantins', 'miranorte',
    'monte do carmo', 'monte santo do tocantins', 'muricilândia', 'natividade',
    'nazaré', 'nova olinda', 'nova rosalândia', 'novo acreditão', 'novo alegre',
    'novo jardim', 'oliveira de fatima', 'palmas', 'palmeirante', 'palmeiras do tocantins',
    'palmeiropolis', 'paraíso do tocantins', 'paranã', 'pau d’arco', 'peixe',
    'pequizeiro', 'pindorama do tocantins', 'piraquê', 'pium', 'ponte alta do bom jesus',
    'ponte alta do tocantins', 'porto alegre do tocantins', 'porto nacional',
    'praia norte', 'presidente kennedy', 'pugmil', 'recursolândia', 'riachinho',
    'rio da conceição', 'rio dos bois', 'rio sono', 'sam póio', 'sampaio',
    'sandolândia', 'santa fé do araguaia', 'santa maria do tocantins',
    'santa rita do tocantins', 'santa rosa do tocantins', 'silvanópolis',
    'sítio novo do tocantins', 'sucupira', 'taguatinga', 'taipas do tocantins',
    'talismã', 'tocantínia', 'tocantinópolis', 'tupirama', 'tupiratins',
    'wagner', 'wanderlândia', 'xambioá'
]
ESTADOS = {
    'AC': 'Acre', 'AL': 'Alagoas', 'AP': 'Amapá', 'AM': 'Amazonas', 'BA': 'Bahia', 'CE': 'Ceará',
    'DF': 'Distrito Federal', 'ES': 'Espírito Santo', 'GO': 'Goiás', 'MA': 'Maranhão', 'MT': 'Mato Grosso',
    'MS': 'Mato Grosso do Sul', 'MG': 'Minas Gerais', 'PA': 'Pará', 'PB': 'Paraíba', 'PR': 'Paraná',
    'PE': 'Pernambuco', 'PI': 'Piauí', 'RJ': 'Rio de Janeiro', 'RN': 'Rio Grande do Norte',
    'RS': 'Rio Grande do Sul', 'RO': 'Rondônia', 'RR': 'Roraima', 'SC': 'Santa Catarina',
    'SP': 'São Paulo', 'SE': 'Sergipe', 'TO': 'Tocantins'
}
CIDADES_POR_ESTADO = { 'palmas': 'TO', 'gurupi': 'TO', 'araguaína': 'TO', 'porto nacional': 'TO', 'paraíso do tocantins': 'TO', 'goiânia': 'GO', 'brasilia': 'DF' }

# Listas para análise demográfica
NOMES_MASCULINOS = [
    'josé', 'joão', 'antônio', 'francisco', 'carlos', 'paulo', 'pedro',
    'lucas', 'luiz', 'marcos', 'luís', 'gabriel', 'rafael', 'daniel',
    'marcelo', 'bruno', 'eduardo', 'felipe', 'andré', 'fernando',
    'rodrigo', 'gustavo', 'guilherme', 'ricardo', 'tiago', 'sérgio',
    'vinícius',
    'henrique', 'leonardo', 'alexandre', 'thiago', 'henri', 'jorge',
    'fernando', 'mateus', 'vincent', 'isaac', 'samuel', 'arthur',
    'heitor', 'nicolas', 'ramon', 'alex', 'luan', 'caio', 'igor',
    'rafael', 'davi', 'benjamin', 'enrique', 'isaque', 'gabriel',
    'rafinha', 'marcos vinícius', 'marcos paulo', 'michael'
]
NOMES_FEMININOS = [
    'maria', 'ana', 'francisca', 'antônia', 'adriana', 'juliana', 'márcia',
    'fernanda', 'patrícia', 'aline', 'sandra', 'camila', 'amanda', 'bruna',
    'jéssica', 'letícia', 'júlia', 'luciana', 'vanessa', 'mariana', 'gabriela',
    'vera', 'vitória', 'larissa', 'cláudia', 'beatriz',
    # Acréscimos:
    'rafaela', 'priscila', 'carla', 'daniela', 'aline', 'isabela',
    'thais', 'paula', 'renata', 'michele', 'juliana', 'natália',
    'karen', 'aline', 'aline', 'aline', 'aline', 
    'catarina', 'flávia', 'rosana', 'eliana', 'tatiane', 'mônica',
    'elisa', 'eymara', 'julia', 'heloísa', 'mara', 'diana', 'evelyn',
    'sabrina', 'marina', 'rosângela', 'roseli', 'silvana', 'elizabete'
]
INTERESSES_E_PROFISSOES = {
    "Saúde & Bem-estar": [
        'médica', 'médico', 'nutri', 'nutricionista', 'psicóloga', 'psicólogo',
        'dentista', 'fisio', 'fisioterapeuta', 'enfermeira', 'enfermeiro',
        'terapeuta', 'fonoaudióloga', 'fonoaudiólogo', 'bem-estar', 'saúde',
        'massoterapeuta', 'acupunturista', 'osteopata'
    ],
    "Direito": [
        'advogada', 'advogado', 'advocacia', 'direito', 'oab',
        'jurídico', 'defensora pública', 'promotor', 'escrivã'
    ],
    "Beleza & Estética": [
        'beleza', 'estética', 'maquiadora', 'makeup', 'cabelo', 'nail',
        'designer de sobrancelhas', 'micropigmentadora', 'esteticista',
        'manicure', 'pedicure', 'cosmetóloga', 'lash designer'
    ],
    "Fitness & Esportes": [
        'fitness', 'fit', 'musculação', 'crossfit', 'personal trainer',
        'educador físico', 'atleta', 'treinador', 'corredor', 'ciclista',
        'yoga', 'pilates', 'dançarina', 'dançarino', 'lutador'
    ],
    "Marketing & Digital": [
        'marketing', 'mkt', 'social media', 'conteúdo digital', 'influencer',
        'publicidade', 'copywriter', 'gestora de tráfego', 'freelancer',
        'consultora digital', 'criador de conteúdo', 'branding', 'produtor digital'
    ],
    "Moda": [
        'moda', 'fashion', 'look', 'estilo', 'consultora de imagem',
        'modelo', 'influencer de moda', 'stylist', 'personal stylist',
        'tendência', 'produção de moda'
    ],
    "Educação": [
        'professora', 'professor', 'educadora', 'pedagoga', 'licenciatura',
        'ensino', 'psicopedagoga', 'orientadora educacional', 'revisora',
        'alfabetização', 'tutora', 'mestre', 'doutoranda'
    ],
    "Tecnologia": [
        'programador', 'desenvolvedor', 'dev', 'analista de sistemas',
        'engenheiro de software', 'TI', 'dados', 'machine learning',
        'ux/ui', 'designer gráfico', 'frontend', 'backend', 'fullstack'
    ],
    "Negócios & Finanças": [
        'empreendedora', 'empreendedor', 'consultora', 'coach',
        'mentor', 'negócios', 'investimentos', 'trader',
        'economista', 'administradora', 'finanças pessoais'
    ],
    "Artes & Criatividade": [
        'artista', 'artesã', 'pintora', 'ilustradora', 'fotógrafa',
        'cinegrafista', 'produtora cultural', 'criativa', 'designer',
        'arquitetura', 'decoração', 'música', 'cantora', 'escritora'
    ]
}
PALAVRAS_CHAVE_ESTUDANTE = {
    "TERMOS_GENERICOS": [
        'estudante', 'aluno', 'aluna', 'acadêmico', 'acadêmica',
        'universitário', 'universitária', 'cursando', 'formando', 'formanda',
        'calouro', 'caloura', 'graduando', 'graduanda', 'pós-graduando',
        'mestrando', 'doutorando', 'residente'
    ],
    "INSTITUICOES": [
        'faculdade', 'universidade', 'escola', 'colégio', 'instituto',
        'uf', 'ue', 'puc', 'fgv', 'uft', 'unitins', 'ifto',
        'unesp', 'usp', 'ufrj', 'ufmg', 'ufba', 'unb', 'unicamp',
        'ufsc', 'ufpe', 'ufpr', 'ufes', 'ufpa', 'unifesp', 'ueg',
        'ufc', 'if', 'ifsp', 'ifrn', 'ifba', 'ifce', 'ifpb'
    ],
    "CURSOS": [
        'direito', 'medicina', 'engenharia', 'engenharia civil',
        'engenharia elétrica', 'engenharia mecânica', 'administração', 'adm',
        'jornalismo', 'publicidade', 'arquitetura', 'odonto', 'odontologia',
        'psicologia', 'enfermagem', 'biomedicina', 'nutrição', 'farmácia',
        'fisioterapia', 'ciências contábeis', 'contabilidade', 'educação física',
        'pedagogia', 'letras', 'história', 'geografia', 'design', 'computação',
        'sistemas de informação', 'ciência da computação', 'análise e desenvolvimento de sistemas'
    ],
    "PADROES_REGEX": [
        r'\dº\s?período', r'\d\s?semestre', r'turma\s?\d+', r'\dº\s?ano',
        r'classe\s?\d+', r'módulo\s?\d+', r'estágio\s?(supervisionado|obrigatório)?',
        r'grupo\s?\d+', r'monografia', r'tcc', r'banca\s?final'
    ]
}
# =======================================================================================
# --- FUNÇÕES DE ANÁLISE ---

def converter_para_numero(valor):
    if isinstance(valor, (int, float)): return int(valor)
    if not isinstance(valor, str): return 0
    valor = valor.lower().strip().replace(',', '.')
    if 'k' in valor: return int(float(valor.replace('k', '')) * 1000)
    if 'm' in valor: return int(float(valor.replace('m', '')) * 1000000)
    valor_numerico = re.sub(r'[^0-9]', '', valor)
    return int(valor_numerico) if valor_numerico else 0

def extrair_localizacao(row):
    texto_busca = f"{str(row.get('bio', ''))} {str(row.get('nome_completo', ''))} {str(row.get('endereco', ''))}".lower()
    cidade_encontrada, estado_encontrado = "", ""
    for sigla in ESTADOS:
        if re.search(r'\b' + sigla.lower() + r'\b', texto_busca):
            estado_encontrado = sigla
            break
    for cidade in CAPITAIS_E_CIDADES_IMPORTANTES:
        if cidade in texto_busca:
            cidade_encontrada = cidade.title()
            if not estado_encontrado and cidade in CIDADES_POR_ESTADO:
                estado_encontrado = CIDADES_POR_ESTADO[cidade]
            break
    return cidade_encontrada, estado_encontrado

def extrair_caracteristicas_demograficas(row):
    texto_busca = f"{str(row.get('bio', '')).lower()} {str(row.get('username', '')).lower()}"
    nome_completo = str(row.get('nome_completo', '')).lower()
    idade_aprox, genero_inferido = None, "Indefinido"
    try: # Inferência de Idade
        match_anos = re.search(r'\b(1[8-9]|[2-9]\d)\s?anos\b', texto_busca)
        if match_anos: idade_aprox = int(match_anos.group(1))
        else:
            match_ano4 = re.search(r'\b(19[5-9]\d|200[0-5])\b', texto_busca)
            if match_ano4: idade_aprox = datetime.now().year - int(match_ano4.group(1))
            else:
                match_ano2 = re.search(r'[\'|\/](\d{2})\b', texto_busca)
                if match_ano2:
                    ano = int(match_ano2.group(1))
                    ano_nascimento = 1900 + ano if ano > (datetime.now().year - 2000) else 2000 + ano
                    idade_aprox = datetime.now().year - ano_nascimento
    except: pass
    try: # Inferência de Gênero
        primeiro_nome = nome_completo.split(' ')[0]
        if primeiro_nome in NOMES_FEMININOS: genero_inferido = "Feminino"
        elif primeiro_nome in NOMES_MASCULINOS: genero_inferido = "Masculino"
    except: pass
    return idade_aprox, genero_inferido

def identificar_estudante(row):
    texto_busca = f"{str(row.get('bio', ''))} {str(row.get('categoria', ''))}".lower()
    eh_estudante, detalhe_estudo = "Não", ""
    if not texto_busca.strip(): return eh_estudante, detalhe_estudo
    for padrao in PALAVRAS_CHAVE_ESTUDANTE["PADROES_REGEX"]:
        match = re.search(padrao, texto_busca)
        if match: return "Sim", match.group(0)
    todas_palavras = PALAVRAS_CHAVE_ESTUDANTE["TERMOS_GENERICOS"] + PALAVRAS_CHAVE_ESTUDANTE["INSTITUICOES"] + PALAVRAS_CHAVE_ESTUDANTE["CURSOS"]
    palavras_encontradas = [palavra.title() for palavra in todas_palavras if re.search(r'\b' + palavra + r'\b', texto_busca)]
    if palavras_encontradas:
        eh_estudante = "Sim"
        detalhe_estudo = ", ".join(palavras_encontradas)
    return eh_estudante, detalhe_estudo

def executar_analise_completa(df):
    """Aplica todas as funções de análise e classificação ao DataFrame."""
    logging.info("Iniciando pipeline de análise completa...")

    # Garante que colunas essenciais existam e preenche valores nulos
    for col in ['n_seguidores', 'n_seguindo', 'email', 'telefone', 'link_externo', 'bio', 'categoria', 'nome_completo', 'username', 'endereco']:
        if col not in df.columns: df[col] = ''
    df.fillna({'bio': '', 'categoria': '', 'nome_completo': '', 'endereco': ''}, inplace=True)

    # --- ETAPA 1: Análise Básica ---
    logging.info("ETAPA 1/5: Realizando análise básica (influência, contato, etc.)...")
    df['n_seguidores_num'] = df['n_seguidores'].apply(converter_para_numero)
    df['n_seguindo_num'] = df['n_seguindo'].apply(converter_para_numero)
    df['nivel_influencia'] = df['n_seguidores_num'].apply(lambda x: 'Iniciante (< 1k)' if x < 1000 else 'Nano-influenciador (1k - 10k)' if x < 10000 else 'Micro-influenciador (10k - 100k)' if x < 100000 else 'Médio Porte (100k - 1M)' if x < 1000000 else 'Macro/Mega-influenciador (> 1M)')
    df['ratio_seguidores_seguindo'] = round(df['n_seguidores_num'] / df['n_seguindo_num'].apply(lambda x: max(1, x)), 2)
    df['potencial_contato'] = df.apply(lambda row: 'Sim' if pd.notna(row['email']) and row['email'] or pd.notna(row['telefone']) and row['telefone'] else 'Não', axis=1)
    df['possui_link_externo'] = df['link_externo'].apply(lambda x: 'Sim' if pd.notna(x) and x else 'Não')
    df['palavras_chave_bio'] = df['bio'].apply(lambda bio: ", ".join([p for p in PALAVRAS_CHAVE_BIO_GERAL if isinstance(bio, str) and p in bio.lower()]))

    # --- ETAPA 2: Classificação de Tipo de Perfil ---
    logging.info("ETAPA 2/5: Classificando tipo de perfil (Empresa vs. Pessoa)...")
    df['tipo_perfil'] = df.apply(lambda row: "Empresa / Comércio" if (sum(p in str(row.get('categoria','')).lower() for p in PALAVRAS_CHAVE_EMPRESA)*5 + sum(p in f"{str(row.get('bio',''))} {str(row.get('nome_completo',''))}".lower() for p in PALAVRAS_CHAVE_EMPRESA)*3 + (2 if row.get('potencial_contato') == 'Sim' else 0) + (1 if row.get('possui_link_externo') == 'Sim' else 0) - (2 if sum(p in str(row.get('categoria','')).lower() for p in PALAVRAS_CHAVE_PESSOA) else 0)) >= 4 else "Pessoa / Criador", axis=1)

    # --- ETAPA 3: Extração de Localização ---
    logging.info("ETAPA 3/5: Extraindo informações de localização (cidade/estado)...")
    df[['cidade', 'estado']] = df.apply(extrair_localizacao, axis=1, result_type='expand')

    # --- ETAPA 4: Análise Demográfica ---
    logging.info("ETAPA 4/5: Inferindo idade e gênero...")
    df[['idade_aprox', 'genero_inferido']] = df.apply(extrair_caracteristicas_demograficas, axis=1, result_type='expand')
    
    # --- ETAPA 5: Identificação de Estudantes ---
    logging.info("ETAPA 5/5: Identificando prováveis estudantes...")
    df[['eh_estudante', 'detalhe_estudo']] = df.apply(identificar_estudante, axis=1, result_type='expand')

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
        dataframe_analisado = executar_analise_completa(dataframe_original.copy())
        
        # Reorganiza as colunas para melhor visualização
        colunas_principais = ['username', 'nome_completo', 'tipo_perfil', 'cidade', 'estado', 'genero_inferido', 'idade_aprox', 'nivel_influencia', 'n_seguidores', 'potencial_contato', 'eh_estudante', 'detalhe_estudo']
        outras_colunas = [col for col in dataframe_analisado.columns if col not in colunas_principais]
        dataframe_final = dataframe_analisado[colunas_principais + outras_colunas]
        
        dataframe_final.to_csv(ARQUIVO_SAIDA, index=False, encoding='utf-8')
        
        logging.info("="*60)
        logging.info(f"🎉 SUCESSO! O arquivo com a análise COMPLETA foi salvo em:")
        logging.info(f"   👉 {ARQUIVO_SAIDA}")
        logging.info("="*60)

        logging.info("RESUMO DA ANÁLISE COMPLETA:")
        print("\n--- Classificação de Tipo de Perfil ---")
        print(dataframe_final['tipo_perfil'].value_counts())
        print("\n--- Resumo de Localizações (Estados) ---")
        print(dataframe_final['estado'].value_counts().head(5))
        print("\n--- Resumo de Gêneros Inferidos ---")
        print(dataframe_final['genero_inferido'].value_counts())
        print("\n--- Resumo da Identificação de Estudantes ---")
        print(dataframe_final['eh_estudante'].value_counts())

    except Exception as e:
        logging.critical(f"❌ Um erro inesperado ocorreu durante a análise: {e}")