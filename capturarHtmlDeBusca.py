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
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

# --- CONFIGURAÇÕES ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

INSTAGRAM_USERNAME = "antoniocassiorodrigueslima"
INSTAGRAM_PASSWORD = "Lc181340sl@?"

# ============================ AÇÃO NECESSÁRIA AQUI ============================
# Edite esta lista com todas as palavras-chave que você quer pesquisar.
# Dica: Use termos específicos com cidades para melhores resultados.
PALAVRAS_CHAVE = [
    "salão de beleza palmas",
    "barbearia palmas tocantins",
    "clínica estética palmas",
    "loja de roupas palmas",
    "restaurante palmas"
]
# ==============================================================================

ARQUIVO_SAIDA = f"perfis_comerciais_encontrados.csv"


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
            WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//*[text()='Agora não' or text()='Not Now']"))
            ).click()
        except: pass
    except Exception as e:
        logging.error(f"❌ Erro inesperado durante o login: {e}")
        return False
    return True

def buscar_e_coletar_perfis(driver, wait, keywords):
    """Busca por uma lista de palavras-chave e coleta os perfis encontrados."""
    perfis_encontrados = {} # Usar um dicionário para evitar duplicatas (username -> dados)
    
    # Seletor para a linha de resultado, baseado na classe que você encontrou
    # Usamos contains para o caso de a classe mudar um pouco, mas _a6hd parece ser a parte importante.
    SELETOR_LINHA_RESULTADO = (By.XPATH, "//a[contains(@class, '_a6hd')]")

    for keyword in keywords:
        logging.info(f"\n🔎 Buscando pela palavra-chave: '{keyword}'")
        try:
            # 1. Clicar no botão de Pesquisa
            search_icon = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[text()='Pesquisar']/ancestor::a")))
            search_icon.click()
            
            # 2. Digitar a palavra-chave
            search_box = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@aria-label='Entrada da pesquisa']")))
            # Limpa o campo de busca de forma segura
            search_box.send_keys(Keys.CONTROL + "a")
            search_box.send_keys(Keys.DELETE)
            search_box.send_keys(keyword)
            
            logging.info("⏳ Aguardando resultados...")
            time.sleep(5)

            # 3. Coletar os resultados
            resultados = wait.until(EC.presence_of_all_elements_located(SELETOR_LINHA_RESULTADO))
            logging.info(f"   ✅ Encontrados {len(resultados)} resultados para '{keyword}'.")

            for resultado in resultados:
                try:
                    href = resultado.get_attribute('href')
                    username = href.strip('/').split('/')[-1]

                    if username in perfis_encontrados: continue # Pula se já coletamos

                    spans = resultado.find_elements(By.TAG_NAME, 'span')
                    textos = [s.text.strip() for s in spans if s.text.strip()]
                    
                    nome_completo = ""
                    subtitulo = ""
                    
                    if len(textos) > 1:
                        nome_completo = textos[0]
                        subtitulo = textos[1]
                    elif len(textos) == 1:
                        nome_completo = textos[0]
                    
                    if username and nome_completo:
                        perfis_encontrados[username] = {
                            "nome_completo": nome_completo,
                            "subtitulo": subtitulo,
                            "palavra_chave_origem": keyword
                        }
                        logging.info(f"      -> Coletado: {username} ({nome_completo})")

                except Exception:
                    continue # Ignora erros em um único resultado e continua
            
            # Pausa entre as buscas para segurança
            pausa = random.uniform(5, 10)
            logging.info(f"   ⏸️ Pausando por {pausa:.1f} segundos antes da próxima busca...")
            time.sleep(pausa)

        except Exception as e:
            logging.error(f"❌ Falha ao processar a palavra-chave '{keyword}'. Erro: {e}")
            # Clica em outro lugar para fechar a busca e tentar a próxima palavra-chave
            try: driver.find_element(By.XPATH, "//a[contains(@href, '#')]").click() # Link de "Início"
            except: pass
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
            
            if perfis:
                # Transforma o dicionário em um DataFrame do Pandas
                df = pd.DataFrame.from_dict(perfis, orient='index')
                df.reset_index(inplace=True)
                df.rename(columns={'index': 'username'}, inplace=True)
                
                df.to_csv(ARQUIVO_SAIDA, index=False, encoding='utf-8')
                logging.info(f"\n✅ SUCESSO! {len(perfis)} perfis únicos foram encontrados e salvos em '{ARQUIVO_SAIDA}'")
            else:
                logging.info("\n⚠️ Nenhuma perfil foi encontrado para as palavras-chave fornecidas.")

    except Exception as final_e:
        logging.critical(f"❌ Um erro inesperado ocorreu no fluxo principal: {final_e}")
    finally:
        if driver:
            driver.quit()
            logging.info("Navegador fechado.")