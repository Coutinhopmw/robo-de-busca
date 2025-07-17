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
import os

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- SUAS CONFIGURAÇÕES ---
INSTAGRAM_USERNAME = "antoniocassiorodrigueslima"
INSTAGRAM_PASSWORD = "Lc181340sl@?"
PERFIL_ALVO = "fgtaekwondo" 
LIMITE_SEGUIDORES = float('inf') 
# Nome do arquivo de saída atualizado para refletir o conteúdo
# ARQUIVO_SAIDA_SEGUIDORES = f"seguidores_enriquecido_{PERFIL_ALVO}.csv"
ARQUIVO_SAIDA_SEGUIDORES = os.path.join("seguidores", f"seguidores_enriquecido_{PERFIL_ALVO}.csv")

# --- FUNÇÕES DO SCRIPT ---

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
        except:
            pass
    except Exception as e:
        logging.error(f"❌ Erro inesperado durante o login: {e}")
        return False
    return True

def garantir_perfil_alvo(driver, wait, perfil_alvo):
    url_perfil = f"https://www.instagram.com/{perfil_alvo}/"
    logging.info(f"Navegando para o perfil {perfil_alvo}...")
    driver.get(url_perfil)
    try:
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "header")))
        logging.info(f"✅ Perfil {perfil_alvo} acessado com sucesso.")
        return True
    except Exception as e:
        logging.error(f"❌ Não foi possível acessar o perfil {perfil_alvo}: {e}")
        return False

def coletar_seguidores(driver, wait, perfil_alvo, limite_seguidores):
    logging.info("📥 Coletando seguidores em tempo real...")
    seguidores = {}
    scrolls_sem_novos = 0
    scroll_limit = 15

    try:
        logging.info("🔍 Procurando e clicando no botão de 'seguidores'...")
        seguidores_btn = wait.until(EC.element_to_be_clickable((By.XPATH, f"//a[contains(@href, '/followers/')]")))
        seguidores_btn.click()
        logging.info("✅ Botão de seguidores clicado.")
    except Exception as e:
        logging.error(f"❌ Erro ao clicar no botão de seguidores: {e}")
        return {}

    try:
        logging.info("⏳ Aguardando modal e pausando 3 segundos para carregar...")
        wait.until(EC.presence_of_element_located((By.XPATH, "//div[@role='dialog']")))
        time.sleep(3)
    except Exception as e:
        logging.error(f"❌ Erro ao carregar a janela de seguidores: {e}")
        return {}
        
    SELETOR_CONTAINER_SCROLL = (By.XPATH, "//div[contains(@class, 'x6nl9eh')]")
    SELETOR_LINHA_USUARIO = (By.CSS_SELECTOR, "div.x9f619.x1ja2u2z.x78zum5.x2lah0s.x1n2onr6.x1qughib.x6s0dn4.xozqiw3.x1q0g3np")
    
    try:
        scroll_container = driver.find_element(*SELETOR_CONTAINER_SCROLL)
        logging.info("✅ Container de rolagem encontrado com sucesso!")
    except NoSuchElementException:
        logging.error("❌ Não foi possível encontrar o container de rolagem com o seletor definitivo.")
        return {}

    while len(seguidores) < limite_seguidores and scrolls_sem_novos < scroll_limit:
        try:
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scroll_container)
            time.sleep(2)

            linhas_de_usuario = scroll_container.find_elements(*SELETOR_LINHA_USUARIO)
            if not linhas_de_usuario:
                scrolls_sem_novos += 1
                logging.warning(f"⚠️ Nenhuma linha de usuário encontrada. Tentativa {scrolls_sem_novos}/{scroll_limit}")
                continue

            novos_encontrados = 0
            # ======================= INÍCIO DA LÓGICA DE EXTRAÇÃO ENRIQUECIDA =======================
            for linha in linhas_de_usuario:
                try:
                    link_element = linha.find_element(By.TAG_NAME, "a")
                    href = link_element.get_attribute('href')
                    username = href.strip('/').split('/')[-1]

                    if username in seguidores: continue

                    # 1. Extrai Nome Completo
                    nome_completo = ""
                    spans = linha.find_elements(By.TAG_NAME, "span")
                    textos = [s.text.strip() for s in spans if s.text.strip() and "·" not in s.text and "Seguir" not in s.text]
                    
                    if len(textos) > 1 and textos[0].lower() == username.lower():
                        nome_completo = textos[1]
                    elif len(textos) > 0 and textos[0].lower() != username.lower():
                        nome_completo = textos[0]
                    
                    # 2. Extrai Status de Verificação
                    verificado = True if linha.find_elements(By.XPATH, ".//svg[@aria-label='Verificado']") else False

                    # 3. Extrai URL da Foto de Perfil
                    url_foto_perfil = ""
                    try:
                        url_foto_perfil = linha.find_element(By.TAG_NAME, "img").get_attribute('src')
                    except NoSuchElementException: pass

                    # 4. Extrai Status da Relação
                    status_relacao = ""
                    try:
                        status_relacao = linha.find_element(By.TAG_NAME, "button").text
                    except NoSuchElementException: pass

                    # Armazena todos os dados em um dicionário
                    if username:
                        seguidores[username] = {
                            "nome_completo": nome_completo,
                            "verificado": verificado,
                            "url_foto_perfil": url_foto_perfil,
                            "status_relacao": status_relacao
                        }
                        novos_encontrados += 1
                except Exception:
                    continue
            # ======================== FIM DA LÓGICA DE EXTRAÇÃO ENRIQUECIDA ========================
            
            if novos_encontrados > 0:
                logging.info(f"Capturados {novos_encontrados} novos usuários. Total: {len(seguidores)}")
                scrolls_sem_novos = 0
            else:
                scrolls_sem_novos += 1
                logging.info(f"↕️ Nenhum usuário *novo* encontrado. Tentativa {scrolls_sem_novos}/{scroll_limit}")

        except StaleElementReferenceException:
            logging.warning("Elemento de rolagem obsoleto, tentando reencontrá-lo...")
            try:
                scroll_container = driver.find_element(*SELETOR_CONTAINER_SCROLL)
            except:
                logging.error("Não foi possível reencontrar o elemento de rolagem. Interrompendo.")
                break
        except Exception as e:
            logging.error(f"⚠️ Erro inesperado durante a coleta: {e}")
            break

    return seguidores

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
            if garantir_perfil_alvo(driver, wait, PERFIL_ALVO):
                todos_seguidores = coletar_seguidores(driver, wait, PERFIL_ALVO, LIMITE_SEGUIDORES)
                if todos_seguidores:
                    # ======================= SALVANDO OS DADOS ENRIQUECIDOS =======================
                    # Transforma o dicionário de dicionários em um DataFrame do Pandas
                    df = pd.DataFrame.from_dict(todos_seguidores, orient='index')
                    # Reseta o índice para que o 'username' se torne uma coluna
                    df.reset_index(inplace=True)
                    df.rename(columns={'index': 'username'}, inplace=True)
                    
                    df.to_csv(ARQUIVO_SAIDA_SEGUIDORES, index=False, encoding='utf-8')
                    logging.info(f"\n✅ SUCESSO! {len(todos_seguidores)} seguidores salvos em {ARQUIVO_SAIDA_SEGUIDORES}")
                    # ==============================================================================
                else:
                    logging.info("\n⚠️ Nenhum seguidor foi coletado.")
    except Exception as final_e:
        logging.critical(f"❌ Um erro inesperado ocorreu no fluxo principal do script: {final_e}")
    finally:
        if driver:
            try: 
                driver.find_element(By.XPATH, "//div[@role='dialog']//button[contains(@class, 'x1i10hfl')]").click()
                time.sleep(1)
            except: 
                pass
            driver.quit()
            logging.info("Navegador fechado.")