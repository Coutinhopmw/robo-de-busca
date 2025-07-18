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

# --- CONFIGURAÇÕES ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

INSTAGRAM_USERNAME = "proescola.com.br"
INSTAGRAM_PASSWORD = "Pro35c0l@2025"

# ============================ AÇÃO NECESSÁRIA AQUI (EDITAR) ============================
# Coloque aqui o username de UM perfil específico que você sabe que tem bio,
# mas para o qual o script anterior não conseguiu extrair a informação.
PERFIL_ALVO_PARA_CAPTURA = "proescola.com.br"
# =======================================================================================

ARQUIVO_SAIDA_HTML = "debug_pagina_perfil.html"


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
            WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, "//button[text()='Agora não' or text()='Not Now']"))).click()
        except: pass
    except Exception as e:
        logging.error(f"❌ Erro inesperado durante o login: {e}")
        return False
    return True

def capturar_html_perfil(driver, wait, username):
    """Navega até um perfil e salva o HTML completo da página."""
    if "username_com_problema_na_bio" in username:
        logging.error("❌ Por favor, edite o script e insira um username real na variável 'PERFIL_ALVO_PARA_CAPTURA'.")
        return False
        
    logging.info("⚙️ MODO DE CAPTURA DE PÁGINA DE PERFIL ATIVADO ⚙️")
    url_perfil = f"https://www.instagram.com/{username}/"
    logging.info(f"Navegando para o perfil: {url_perfil}")
    driver.get(url_perfil)
    
    try:
        # Espera o cabeçalho do perfil carregar, que é o container principal das informações
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "header")))
        logging.info("Página do perfil carregada. Aguardando 3 segundos para estabilizar...")
        time.sleep(3)

        pagina_html = driver.page_source
        
        with open(ARQUIVO_SAIDA_HTML, "w", encoding="utf-8") as f:
            f.write(pagina_html)

        logging.info("="*60)
        logging.info("✅ SUCESSO! O arquivo de depuração do PERFIL foi salvo.")
        logging.info(f"   👉 Arquivo: {os.path.abspath(ARQUIVO_SAIDA_HTML)}")
        logging.info("   PRÓXIMO PASSO: Por favor, me envie este novo arquivo.")
        logging.info("="*60)
        return True

    except Exception as e:
        logging.critical(f"❌ Falha durante a captura do HTML do perfil: {e}")
        return False

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
            capturar_html_perfil(driver, wait, PERFIL_ALVO_PARA_CAPTURA)

    except Exception as final_e:
        logging.critical(f"❌ Um erro geral ocorreu: {final_e}")
    finally:
        if driver:
            logging.info("Pausa de 5 segundos antes de fechar.")
            time.sleep(5)
            driver.quit()
            logging.info("Navegador fechado.")