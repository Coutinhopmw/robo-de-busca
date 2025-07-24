# --- SCRIPT ESPECIAL PARA CAPTURAR O HTML DA PÁGINA DE UM POST ---

import time
import logging
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- SUAS CONFIGURAÇÕES ---
INSTAGRAM_USERNAME = "antoniocassiorodrigueslima"
INSTAGRAM_PASSWORD = "Lc181340sl@?"

# ============================ AÇÃO NECESSÁRIA AQUI ============================
# Cole aqui a URL completa do mesmo post que você usou no teste anterior.
POST_ALVO_URL = "https://www.instagram.com/p/DMGIPZZu9OP/"
# ==============================================================================

def perform_login(driver, wait, username, password):
    logging.info("🔑 Realizando login...")
    driver.get("https://www.instagram.com/accounts/login/")
    try:
        wait.until(EC.presence_of_element_located((By.NAME, "username"))).send_keys(username)
        driver.find_element(By.NAME, "password").send_keys(password + Keys.RETURN)
        wait.until(EC.url_contains("instagram.com"))
        logging.info("✅ Login realizado com sucesso.")
        try:
            WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, "//button[text()='Agora não']"))).click()
        except: pass
    except Exception as e:
        logging.error(f"❌ Erro inesperado durante o login: {e}")
        return False
    return True

def capturar_html_pagina_post(driver, wait, post_url):
    if "COLE_A_URL" in post_url:
        logging.error("❌ Por favor, edite o script e insira a URL de um post na variável 'POST_ALVO_URL'.")
        return False
        
    logging.info("⚙️ MODO DE CAPTURA DE PÁGINA DE POST ATIVADO ⚙️")
    logging.info(f"Navegando para o post: {post_url}")
    driver.get(post_url)
    
    try:
        # Espera o conteúdo principal da página do post carregar
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "main")))
        time.sleep(3)

        pagina_html = driver.page_source
        file_path = os.path.join(os.getcwd(), "debug_post_pagina.html")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n")
            f.write(pagina_html)

        logging.info("="*60)
        logging.info("✅ SUCESSO! O arquivo de depuração da PÁGINA DO POST foi salvo.")
        logging.info(f"   👉 Arquivo: {file_path}")
        logging.info("   PRÓXIMO PASSO: Por favor, me envie este novo arquivo.")
        logging.info("="*60)
        return True

    except Exception as e:
        logging.error(f"❌ Falha durante a captura do HTML da página: {e}")
        return False

# --- FLUXO PRINCIPAL DE CAPTURA ---
if __name__ == "__main__":
    driver = None
    try:
        options = Options()
        options.add_argument("--start-maximized")
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        wait = WebDriverWait(driver, 20)

        if perform_login(driver, wait, INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD):
            capturar_html_pagina_post(driver, wait, POST_ALVO_URL)

    except Exception as final_e:
        logging.critical(f"❌ Um erro geral ocorreu: {final_e}")
    finally:
        if driver:
            logging.info("Pausa de 5 segundos antes de fechar.")
            time.sleep(5)
            driver.quit()
            logging.info("Navegador fechado.")