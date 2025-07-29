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

INSTAGRAM_USERNAME = "proescola.com.br" # Substitua pelo seu usuário
INSTAGRAM_PASSWORD = "Pro35c0l@2025" # Substitua pela sua senha

# ============================ AÇÃO NECESSÁRIA AQUI (EDITAR) ============================
ARQUIVO_ENTRADA = "Empresa__Comércio.csv"
URL_DO_POST_A_ENVIAR = "https://www.instagram.com/p/DMsLiIEsLbH/" # Substitua por uma URL de post real
MENSAGEM_OPCIONAL = "Olá! Vimos seu perfil e acreditamos que este conteúdo pode ser do seu interesse."
MAX_DMS_POR_SESSAO = 1 # MANTENHA BAIXO PARA TESTES
# =======================================================================================

LOG_DE_ENVIO = "log_de_envio.csv"


# --- FUNÇÕES ---

def salvar_html_para_debug(driver, nome_arquivo):
    """Salva o HTML da página atual para auxiliar na depuração."""
    try:
        caminho_completo = os.path.join(os.getcwd(), f"{nome_arquivo}.html")
        with open(caminho_completo, 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        logging.info(f"💾 HTML de depuração salvo em: {caminho_completo}")
    except Exception as e:
        logging.error(f"   Falha ao salvar o arquivo HTML de depuração: {e}")

def perform_login(driver, wait, username, password):
    logging.info("🔑 Iniciando processo de login...")
    driver.get("https://www.instagram.com/accounts/login/")
    try:
        logging.info("   - Aguardando campo 'username'...")
        wait.until(EC.presence_of_element_located((By.NAME, "username"))).send_keys(username)
        logging.info("   - Preenchendo senha e pressionando ENTER...")
        driver.find_element(By.NAME, "password").send_keys(password + Keys.RETURN)
        wait.until(EC.url_contains("instagram.com"))
        logging.info("✅ Login realizado com sucesso.")
        
        for i in range(2):
            try:
                logging.info(f"   - Procurando por pop-ups (tentativa {i+1}/2)...")
                pop_up_button = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, "//*[text()='Agora não' or text()='Not Now' or text()='Dispensar']")))
                pop_up_button.click()
                logging.info("   - Pop-up de notificação/salvamento fechado.")
                time.sleep(1)
            except:
                logging.info("   - Nenhum pop-up encontrado.")
                break
    except Exception as e:
        logging.error(f"❌ Erro inesperado durante o login: {e}")
        salvar_html_para_debug(driver, "erro_durante_login")
        return False
    return True

def enviar_post_para_perfil(driver, wait, username, mensagem):
    """Lógica detalhada para enviar o post para um único perfil."""
    try:
        logging.info(f"    Buscando destinatário: {username}...")
        search_box = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@name='search-box']")))
        search_box.send_keys(username)
        logging.info(f"      -> Aguardando resultados para '{username}'...")
        time.sleep(4)

        seletor_destinatario = f"//span[text()='{username}']/ancestor::div[4]//div[@role='checkbox']"
        destinatario_checkbox = wait.until(EC.element_to_be_clickable((By.XPATH, seletor_destinatario)))
        logging.info("      -> Checkbox do destinatário encontrado. Clicando...")
        destinatario_checkbox.click()
        logging.info("      -> Destinatário selecionado.")

        if mensagem:
            try:
                mensagem_box = driver.find_element(By.XPATH, "//textarea[@placeholder='Escreva uma mensagem...']")
                mensagem_box.send_keys(mensagem)
                logging.info("      -> Mensagem opcional inserida.")
            except NoSuchElementException:
                logging.warning("      -> Caixa de mensagem opcional não encontrada.")

        logging.info("      -> Procurando botão 'Enviar'...")
        driver.find_element(By.XPATH, "//div[text()='Enviar']/ancestor::button").click()
        logging.info("      -> Botão 'Enviar' clicado.")
        
        wait.until(EC.invisibility_of_element_located((By.XPATH, "//div[@aria-label='Compartilhar']")))
        return True

    except Exception as e:
        logging.error(f"   ❌ Erro ao tentar enviar para '{username}': {e}")
        salvar_html_para_debug(driver, f"erro_modal_envio_{username}")
        try: 
            driver.find_element(By.XPATH, "//div[@aria-label='Fechar']/ancestor::button").click()
        except: 
            driver.refresh()
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
    
    if os.path.exists(LOG_DE_ENVIO):
        df_log = pd.read_csv(LOG_DE_ENVIO)
        enviados_anteriormente = df_log['username'].tolist()
        usernames_para_enviar = [u for u in usernames_para_enviar if u not in enviados_anteriormente]
        logging.info(f"Encontrado log de envios. {len(enviados_anteriormente)} perfis já receberam a DM. Restam {len(usernames_para_enviar)}.")
    else:
        pd.DataFrame(columns=['username', 'timestamp']).to_csv(LOG_DE_ENVIO, index=False)

    if not usernames_para_enviar:
        logging.info("Nenhum novo perfil para enviar mensagem. Encerrando.")
        exit()
    
    usernames_para_enviar = usernames_para_enviar[:MAX_DMS_POR_SESSAO]

    driver = None
    try:
        options = Options()
        options.add_argument("--start-maximized")
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        wait = WebDriverWait(driver, 15)
        
        if not perform_login(driver, wait, INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD):
            exit()
        
        driver.get(URL_DO_POST_A_ENVIAR)
        logging.info(f"Navegando para o post a ser compartilhado: {URL_DO_POST_A_ENVIAR}")
        time.sleep(3)
        
        enviados_nesta_sessao = 0
        for i, username in enumerate(usernames_para_enviar):
            logging.info(f"\n➡️  Processando {i+1}/{len(usernames_para_enviar)}: {username}")
            
            try:
                logging.info("   - Procurando ícone de compartilhar (avião de papel)...")
                # ======================= SELETOR CORRIGIDO =======================
                # O seletor foi ajustado para ser mais robusto, pegando o terceiro
                # botão na barra de ações (Curtir, Comentar, Compartilhar).
                share_icon = wait.until(EC.element_to_be_clickable(
                    (By.XPATH, "(//section/span/div/div)[3]")
                ))
                # =================================================================
                share_icon.click()
                logging.info("   - Ícone de compartilhar clicado.")

                if enviar_post_para_perfil(driver, wait, username, MENSAGEM_OPCIONAL):
                    logging.info(f"✅ Post enviado com sucesso para: {username}")
                    log_entry = pd.DataFrame([{'username': username, 'timestamp': pd.Timestamp.now()}])
                    log_entry.to_csv(LOG_DE_ENVIO, mode='a', header=False, index=False)
                    enviados_nesta_sessao += 1
                else:
                    logging.error(f"❌ Falha no processo de envio para: {username}")

                pausa = random.uniform(60, 120)
                logging.info(f"   ⏸️ Pausando por {pausa:.1f} segundos para segurança...")
                time.sleep(pausa)

            except Exception as e:
                logging.error(f"Ocorreu um erro CRÍTICO no laço principal ao processar '{username}': {e}")
                salvar_html_para_debug(driver, f"erro_principal_{username}")
                logging.info("Tentando atualizar a página para se recuperar...")
                driver.get(URL_DO_POST_A_ENVIAR)
                time.sleep(5)
                continue

        logging.info(f"\n🎉 Processo concluído! {enviados_nesta_sessao} DMs foram enviadas nesta sessão.")

    except Exception as final_e:
        logging.critical(f"❌ Um erro fatal ocorreu no fluxo principal: {final_e}")
        if driver:
            salvar_html_para_debug(driver, "erro_fatal")
    finally:
        if driver:
            driver.quit()
            logging.info("Navegador fechado.")