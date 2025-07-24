import requests

URL = "https://demo.templatemonster.com/pt-br/demo/157393.html?_gl=1*1e2kbfv*_ga*MTk4Nzk4NTQ1OC4xNzUzMjc1ODA2*_ga_FTPYEGT5LY*czE3NTMyNzU4MDUkbzEkZzEkdDE3NTMyNzU4NTMkajEyJGwwJGgw"
OUTPUT_FILE = "html/captura_pagina_demo.html"

def capturar_html(url, output_file):
    response = requests.get(url)
    response.raise_for_status()
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(response.text)
    print(f"HTML salvo em: {output_file}")

if __name__ == "__main__":
    capturar_html(URL, OUTPUT_FILE)
