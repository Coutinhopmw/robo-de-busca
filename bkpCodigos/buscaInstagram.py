import pandas as pd
from serpapi import GoogleSearch
import instaloader
import requests
from bs4 import BeautifulSoup
import re

# CHAVE SerpAPI
SERPAPI_API_KEY = "a700251a876368c41fc5419e4c834251b0182bcbf928c75506bf5250de989ba0"

def buscar_instagram_no_google(nome):
    query = f'site:instagram.com "{nome}"'
    search = GoogleSearch({
        "q": query,
        "api_key": SERPAPI_API_KEY
    })
    results = search.get_dict()
    usernames = []

    for result in results.get("organic_results", []):
        url = result.get("link")
        match = re.search(r"instagram\.com/([a-zA-Z0-9_.]+)", url)
        if match:
            username = match.group(1).split('/')[0]
            if username not in usernames:
                usernames.append(username)

    return usernames

def extrair_telefone(texto):
    padrao = r'\(?\b\d{2}\)?\s?\d{4,5}[-\s]?\d{4}\b'
    telefones = re.findall(padrao, texto)
    return telefones[0] if telefones else ""

def formatar_telefone(telefone):
    telefone = re.sub(r'\D', '', telefone)
    if len(telefone) == 10:
        return f"+55{telefone[:2]}9{telefone[2:]}"
    elif len(telefone) == 11:
        return f"+55{telefone}"
    return ""

def buscar_telefone_em_link(link):
    try:
        response = requests.get(link, timeout=5)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            texto = soup.get_text()
            return extrair_telefone(texto)
    except Exception:
        return ""
    return ""

def buscar_dados_publicos_instagram(username):
    try:
        L = instaloader.Instaloader()
        profile = instaloader.Profile.from_username(L.context, username)

        telefone_bio = extrair_telefone(profile.biography)
        telefone_link = buscar_telefone_em_link(profile.external_url) if profile.external_url else ""
        telefone = telefone_bio or telefone_link
        telefone_formatado = formatar_telefone(telefone)

        return {
            "Instagram": profile.username,
            "Nome no Instagram": profile.full_name,
            "Biografia": profile.biography,
            "Link na bio": profile.external_url,
            "Telefone": telefone_formatado
        }

    except Exception as e:
        print(f"❌ Erro ao acessar @{username}: {e}")
        return None

# ------------ EXECUÇÃO ------------

# Nome do arquivo com seus dados
ARQUIVO_ENTRADA = "dados_funcionarios.csv"
ARQUIVO_SAIDA = "funcionarios_instagram.csv"

# Lê o CSV de entrada
df_funcionarios = pd.read_csv(ARQUIVO_ENTRADA)

# Lista com resultados
resultados = []

# Para cada funcionário...
for index, row in df_funcionarios.iterrows():
    nome_funcionario = row['funcionario']
    print(f"\n🔎 Buscando perfis para: {nome_funcionario}")
    usernames = buscar_instagram_no_google(nome_funcionario)

    for user in usernames:
        print(f"📥 Coletando dados de @{user}")
        dados = buscar_dados_publicos_instagram(user)
        if dados:
            resultados.append({
                "Funcionário": nome_funcionario,
                **dados
            })

# Salva os dados no novo CSV
df_saida = pd.DataFrame(resultados)
df_saida.to_csv(ARQUIVO_SAIDA, index=False, encoding='utf-8')

print(f"\n✅ Busca concluída. Resultados salvos em '{ARQUIVO_SAIDA}'")
