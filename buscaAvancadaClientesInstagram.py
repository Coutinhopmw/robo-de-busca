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

INSTAGRAM_USERNAME = "antoniocassiorodrigueslima"
INSTAGRAM_PASSWORD = "Lc181340sl@?"

# --- CONFIGURAÇÃO DOS ARQUIVOS ---
# O robô vai ler os usernames deste arquivo:
ARQUIVO_ENTRADA = os.path.join("buscaClientesInstagram", "perfis_comerciais_encontrados.csv")
# O robô vai criar e salvar os dados detalhados neste novo arquivo:
ARQUIVO_SAIDA = os.path.join("dadosAvancadosBuscaClientesInstagram", "leads_detalhados.csv")

# --- FUNÇÕES ---

def perform_login(driver, wait, username, password):
    logging.info("🔑 Realizando login...")
    driver.get("https://www.instagram.com/accounts/login/")
    try:
        wait.until(EC.presence_of_element_located((By.NAME, "username"))).send_keys(username)
        driver.find_element(By.NAME, "password").send_keys(password + Keys.RETURN)
        wait.until(EC.url_contains("instagram.com"))
        logging.info("✅ Login realizado com sucesso.")
        try:
            WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, "//*[text()='Agora não' or text()='Not Now']"))).click()
        except: pass
    except Exception as e:
        logging.error(f"❌ Erro inesperado durante o login: {e}")
        return False
    return True

def extrair_dados_detalhados(driver, wait, username):
    """Visita um perfil e extrai um conjunto completo de informações comerciais."""
    url_perfil = f"https://www.instagram.com/{username}/"
    driver.get(url_perfil)
    
    dados = {
        "categoria": "", "bio": "", "n_publicacoes": "0", "n_seguidores": "0", 
        "n_seguindo": "0", "link_externo": "", "telefone": "", "email": "", 
        "endereco": "", "status_conta": "Pública"
    }

    try:
        header = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "header")))
        if "Esta conta é privada" in driver.page_source:
            dados["status_conta"] = "Privada"
            return dados

        # Métricas: Publicações, Seguidores, Seguindo
        try:
            stats_list = header.find_elements(By.CSS_SELECTOR, "ul li")
            if len(stats_list) == 3:
                dados["n_publicacoes"] = stats_list[0].text.split(' ')[0]
                dados["n_seguidores"] = stats_list[1].text.split(' ')[0]
                dados["n_seguindo"] = stats_list[2].text.split(' ')[0]
        except Exception: pass

        # Categoria, Bio e Link Externo
        try:
            bio_container = driver.find_element(By.XPATH, "//header/section/div[3]")
            spans = bio_container.find_elements(By.TAG_NAME, 'span')
            dados['categoria'] = spans[0].text if spans else ""
            dados['bio'] = spans[1].text if len(spans) > 1 else ""
            dados['link_externo'] = bio_container.find_element(By.TAG_NAME, "a").get_attribute("href")
        except Exception: pass

        # Informações de Contato (a parte mais complexa)
        try:
            # Procura por um botão de Contato, E-mail ou Ligar
            botoes_contato = driver.find_elements(By.XPATH, "//div[contains(text(), 'E-mail') or contains(text(), 'Contato') or contains(text(), 'Ligar')]")
            if botoes_contato:
                # Se houver um botão de contato, clica nele para abrir o modal
                botoes_contato[0].click()
                time.sleep(2)
                # Tenta ler as informações do modal de contato
                info_elements = driver.find_elements(By.XPATH, "//div[@role='dialog']//div[contains(@class, 'x1i10hfl')]")
                for info in info_elements:
                    if "@" in info.text:
                        dados['email'] = info.text
                    elif any(char.isdigit() for char in info.text): # Heurística para telefone
                        dados['telefone'] = info.text
                    else: # Heurística para endereço
                        dados['endereco'] = info.text
                # Fecha o modal de contato
                try: driver.find_element(By.XPATH, "//div[@role='dialog']//div[@aria-label='Fechar']").click()
                except: driver.refresh()
            else:
                 # Se não houver botão, tenta encontrar um link mailto: na página
                 email_links = driver.find_elements(By.XPATH, "//a[contains(@href, 'mailto:')]")
                 if email_links:
                     dados['email'] = email_links[0].get_attribute('href').replace('mailto:', '')
        except Exception: pass
            
    except TimeoutException:
        dados["status_conta"] = "Não encontrado/Timeout"
    except Exception as e:
        dados["status_conta"] = f"Erro: {e}"
        
    return dados

# --- FLUXO PRINCIPAL ---
if __name__ == "__main__":
    if not os.path.exists("dadosAvancadosBuscaClientesInstagram"):
        os.makedirs("dadosAvancadosBuscaClientesInstagram")
    if not os.path.exists(ARQUIVO_ENTRADA):
        logging.error(f"O arquivo de entrada '{ARQUIVO_ENTRADA}' não foi encontrado!")
        exit()

    df_entrada = pd.read_csv(ARQUIVO_ENTRADA)
    if 'username' not in df_entrada.columns:
        logging.error("O arquivo de entrada deve conter uma coluna chamada 'username'.")
        exit()
        
    usernames_para_buscar = df_entrada['username'].tolist()
    
    colunas_detalhadas = [
        "categoria", "bio", "n_publicacoes", "n_seguidores", "n_seguindo",
        "link_externo", "telefone", "email", "endereco", "status_conta"
    ]
    colunas_finais = list(df_entrada.columns) + colunas_detalhadas

    # Cria o arquivo CSV com cabeçalho se não existir
    if not os.path.exists(ARQUIVO_SAIDA):
        import csv
        with open(ARQUIVO_SAIDA, mode='w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(colunas_finais)
        logging.info(f"Arquivo de saída '{ARQUIVO_SAIDA}' criado com sucesso.")
    else:
        df_progresso = pd.read_csv(ARQUIVO_SAIDA)
        usernames_ja_buscados = df_progresso['username'].tolist()
        usernames_para_buscar = [u for u in usernames_para_buscar if u not in usernames_ja_buscados]
        logging.info(f"{len(usernames_ja_buscados)} perfis já processados. Restam {len(usernames_para_buscar)}.")

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
        
        import csv
        for i, username in enumerate(usernames_para_buscar):
            logging.info(f"➡️  Processando perfil {i+1}/{len(usernames_para_buscar)}: {username}")
            
            dados_avancados = extrair_dados_detalhados(driver, wait, username)
            
            dados_originais = df_entrada[df_entrada['username'] == username].to_dict('records')[0]
            registro_completo = {**dados_originais, **dados_avancados}

            # Salva imediatamente no CSV
            with open(ARQUIVO_SAIDA, mode='a', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=colunas_finais)
                writer.writerow(registro_completo)
            logging.info(f"✅ Dados de '{username}' salvos no CSV.")
            
            pausa = random.uniform(12, 22)
            logging.info(f"   ⏸️ Pausando por {pausa:.1f} segundos...")
            time.sleep(pausa)

        logging.info(f"\n🎉 Processo de enriquecimento concluído!")

    except Exception as final_e:
        logging.critical(f"❌ Um erro inesperado ocorreu no fluxo principal: {final_e}")
    finally:
        if driver:
            driver.quit()
            logging.info("Navegador fechado.")