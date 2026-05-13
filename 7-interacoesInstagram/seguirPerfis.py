import pandas as pd
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

INSTAGRAM_USERNAME = "orkestragestao"
INSTAGRAM_PASSWORD = "Lc181340sl@*" 

# INSTAGRAM_USERNAME = "proescola.com.br"
# INSTAGRAM_PASSWORD = "Pro35c0l@2025"


# ============================ AÇÃO NECESSÁRIA AQUI (EDITAR) ============================
# 1. Nome do arquivo CSV que contém a coluna 'username'.
ARQUIVO_ENTRADA = "Empresa__Comércio.csv" # Exemplo

# 2. Defina o número MÁXIMO de perfis para seguir NESTA SESSÃO.
MAX_SEGUIR_SESSAO = 5000

# 3. Defina o intervalo de tempo em segundos para a pausa entre as ações de seguir.
PAUSA_MINIMA_SEGUNDOS = 60  # 1 minuto
PAUSA_MAXIMA_SEGUNDOS = 120  # 2 minutos
# =======================================================================================

# Arquivo para registrar os perfis já seguidos
LOG_DE_SEGUIR = "log_de_seguir.csv"


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
        
        # Espera de 2 minutos após o login para proteger a conta
        logging.info("⏱️  Aguardando 2 minutos após o login para proteger a conta...")
        time.sleep(120)  # 2 minutos
        logging.info("✅ Pausa de segurança concluída. Continuando com as ações...")
    except Exception as e:
        logging.error(f"❌ Erro inesperado durante o login: {e}")
        return False
    return True

def seguir_perfil(driver, wait, username):
    """Navega até um perfil e clica no botão 'Seguir' se disponível."""
    url_perfil = f"https://www.instagram.com/{username}/"
    driver.get(url_perfil)
    
    try:
        header = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "header")))
        
        # ======================= SELETOR CORRIGIDO =======================
        # O seletor foi ajustado para procurar por um botão que CONTENHA o texto "Seguir",
        # o que é mais robusto do que procurar por texto exato.
        botao_seguir = header.find_element(By.XPATH, ".//button[contains(., 'Seguir')]")
        # =================================================================
        
        # Checagem extra para garantir que não estamos clicando em "Deixar de seguir"
        if "Seguir" in botao_seguir.text:
            botao_seguir.click()
            logging.info(f"   ✅ Perfil '{username}' seguido com sucesso.")
            return True
        else:
            # Caso o botão contenha "Seguir" mas também outra palavra (ex: "Seguir também"),
            # esta lógica previne cliques indesejados.
            logging.info(f"   - Botão encontrado para '{username}' não era 'Seguir'. Texto: '{botao_seguir.text}'. Ignorando.")
            return False

    except NoSuchElementException:
        logging.info(f"   - Perfil '{username}' já seguido ou solicitação pendente. Ignorando.")
        return False
    except TimeoutException:
        logging.error(f"   ❌ Timeout ao carregar o perfil de '{username}'.")
        return False
    except Exception as e:
        logging.error(f"   ❌ Erro inesperado ao tentar seguir '{username}': {e}")
        return False

# --- FLUXO PRINCIPAL ---
if __name__ == "__main__":
    if not os.path.exists(ARQUIVO_ENTRADA):
        logging.error(f"O arquivo de entrada '{ARQUIVO_ENTRADA}' não foi encontrado!")
        exit()

    df_entrada = pd.read_csv(ARQUIVO_ENTRADA)
    if 'username' not in df_entrada.columns:
        logging.error("O arquivo de entrada deve conter uma coluna chamada 'username'.")
        exit()
        
    usernames_para_seguir = df_entrada['username'].dropna().tolist()
    
    if os.path.exists(LOG_DE_SEGUIR):
        df_log = pd.read_csv(LOG_DE_SEGUIR)
        seguidos_anteriormente = df_log['username'].tolist()
        usernames_para_seguir = [u for u in usernames_para_seguir if u not in seguidos_anteriormente]
        logging.info(f"Encontrado log de ações. {len(seguidos_anteriormente)} perfis já foram seguidos. Restam {len(usernames_para_seguir)} para processar.")
    else:
        pd.DataFrame(columns=['username', 'timestamp']).to_csv(LOG_DE_SEGUIR, index=False)
        logging.info(f"Arquivo de log '{LOG_DE_SEGUIR}' criado.")

    if not usernames_para_seguir:
        logging.info("Nenhum novo perfil para seguir. Encerrando.")
        exit()
    
    usernames_para_seguir = usernames_para_seguir[:MAX_SEGUIR_SESSAO]
    logging.info(f"Esta sessão irá tentar seguir no máximo {len(usernames_para_seguir)} perfis.")

    driver = None
    try:
        options = Options()
        options.add_argument("--start-maximized")
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        wait = WebDriverWait(driver, 15)
        
        if not perform_login(driver, wait, INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD):
            exit()
        
        seguidos_nesta_sessao = 0
        for i, username in enumerate(usernames_para_seguir):
            logging.info(f"\n➡️  Processando {i+1}/{len(usernames_para_seguir)}: {username}")
            
            if seguir_perfil(driver, wait, username):
                log_entry = pd.DataFrame([{'username': username, 'timestamp': pd.Timestamp.now()}])
                log_entry.to_csv(LOG_DE_SEGUIR, mode='a', header=False, index=False)
                seguidos_nesta_sessao += 1
                
                pausa = random.uniform(PAUSA_MINIMA_SEGUNDOS, PAUSA_MAXIMA_SEGUNDOS)
                logging.info(f"   ⏸️ Pausando por {pausa:.1f} segundos para proteger a conta...")
                time.sleep(pausa)
            else:
                time.sleep(random.uniform(3, 7))

        logging.info(f"\n🎉 Processo concluído! {seguidos_nesta_sessao} novo(s) perfil(s) foram seguidos nesta sessão.")

    except Exception as final_e:
        logging.critical(f"❌ Um erro fatal ocorreu no fluxo principal: {final_e}")
    finally:
        if driver:
            driver.quit()
            logging.info("Navegador fechado.")