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

# Insira suas credenciais do Instagram
INSTAGRAM_USERNAME = "orkestragestao"
INSTAGRAM_PASSWORD = "Lc181340sl@?" # Substitua pela sua senha real

# ============================ AÇÃO NECESSÁRIA AQUI (EDITAR) ============================
# 1. Nome do arquivo CSV que contém a coluna 'username' com os perfis de destino.
ARQUIVO_ENTRADA = "log_de_seguir.csv"

# 2. Cole a URL completa do post que você deseja enviar.
URL_DO_POST_A_ENVIAR = "https://www.instagram.com/p/DMYLKuFsJU9/"

# 3. (Opcional) Adicione uma mensagem para ser enviada junto com o post. Deixe em branco ("") se não quiser.
MENSAGEM_OPCIONAL = "Oi! Passando pra te mostrar algo que pode fazer total diferença pra você. É rápido e vale a pena conferir!💡🚀"


# 4. Defina o número máximo de DMs para enviar nesta sessão para segurança.
MAX_DMS_A_ENVIAR = 1
# =======================================================================================

# Arquivo para registrar os envios e evitar duplicatas
LOG_DE_ENVIO = "log_de_envio.csv"


# --- FUNÇÕES ---

def perform_login(driver, wait, username, password):
    """Realiza o login na conta do Instagram."""
    logging.info("🔑 Realizando login...")
    driver.get("https://www.instagram.com/accounts/login/")
    try:
        wait.until(EC.presence_of_element_located((By.NAME, "username"))).send_keys(username)
        driver.find_element(By.NAME, "password").send_keys(password + Keys.RETURN)
        wait.until(EC.presence_of_element_located((By.XPATH, "//*[text()='Página inicial']")))
        logging.info("✅ Login realizado com sucesso.")
        time.sleep(random.uniform(3, 5))
        try:
            not_now_button = driver.find_element(By.XPATH, "//div[text()='Agora não']")
            if not_now_button:
                not_now_button.click()
                logging.info("Pop-up 'Salvar informações de login' fechado.")
                time.sleep(random.uniform(2, 4))
        except NoSuchElementException:
            pass

        try:
            not_now_button_notifications = driver.find_element(By.XPATH, "//button[text()='Agora não']")
            if not_now_button_notifications:
                not_now_button_notifications.click()
                logging.info("Pop-up 'Ativar notificações' fechado.")
                time.sleep(random.uniform(2, 3))
        except NoSuchElementException:
            pass

    except TimeoutException:
        logging.error("❌ Timeout: Não foi possível fazer o login.")
        return False
    except Exception as e:
        logging.error(f"❌ Erro inesperado durante o login: {e}")
        return False
    return True

def enviar_post_para_perfil(driver, wait, username, mensagem):
    """Lógica super robusta para encontrar elementos e enviar o post."""
    try:
        logging.info(f"    Buscando destinatário: {username}...")
        
        # 1. Espera o modal de compartilhamento carregar e encontra a caixa de busca
        wait.until(EC.presence_of_element_located((By.XPATH, "//div[@aria-label='Compartilhar']")))
        time.sleep(random.uniform(1.5, 2.5)) # Espera a animação do modal
        
        # Tenta encontrar a caixa de busca com diferentes seletores
        search_box = None
        selectors = [
            "//div[@role='dialog']//input[@placeholder='Pesquisar...']",
            "//div[@role='dialog']//input[@placeholder='Search...']",
            "//div[@role='dialog']//input[@type='text']" # Opção mais genérica
        ]
        
        for selector in selectors:
            try:
                search_box = WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.XPATH, selector)))
                logging.info(f"      -> Caixa de pesquisa encontrada com o seletor: {selector}")
                break # Sai do loop se encontrar
            except TimeoutException:
                continue # Tenta o próximo seletor
        
        if not search_box:
            raise TimeoutException("Não foi possível encontrar a caixa de pesquisa no modal de envio.")

        search_box.send_keys(username)
        time.sleep(random.uniform(4, 6)) # Espera crucial para os resultados da busca carregarem

        # 2. Clica no checkbox ao lado do nome de usuário
        seletor_destinatario = f"//div[@role='dialog']//span[text()='{username}']/ancestor::div[contains(@class, 'x1qjc9v5')][1]//div[@role='checkbox']"
        destinatario_checkbox = wait.until(EC.element_to_be_clickable((By.XPATH, seletor_destinatario)))
        destinatario_checkbox.click()
        logging.info(f"      -> Destinatário '{username}' selecionado.")
        time.sleep(random.uniform(1, 2))

        # 3. Adiciona mensagem opcional, se houver
        if mensagem:
            try:
                mensagem_box = driver.find_element(By.XPATH, "//textarea[@placeholder='Escreva uma mensagem...']")
                mensagem_box.send_keys(mensagem)
                logging.info("      -> Mensagem opcional adicionada.")
                time.sleep(random.uniform(1, 2))
            except NoSuchElementException:
                logging.warning("      -> Caixa de mensagem opcional não encontrada (pode não ser necessária).")

        # 4. Clicar em "Enviar"
        driver.find_element(By.XPATH, "//div[text()='Enviar']/ancestor::button").click()
        logging.info("      -> Botão 'Enviar' clicado.")
        
        # Espera a confirmação de envio (o modal fecha)
        wait.until(EC.invisibility_of_element_located((By.XPATH, "//div[@aria-label='Compartilhar']")))
        return True

    except TimeoutException as e:
        logging.error(f"   ❌ Timeout: {e.msg.splitlines()[0]}")
        try:
            # Tenta fechar o modal para não travar o loop
            close_button = driver.find_element(By.XPATH, "//div[@aria-label='Fechar']")
            close_button.click()
        except:
            driver.refresh() # Último recurso
        return False
    except Exception as e:
        logging.error(f"   ❌ Erro inesperado ao tentar enviar para '{username}': {e}")
        try:
            close_button = driver.find_element(By.XPATH, "//div[@aria-label='Fechar']")
            close_button.click()
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
        
    usernames_para_enviar = df_entrada['username'].dropna().unique().tolist()
    
    if os.path.exists(LOG_DE_ENVIO):
        try:
            df_log = pd.read_csv(LOG_DE_ENVIO)
            enviados_anteriormente = df_log['username'].tolist()
            usernames_para_enviar = [u for u in usernames_para_enviar if u not in enviados_anteriormente]
            logging.info(f"Encontrado log de envios. {len(enviados_anteriormente)} perfis já receberam a DM. Restam {len(usernames_para_enviar)} perfis únicos na fila.")
        except pd.errors.EmptyDataError:
             logging.info(f"Arquivo de log '{LOG_DE_ENVIO}' está vazio. Começando do zero.")
    else:
        pd.DataFrame(columns=['username', 'timestamp']).to_csv(LOG_DE_ENVIO, index=False)
        logging.info(f"Arquivo de log '{LOG_DE_ENVIO}' criado.")

    if not usernames_para_enviar:
        logging.info("Nenhum novo perfil para enviar mensagem. Encerrando.")
        exit()
    
    usernames_para_enviar = usernames_para_enviar[:MAX_DMS_A_ENVIAR]
    logging.info(f"🎯 Sessão atual enviará no máximo {len(usernames_para_enviar)} DMs.")

    driver = None
    try:
        options = Options()
        options.add_argument("--start-maximized")
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        wait = WebDriverWait(driver, 20)
        
        if not perform_login(driver, wait, INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD):
            exit()
        
        enviados_nesta_sessao = 0
        for i, username in enumerate(usernames_para_enviar):
            logging.info(f"\n➡️  Processando {i+1}/{len(usernames_para_enviar)}: {username}")
            
            driver.get(URL_DO_POST_A_ENVIAR)
            
            try:
                # Seletor ATUALIZADO e MAIS ROBUSTO para o ícone de compartilhamento
                share_button_selector = "//*[name()='svg' and @aria-label='Compartilhar']/ancestor::div[@role='button']"
                
                share_button = wait.until(EC.element_to_be_clickable((By.XPATH, share_button_selector)))
                share_button.click()
                logging.info("Botão de compartilhar clicado.")

                if enviar_post_para_perfil(driver, wait, username, MENSAGEM_OPCIONAL):
                    logging.info(f"✅ Post enviado com sucesso para: {username}")
                    log_entry = pd.DataFrame([{'username': username, 'timestamp': pd.Timestamp.now()}])
                    log_entry.to_csv(LOG_DE_ENVIO, mode='a', header=False, index=False)
                    enviados_nesta_sessao += 1
                else:
                    logging.error(f"❌ Falha ao enviar para: {username}")

                # Pausa longa e aleatória entre envios para segurança
                pausa = random.uniform(25, 45)
                logging.info(f"   ⏸️ Pausando por {pausa:.1f} segundos para segurança...")
                time.sleep(pausa)

            except Exception as e:
                logging.error(f"Ocorreu um erro no laço principal ao processar '{username}': {e}")
                # Salva o HTML da página para análise em caso de erro
                try:
                    with open(f"erro_html_{username}.html", "w", encoding="utf-8") as f:
                        f.write(driver.page_source)
                    logging.info(f"HTML da página de erro salvo em erro_html_{username}.html")
                except Exception as html_e:
                    logging.error(f"Falha ao salvar HTML da página: {html_e}")
                continue

        logging.info(f"\n🎉 Processo concluído! {enviados_nesta_sessao} DMs foram enviadas nesta sessão.")

    except Exception as final_e:
        logging.critical(f"❌ Um erro fatal ocorreu no fluxo principal: {final_e}")
    finally:
        if driver:
            driver.quit()
            logging.info("Navegador fechado.")