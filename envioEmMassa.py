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

INSTAGRAM_USERNAME = "proescola.com.br"
INSTAGRAM_PASSWORD = "Pro35c0l@2025"

# ============================ AÇÃO NECESSÁRIA AQUI (EDITAR) ============================
# 1. Nome do arquivo CSV que contém a coluna 'username' com os perfis de destino.
ARQUIVO_ENTRADA = "perfis_comerciais_encontrados_v2.csv"

# 2. Cole a URL completa do post que você deseja enviar.
URL_DO_POST_A_ENVIAR = "https://www.instagram.com/p/C9z4h8gA7xR/" # Substitua por uma URL de post real

# 3. (Opcional) Adicione uma mensagem para ser enviada junto com o post. Deixe em branco ("") se não quiser.
MENSAGEM_OPCIONAL = "Olá! Acredito que este conteúdo pode ser do seu interesse."

# 4. Defina o número máximo de DMs para enviar nesta sessão para segurança.
MAX_DMS_A_ENVIAR = 15
# =======================================================================================

# Arquivo para registrar os envios e evitar duplicatas
LOG_DE_ENVIO = "log_de_envio.csv"


# --- FUNÇÕES ---

def perform_login(driver, wait, username, password):
    logging.info("🔑 Realizando login...")
    driver.get("https://www.instagram.com/accounts/login/")
    try:
        wait.until(EC.presence_of_element_located((By.NAME, "username"))).send_keys(username)
        driver.find_element(By.NAME, "password").send_keys(password + Keys.RETURN)
        wait.until(EC.url_contains("instagram.com"))
        logging.info("✅ Login realizado com sucesso.")
        # Lida com vários pop-ups pós-login
        for _ in range(2):
            try:
                WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, "//*[text()='Agora não' or text()='Not Now' or text()='Dispensar']"))).click()
                logging.info("Pop-up de notificação/salvamento fechado.")
            except: pass
    except Exception as e:
        logging.error(f"❌ Erro inesperado durante o login: {e}")
        return False
    return True

def enviar_post_para_perfil(driver, wait, username, mensagem):
    """Lógica para enviar o post para um único perfil."""
    try:
        logging.info(f"    Buscando destinatário: {username}...")
        # 1. Encontrar a caixa de busca de destinatários
        search_box = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@name='search-box']")))
        search_box.send_keys(username)
        time.sleep(3) # Espera os resultados da busca aparecerem

        # 2. Encontrar o destinatário correto na lista e clicar na bolinha de seleção
        # Este XPath é robusto: encontra o span com o username, sobe para a div que agrupa tudo e encontra a bolinha de seleção
        seletor_destinatario = f"//span[text()='{username}']/ancestor::div[contains(@class, 'x1cy8zhl')][1]//div[@role='checkbox']"
        destinatario_checkbox = wait.until(EC.element_to_be_clickable((By.XPATH, seletor_destinatario)))
        destinatario_checkbox.click()
        logging.info(f"      -> Destinatário '{username}' selecionado.")

        # 3. Adicionar mensagem opcional, se houver
        if mensagem:
            try:
                mensagem_box = driver.find_element(By.XPATH, "//textarea[@placeholder='Escreva uma mensagem...']")
                mensagem_box.send_keys(mensagem)
            except NoSuchElementException:
                logging.warning("      -> Caixa de mensagem opcional não encontrada.")

        # 4. Clicar em "Enviar"
        driver.find_element(By.XPATH, "//div[text()='Enviar']/ancestor::button").click()
        logging.info("      -> Botão 'Enviar' clicado.")
        
        # Espera a confirmação de envio (o modal fecha)
        wait.until(EC.invisibility_of_element_located((By.XPATH, "//div[@role='dialog']")))
        return True

    except TimeoutException:
        logging.error(f"   ❌ Timeout: Não foi possível encontrar o perfil '{username}' na lista ou o botão de Enviar.")
        # Clica no botão de cancelar para fechar o modal e tentar o próximo
        try: driver.find_element(By.XPATH, "//button[text()='Cancelar']").click()
        except: driver.refresh()
        return False
    except Exception as e:
        logging.error(f"   ❌ Erro inesperado ao tentar enviar para '{username}': {e}")
        try: driver.find_element(By.XPATH, "//button[text()='Cancelar']").click()
        except: driver.refresh()
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
        
    usernames_para_enviar = df_entrada['username'].dropna().tolist()
    
    # Lógica de resumo: lê o log de envios para não enviar de novo
    if os.path.exists(LOG_DE_ENVIO):
        df_log = pd.read_csv(LOG_DE_ENVIO)
        enviados_anteriormente = df_log['username'].tolist()
        usernames_para_enviar = [u for u in usernames_para_enviar if u not in enviados_anteriormente]
        logging.info(f"Encontrado log de envios. {len(enviados_anteriormente)} perfis já receberam a DM. Restam {len(usernames_para_enviar)}.")
    else:
        # Cria o arquivo de log com cabeçalho
        with open(LOG_DE_ENVIO, 'w', newline='', encoding='utf-8') as f:
            writer = pd.DataFrame(columns=['username', 'timestamp'])
            writer.to_csv(f, index=False)
        logging.info(f"Arquivo de log '{LOG_DE_ENVIO}' criado.")

    if not usernames_para_enviar:
        logging.info("Nenhum novo perfil para enviar mensagem. Encerrando.")
        exit()
    
    # Aplica o limite máximo de envios por sessão
    usernames_para_enviar = usernames_para_enviar[:MAX_DMS_A_ENVIAR]

    driver = None
    try:
        options = Options()
        options.add_argument("--start-maximized")
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        wait = WebDriverWait(driver, 15)
        
        if not perform_login(driver, wait, INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD):
            exit()
        
        enviados_nesta_sessao = 0
        for i, username in enumerate(usernames_para_enviar):
            logging.info(f"\n➡️  Processando {i+1}/{len(usernames_para_enviar)}: {username}")
            
            # Navega para o post a cada envio para garantir um estado limpo
            driver.get(URL_DO_POST_A_ENVIAR)
            time.sleep(3)

            try:
                # Clica no ícone de compartilhar (avião de papel)
                share_icon = wait.until(EC.element_to_be_clickable((By.XPATH, "//svg[@aria-label='Compartilhar publicação' or @aria-label='Share Post']/ancestor::div[@role='button']")))
                share_icon.click()

                if enviar_post_para_perfil(driver, wait, username, MENSAGEM_OPCIONAL):
                    logging.info(f"✅ Post enviado com sucesso para: {username}")
                    # Registra no log
                    log_entry = pd.DataFrame([{'username': username, 'timestamp': pd.Timestamp.now()}])
                    log_entry.to_csv(LOG_DE_ENVIO, mode='a', header=False, index=False)
                    enviados_nesta_sessao += 1
                else:
                    logging.error(f"❌ Falha ao enviar para: {username}")

                # Pausa longa e aleatória para segurança
                pausa = random.uniform(60, 120)
                logging.info(f"   ⏸️ Pausando por {pausa:.1f} segundos para segurança...")
                time.sleep(pausa)

            except Exception as e:
                logging.error(f"Ocorreu um erro no laço principal ao processar '{username}': {e}")
                continue

        logging.info(f"\n🎉 Processo concluído! {enviados_nesta_sessao} DMs foram enviadas nesta sessão.")

    except Exception as final_e:
        logging.critical(f"❌ Um erro fatal ocorreu no fluxo principal: {final_e}")
    finally:
        if driver:
            driver.quit()
            logging.info("Navegador fechado.")