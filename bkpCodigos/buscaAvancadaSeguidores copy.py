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

# --- CONFIGURAÇÃO DOS ARQUIVOS ---
# O robô vai ler os usernames deste arquivo:
ARQUIVO_ENTRADA = os.path.join("seguidores", "seguidores_enriquecido_souto.barbearia.csv")

# O robô vai criar e salvar os dados completos na pasta 'dadosAvancados'
PASTA_SAIDA = "dadosAvancados"
if not os.path.exists(PASTA_SAIDA):
    os.makedirs(PASTA_SAIDA, exist_ok=True)
ARQUIVO_SAIDA = os.path.join(PASTA_SAIDA, f"dados_avancados_{os.path.splitext(os.path.basename(ARQUIVO_ENTRADA))[0]}.csv")


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

def extrair_dados_avancados_perfil(driver, wait, username):
    """Visita um perfil e extrai as informações avançadas."""
    url_perfil = f"https://www.instagram.com/{username}/"
    driver.get(url_perfil)
    
    dados = {
        "bio": "", "n_publicacoes": "0", "n_seguidores": "0", "n_seguindo": "0",
        "link_externo": "", "status_conta": "Pública"
    }

    try:
        # Espera o cabeçalho do perfil carregar para garantir que a página não está em um estado de erro
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "header")))

        # Verifica se a conta é privada
        if "Esta conta é privada" in driver.page_source:
            logging.warning(f"   🔒 Perfil '{username}' é privado.")
            dados["status_conta"] = "Privada"
            return dados

        # Extrai números de publicações, seguidores e seguindo
        try:
            stats_elements = driver.find_elements(By.CSS_SELECTOR, "header li span span")
            if len(stats_elements) == 3:
                dados["n_publicacoes"] = stats_elements[0].text
                dados["n_seguidores"] = stats_elements[1].text
                dados["n_seguindo"] = stats_elements[2].text
        except Exception:
             logging.warning(f"   ⚠️ Não foi possível extrair os números (publicações, seguidores) de '{username}'.")

        # Extrai a biografia e o link externo
        try:
            # Tenta encontrar o container da bio de uma forma mais genérica
            bio_container = driver.find_element(By.XPATH, "//header/section/div[3]")
            # A bio pode estar em um h1 (para contas de criador/business) ou em um span
            try:
                dados["bio"] = bio_container.find_element(By.TAG_NAME, "h1").find_element(By.XPATH, "./following-sibling::span").text
            except NoSuchElementException:
                dados["bio"] = bio_container.find_element(By.TAG_NAME, "span").text

            # O link é um 'a' dentro do mesmo container
            dados["link_externo"] = bio_container.find_element(By.TAG_NAME, "a").get_attribute("href")
        except NoSuchElementException:
            pass # É normal não ter bio ou link, então apenas ignora o erro
            
    except TimeoutException:
        if "Esta página não está disponível" in driver.page_source:
            logging.error(f"   ❌ Perfil '{username}' não encontrado ou foi excluído.")
            dados["status_conta"] = "Não encontrado"
        else:
            logging.error(f"   ❌ Timeout ao carregar o perfil de '{username}'.")
            dados["status_conta"] = "Erro de carregamento"
    except Exception as e:
        logging.error(f"   ❌ Erro inesperado ao processar o perfil de '{username}': {e}")
        dados["status_conta"] = "Erro inesperado"
        
    return dados


# --- FLUXO PRINCIPAL DE EXECUÇÃO ---
if __name__ == "__main__":

    if not os.path.exists(ARQUIVO_ENTRADA):
        logging.error(f"O arquivo de entrada '{ARQUIVO_ENTRADA}' não foi encontrado! Verifique o nome e se ele está na mesma pasta do script.")
        exit()

    df_entrada = pd.read_csv(ARQUIVO_ENTRADA)
    if 'username' not in df_entrada.columns:
        logging.error(f"O arquivo de entrada '{ARQUIVO_ENTRADA}' deve conter uma coluna chamada 'username'.")
        exit()

    usernames_para_buscar = df_entrada['username'].tolist()

    colunas_finais = list(df_entrada.columns) + ["bio", "n_publicacoes", "n_seguidores", "n_seguindo", "link_externo", "status_conta"]

    # Garante que o diretório do arquivo de saída existe
    dir_saida = os.path.dirname(ARQUIVO_SAIDA)
    if dir_saida and not os.path.exists(dir_saida):
        os.makedirs(dir_saida, exist_ok=True)

    if os.path.exists(ARQUIVO_SAIDA):
        logging.info("Encontrado arquivo de progresso. Continuando de onde parou...")
        df_progresso = pd.read_csv(ARQUIVO_SAIDA)
        usernames_ja_buscados = df_progresso['username'].tolist()
        usernames_para_buscar = [u for u in usernames_para_buscar if u not in usernames_ja_buscados]
        logging.info(f"{len(usernames_ja_buscados)} perfis já processados. Restam {len(usernames_para_buscar)}.")
    else:
        pd.DataFrame(columns=colunas_finais).to_csv(ARQUIVO_SAIDA, index=False, encoding='utf-8')
        logging.info(f"Arquivo de saída '{ARQUIVO_SAIDA}' criado com sucesso.")

    if not usernames_para_buscar:
        logging.info("Todos os perfis já foram processados. Encerrando.")
        exit()

    driver = None
    try:
        options = Options()
        options.add_argument("--start-maximized")
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        wait = WebDriverWait(driver, 15)
        
        if not perform_login(driver, wait, INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD):
            exit()
        
        total_processados_sessao = 0
        for i, username in enumerate(usernames_para_buscar):
            logging.info(f"➡️  Processando perfil {i+1}/{len(usernames_para_buscar)}: {username}")
            
            dados_avancados = extrair_dados_avancados_perfil(driver, wait, username)
            
            # Junta os dados originais do CSV de entrada com os novos dados coletados
            dados_originais = df_entrada[df_entrada['username'] == username].to_dict('records')[0]
            registro_completo = {**dados_originais, **dados_avancados}

            # =================== LÓGICA DE SALVAMENTO ATUALIZADA ===================
            # Cria um DataFrame com apenas uma linha e anexa ao arquivo CSV
            df_para_salvar = pd.DataFrame([registro_completo])
            df_para_salvar.to_csv(ARQUIVO_SAIDA, mode='a', header=False, index=False, encoding='utf-8')
            logging.info(f"✅ Dados de '{username}' salvos no CSV.")
            # =======================================================================
            
            total_processados_sessao += 1
            
            # Pausa aleatória entre cada perfil para segurança
            pausa = random.uniform(8, 15)
            logging.info(f"   ⏸️ Pausando por {pausa:.1f} segundos...")
            time.sleep(pausa)

        logging.info(f"\n🎉 Processo de enriquecimento de dados concluído! {total_processados_sessao} novos perfis foram processados nesta sessão.")

    except Exception as final_e:
        logging.critical(f"❌ Um erro inesperado ocorreu no fluxo principal: {final_e}")
    finally:
        if driver:
            driver.quit()
            logging.info("Navegador fechado.")
