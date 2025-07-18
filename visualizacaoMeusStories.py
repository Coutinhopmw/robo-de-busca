import time
import logging
import os
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

# --- CONFIGURAÇÕES ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

INSTAGRAM_USERNAME = "proescola.com.br"
INSTAGRAM_PASSWORD = "Pro35c0l@2025"

# ============================ AÇÃO NECESSÁRIA AQUI (EDITAR) ============================
# Defina por quantos minutos você quer que o robô assista aos stories.
# Recomendações: comece com valores curtos como 5 ou 10 minutos para simular um uso real.
TEMPO_MAXIMO_VISUALIZACAO_MINUTOS = 10
# =======================================================================================


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
        # Lida com múltiplos pop-ups que podem aparecer após o login
        for _ in range(2):
            try:
                WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, "//*[text()='Agora não' or text()='Not Now' or text()='Dispensar']"))).click()
                logging.info("Pop-up de notificação/salvamento fechado.")
            except: pass
    except Exception as e:
        logging.error(f"❌ Erro inesperado durante o login: {e}")
        return False
    return True

def visualizar_stories(driver, wait, duration_minutes):
    """Encontra a barra de stories, clica para iniciar e aguarda pelo tempo definido."""
    logging.info("👀 Iniciando processo de visualização de Stories...")
    
    try:
        # O seletor procura por um botão dentro do carrossel de stories
        # Este seletor é geralmente estável para o primeiro story não visto
        seletor_story_ring = (By.XPATH, "//div[@role='menu']//div[@role='button']")
        
        logging.info("🔍 Procurando por um Story para iniciar...")
        story_ring = wait.until(EC.element_to_be_clickable(seletor_story_ring))
        
        story_ring.click()
        logging.info("✅ Visualizador de Stories aberto. O Instagram irá reproduzir automaticamente.")
        
        # Converte os minutos para segundos
        tempo_de_espera_segundos = duration_minutes * 60
        logging.info(f"   ⏯️  Assistindo por {duration_minutes} minuto(s). O robô fechará automaticamente após esse período.")
        
        # Pausa e deixa o Instagram fazer o trabalho de passar os stories
        time.sleep(tempo_de_espera_segundos)
        
        logging.info("⏰ Tempo de visualização concluído.")

    except TimeoutException:
        logging.info("✅ Nenhum Story novo para visualizar no momento.")
    except Exception as e:
        logging.error(f"❌ Um erro ocorreu ao tentar visualizar os Stories: {e}")

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
            visualizar_stories(driver, wait, TEMPO_MAXIMO_VISUALIZACAO_MINUTOS)

    except Exception as final_e:
        logging.critical(f"❌ Um erro inesperado ocorreu no fluxo principal: {final_e}")
    finally:
        if driver:
            driver.quit()
            logging.info("Navegador fechado.")