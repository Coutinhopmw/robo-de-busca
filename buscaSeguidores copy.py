from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import time
import logging

# Configuração de logging para melhor depuração
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# CONFIGURAÇÕES
INSTAGRAM_USERNAME = "antoniocassiorodrigueslima"
INSTAGRAM_PASSWORD = "Lc181340sl@?"
PERFIL_ALVO = "edianemarinho_"
LIMITE_SEGUIDORES = float('inf') 
ARQUIVO_SAIDA_SEGUIDORES = f"seguidores_{PERFIL_ALVO}.csv"

# INICIALIZA O NAVEGADOR
options = Options()
options.add_argument("--start-maximized")
options.add_experimental_option('excludeSwitches', ['enable-logging'])
try:
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 30)
    logging.info("Navegador Chrome inicializado com sucesso.")
except Exception as e:
    logging.error(f"❌ Erro ao inicializar o navegador: {e}")
    exit()

# FUNÇÃO DE LOGIN
def perform_login(driver, wait, username, password):
    logging.info("🔑 Realizando login...")
    driver.get("https://www.instagram.com/accounts/login/")
    try:
        wait.until(EC.presence_of_element_located((By.NAME, "username")))
        username_input = driver.find_element(By.NAME, "username")
        password_input = driver.find_element(By.NAME, "password")
        username_input.send_keys(username)
        password_input.send_keys(password)
        password_input.send_keys(Keys.RETURN)
        logging.info("Credenciais enviadas.")
        wait.until(EC.url_contains("instagram.com"))
        logging.info("✅ Login realizado com sucesso.")
    except Exception as e:
        logging.error(f"❌ Erro inesperado durante o login: {e}")
        with open("login_debug.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        return False

    try:
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.NAME, "security_code")))
        logging.warning("🔐 Instagram solicitou verificação de dois fatores.")
        input("👉 Digite o código no navegador e pressione ENTER aqui quando tiver confirmado.")
        wait.until(EC.url_contains("instagram.com"))
        logging.info("Verificação de segurança concluída manualmente.")
    except TimeoutException:
        logging.info("✅ Login realizado sem verificação adicional.")
    return True

# FUNÇÃO PARA GARANTIR O ACESSO AO PERFIL
def garantir_perfil_alvo(driver, wait, perfil_alvo):
    url_perfil = f"https://www.instagram.com/{perfil_alvo}/"
    logging.info(f"Navegando para o perfil {perfil_alvo}...")
    driver.get(url_perfil)
    time.sleep(3)
    try:
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "header")))
        if perfil_alvo in driver.current_url:
            logging.info(f"✅ Perfil {perfil_alvo} acessado com sucesso.")
            return True
    except Exception as e:
        logging.warning(f"Erro ao verificar o perfil {perfil_alvo}: {e}")
    logging.error(f"❌ Não foi possível acessar o perfil {perfil_alvo}.")
    return False


# === FUNÇÃO: COLETAR SEGUIDORES (VERSÃO FINAL ROBUSTA) ===
def coletar_seguidores(driver, wait, perfil_alvo, limite_seguidores):
    logging.info("📥 Coletando seguidores em tempo real...")
    seguidores = {}
    scrolls_sem_novos = 0
    scroll_limit = 30 

    try:
        logging.info("🔍 Procurando botão de 'seguidores'...")
        seguidores_btn = wait.until(EC.element_to_be_clickable(
            (By.XPATH, f"//a[contains(@href, '/{perfil_alvo}/followers/')]")))
        seguidores_btn.click()
        logging.info("✅ Botão de seguidores clicado.")
    except Exception as e:
        logging.error(f"❌ Erro ao clicar no botão de seguidores: {e}")
        return {}

    # Espera o modal aparecer e pausa para o conteúdo carregar
    try:
        logging.info("⏳ Aguardando carregamento da janela de seguidores...")
        wait.until(EC.presence_of_element_located((By.XPATH, "//div[@role='dialog']")))
        logging.info("⏸️ Pausando por 2 segundos para permitir a renderização da lista...")
        time.sleep(2)
        logging.info("✅ Janela de seguidores carregada e renderizada.")
    except Exception as e:
        logging.error(f"❌ Erro ao carregar a janela de seguidores: {e}")
        return {}

    scroll_container = None
    by_method, selector_value = None, None

    possible_containers = [
        (By.XPATH, ".//div[contains(@class, '_aano')]"),
        (By.XPATH, ".//div[@role='dialog']/div/div/div[2]"),
        (By.CSS_SELECTOR, 'div.x6nl9eh.x1a5l9x9.x7vuprf.x1mg3h75.x1lliihq.x1iyjqo2.xs83m0k.xz65tgg.x1rife3k.x1n2onr6'),
        (By.XPATH, ".//div[@tabindex='0' or @tabindex='-1']")
    ]
    
    # ==================== CORREÇÃO CRÍTICA ====================
    # Obtém uma referência "fresca" do diálogo ANTES de iterar
    try:
        dialog = driver.find_element(By.XPATH, "//div[@role='dialog']")
    except NoSuchElementException:
        logging.error("❌ O modal de diálogo desapareceu antes que pudéssemos interagir.")
        return {}
    # ==========================================================

    for by, selector in possible_containers:
        try:
            # Busca o container DENTRO da referência fresca do diálogo
            scroll_container = dialog.find_element(by, selector)
            by_method, selector_value = by, selector
            logging.info(f"✅ Container rolável de seguidores encontrado com o seletor: {selector}")
            break 
        except NoSuchElementException:
            logging.info(f"⚠️ Não encontrou container com o seletor: {selector}")
            continue

    if not scroll_container:
        logging.error("❌ Não foi possível encontrar o container rolável com nenhum dos seletores.")
        try:
            modal_html = dialog.get_attribute('outerHTML')
            with open("debug_modal_seguidores.html", "w", encoding="utf-8") as f:
                f.write(modal_html)
            logging.info("ℹ️ O HTML do modal foi salvo em 'debug_modal_seguidores.html' para análise.")
        except Exception as e:
            logging.error(f"Falha ao tentar salvar o HTML de depuração: {e}")
        return {}

    # Loop de coleta
    while len(seguidores) < limite_seguidores and scrolls_sem_novos < scroll_limit:
        try:
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scroll_container)
            time.sleep(1.5) 
            novos = 0
            links_depois = scroll_container.find_elements(By.XPATH, ".//a[contains(@href,'.com/') and .//span]")
            
            for link in links_depois:
                try:
                    href = link.get_attribute("href")
                    if href and href.startswith("https://www.instagram.com/"):
                        username = href.strip('/').split('/')[-1]
                        if username and username not in seguidores and username != perfil_alvo:
                            seguidores[username] = ""
                            novos += 1
                            if len(seguidores) % 20 == 0: # Log a cada 20 seguidores
                                logging.info(f"Coletados {len(seguidores)} seguidores...")
                except StaleElementReferenceException:
                    continue
            
            if novos == 0:
                scrolls_sem_novos += 1
                logging.info(f"↕️ Nenhum novo usuário. Tentativa de scroll {scrolls_sem_novos}/{scroll_limit}")
            else:
                logging.info(f"Capturados {novos} novos usuários nesta rolagem. Total: {len(seguidores)}")
                scrolls_sem_novos = 0

            if len(seguidores) >= limite_seguidores:
                logging.info(f"✅ Limite de {limite_seguidores} seguidores atingido.")
                break
        except Exception as e:
            logging.error(f"⚠️ Erro inesperado durante a coleta de seguidores: {e}")
            break
    
    # Fecha o modal
    try:
        driver.find_element(By.XPATH, "//div[@role='dialog']//button[contains(@class, 'x1i10hfl')]").click()
    except Exception:
        driver.refresh() # Se não conseguir fechar, atualiza a página
    
    return seguidores

# ==============================================================================
# FLUXO PRINCIPAL DO SCRIPT
# ==============================================================================
if __name__ == "__main__":
    try:
        if perform_login(driver, wait, INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD):
            if garantir_perfil_alvo(driver, wait, PERFIL_ALVO):
                todos_seguidores = coletar_seguidores(driver, wait, PERFIL_ALVO, LIMITE_SEGUIDORES)
                if todos_seguidores:
                    df_seguidores = pd.DataFrame(list(todos_seguidores.keys()), columns=["username"])
                    df_seguidores.to_csv(ARQUIVO_SAIDA_SEGUIDORES, index=False, encoding='utf-8')
                    logging.info(f"\n✅ SUCESSO! {len(todos_seguidores)} seguidores salvos em {ARQUIVO_SAIDA_SEGUIDORES}")
                else:
                    logging.info("\n⚠️ Nenhum seguidor foi coletado.")
    except Exception as final_e:
        logging.critical(f"❌ Um erro inesperado ocorreu no fluxo principal do script: {final_e}")
    finally:
        if 'driver' in locals() and driver:
            driver.quit()
            logging.info("Navegador fechado.")