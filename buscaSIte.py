import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

base_url = "https://books.toscrape.com/catalogue/page-{}.html"

livros = []

# Loop nas primeiras 5 páginas (mude esse valor se quiser mais)
for pagina in range(1, 6):
    print(f"Lendo página {pagina}...")
    url = base_url.format(pagina)
    response = requests.get(url)
    
    if response.status_code != 200:
        print(f"Erro ao acessar a página {pagina}")
        continue

    soup = BeautifulSoup(response.content, 'html.parser')
    itens = soup.find_all("article", class_="product_pod")

    for item in itens:
        titulo = item.h3.a['title']
        preco = item.find("p", class_="price_color").text.strip()
        estoque = item.find("p", class_="instock availability").text.strip()
        classificacao = item.p['class'][1]  # exemplo: One, Two, Three...

        livros.append({
            "Título": titulo,
            "Preço": preco,
            "Estoque": estoque,
            "Classificação": classificacao
        })

    time.sleep(1)  # evita sobrecarga do servidor

# Exporta para CSV
df = pd.DataFrame(livros)
df.to_csv("livros_scrape.csv", index=False, encoding='utf-8')

print("Scraping concluído. Arquivo 'livros_scrape.csv' salvo com sucesso!")
