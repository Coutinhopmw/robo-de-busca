import pandas as pd
import time
import logging
import os
import random
import csv # Import movido para o topo do arquivo
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# --- CONFIGURAÇÕES ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

INSTAGRAM_USERNAME = "proescola.com.br"
INSTAGRAM_PASSWORD = "Pro35c0l@2025"

PALAVRAS_CHAVE = [
    "salão de beleza", "salão de estética", "salão de cabeleireiro", "salão feminino",
    "salão masculino", "barbearia", "nail designer", "espaço de beleza", "espaço estético",
    "centro de estética", "clínica de estética", "studio de beleza", "studio de sobrancelhas",
    "studio de maquiagem", "spa de beleza", "spa urbano", "salão de unhas",
    "ateliê de beleza", "espaço de autocuidado", "estúdio de beleza"
]

# Garante que o diretório de saída exista
dir_saida = "buscaClientesInstagram"
if not os.path.exists(dir_saida):
    os.makedirs(dir_saida)

ARQUIVO_SAIDA = os.path.join(dir_saida, "perfis_comerciais_encontrados.csv")


# --- FUNÇÕES ---

def perform_login(driver, wait, username, password):
    """Realiza o login na conta do Instagram."""
    logging.info("🔑 Realizando login...")
    driver.get("https://www.instagram.com/accounts/login/")
    try:
        wait.until(EC.presence_of_element_located((By.NAME, "username"))).send_keys(username)
        driver.find_element(By.NAME, "password").send_keys(password + Keys.RETURN)
        wait.until(EC.url_contains("instagram.com"))
        logging.info("✅ Login realizado com sucesso.")
        try:
            WebDriverWait(driver, 7).until(
                EC.element_to_be_clickable((By.XPATH, "//*[text()='Agora não' or text()='Not Now']"))
            ).click()
            logging.info("Pop-up 'Agora não' fechado.")
        except: pass
    except Exception as e:
        logging.error(f"❌ Erro inesperado durante o login: {e}")
        return False
    return True

def buscar_e_coletar_perfis(driver, wait, keywords):
    """Pede ajuda para o clique inicial e depois busca e coleta os perfis."""
    perfis_encontrados = set() # Usar um set para usernames garante que não haverá duplicatas

    # Lógica de resumo: lê o CSV existente para não adicionar duplicatas
    if os.path.exists(ARQUIVO_SAIDA):
        try:
            df_existente = pd.read_csv(ARQUIVO_SAIDA)
            perfis_encontrados.update(df_existente['username'].tolist())
            logging.info(f"Encontrados {len(perfis_encontrados)} perfis já salvos no CSV. Novos perfis serão adicionados.")
        except Exception as e:
            logging.warning(f"Não foi possível ler o arquivo CSV existente. Começando do zero. Erro: {e}")

    # Cria o arquivo CSV com cabeçalho se ele não existir
    if not os.path.exists(ARQUIVO_SAIDA):
        with open(ARQUIVO_SAIDA, mode='w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["username", "nome_completo", "subtitulo", "palavra_chave_origem"])

    input("\n" + "="*60 +
          "\n   AÇÃO NECESSÁRIA: Por favor, clique no ícone de 'Pesquisa' (a lupa) na\n" +
          "   janela do navegador que foi aberta.\n\n" +
          "   Após o painel de busca aparecer, volte aqui e pressione ENTER para continuar...\n" +
          "="*60 + "\n")
    logging.info("✅ Interação manual recebida. Assumindo o controle...")

    SELETOR_LINHA_RESULTADO = (By.XPATH, "//a[contains(@class, '_a6hd') and .//img]")
    KEYWORDS_INVALIDAS = ['liked_by', 'comments', 'terms', 'privacy', 'locations', 'lite', 'explore', 'direct', 'accounts', 'legal']

    for keyword in keywords:
        logging.info(f"\n🔎 Buscando pela palavra-chave: '{keyword}'")
        try:
            search_box = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@aria-label='Entrada da pesquisa']")))
            search_box.send_keys(Keys.CONTROL + "a")
            search_box.send_keys(Keys.DELETE)
            time.sleep(1)
            search_box.send_keys(keyword)
            
            logging.info("⏳ Aguardando resultados...")
            time.sleep(5)

            resultados = wait.until(EC.presence_of_all_elements_located(SELETOR_LINHA_RESULTADO))
            logging.info(f"   ✅ Encontrados {len(resultados)} resultados válidos para '{keyword}'.")

            for resultado in resultados:
                try:
                    href = resultado.get_attribute('href')
                    username = href.strip('/').split('/')[-1]

                    # --- Validação e Verificação de Duplicatas ---
                    if not username or ' ' in username or len(username) < 3: continue
                    if any(kw in username.lower() for kw in KEYWORDS_INVALIDAS): continue
                    if username in perfis_encontrados: continue
                    # -----------------------------------------------

                    spans = resultado.find_elements(By.TAG_NAME, 'span')
                    textos = [s.text.strip() for s in spans if s.text.strip()]
                    
                    nome_completo = textos[0] if textos else ""
                    subtitulo = textos[1] if len(textos) > 1 else ""
                    
                    # =================== LÓGICA DE SALVAMENTO CORRIGIDA ===================
                    # Agora salva se encontrar o username, mesmo que outras infos estejam vazias.
                    if username:
                        perfis_encontrados.add(username) # Adiciona ao set para evitar duplicatas na mesma sessão
                        logging.info(f"      -> Coletado: {username} ({nome_completo})")

                        # Salva imediatamente no CSV
                        with open(ARQUIVO_SAIDA, mode='a', encoding='utf-8', newline='') as f:
                            writer = csv.writer(f)
                            writer.writerow([username, nome_completo, subtitulo, keyword])
                    # ====================================================================

                except Exception as e_inner:
                    # Loga o erro ao processar uma linha específica, mas não para o script
                    logging.warning(f"   ⚠️ Erro ao processar um resultado: {e_inner}")
                    continue
            
            pausa = random.uniform(3, 7)
            logging.info(f"   ⏸️ Pausando por {pausa:.1f} segundos antes da próxima busca...")
            time.sleep(pausa)

        except Exception as e:
            logging.error(f"❌ Falha ao processar a palavra-chave '{keyword}'. Erro: {e}")
            continue
    
    return perfis_encontrados

# --- FLUXO PRINCIPAL ---
if __name__ == "__main__":
    driver = None
    try:
        options = Options()
        options.add_argument("--start-maximized")
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        wait = WebDriverWait(driver, 20)
        
        if perform_login(driver, wait, INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD):
            perfis = buscar_e_coletar_perfis(driver, wait, PALAVRAS_CHAVE)
            
            logging.info(f"\n✅ SUCESSO! A busca foi concluída. Total de perfis únicos no set: {len(perfis)}")
            logging.info(f"Os dados foram salvos em tempo real em '{ARQUIVO_SAIDA}'")

    except Exception as final_e:
        logging.critical(f"❌ Um erro inesperado ocorreu no fluxo principal: {final_e}")
    finally:
        if driver:
            driver.quit()
            logging.info("Navegador fechado.")