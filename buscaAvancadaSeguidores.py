import pandas as pd
import time
import logging
import os
import random
import re
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
ARQUIVO_ENTRADA = os.path.join("seguidores", "seguidores_enriquecido_souto.barbearia.csv")
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

def limpar_numero(texto):
    """Remove pontos, vírgulas e palavras (mil, milhões) de um número em formato de texto."""
    if not isinstance(texto, str):
        return texto
    texto = texto.lower().replace('milhões', 'm').replace('mil', 'k').replace(',', '.').strip()
    
    if 'k' in texto:
        return str(int(float(texto.replace('k', '')) * 1000))
    if 'm' in texto:
        return str(int(float(texto.replace('m', '')) * 1000000))
    
    return re.sub(r'\D', '', texto)

def extrair_dados_avancados_perfil(driver, wait, username):
    """Visita um perfil e extrai as informações avançadas com lógica de extração corrigida."""
    url_perfil = f"https://www.instagram.com/{username}/"
    driver.get(url_perfil)
    
    dados = {
        "bio": "", "n_publicacoes": "0", "n_seguidores": "0", "n_seguindo": "0",
        "link_externo": "", "verificado": False, "status_conta": "Pública"
    }

    try:
        header = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "header")))
        if "Esta conta é privada" in driver.page_source:
            logging.warning(f"   🔒 Perfil '{username}' é privado.")
            dados["status_conta"] = "Privada"
            return dados

        # 1. Extrai números de publicações, seguidores e seguindo (LÓGICA MANTIDA CONFORME SEU PEDIDO)
        try:
            stats_elements = header.find_elements(By.XPATH, ".//li//span")
            if len(stats_elements) >= 3:
                dados['n_publicacoes'] = limpar_numero(stats_elements[0].text)
                dados['n_seguidores'] = limpar_numero(stats_elements[2].get_attribute('title') or stats_elements[2].text)
                dados['n_seguindo'] = limpar_numero(stats_elements[4].text)
        except Exception:
            logging.warning(f"   ⚠️ Não foi possível extrair os números (publicações, seguidores) de '{username}'.")

        # 2. Verifica se o perfil tem o selo de verificado (LÓGICA MANTIDA CONFORME SEU PEDIDO)
        try:
            header.find_element(By.XPATH, ".//svg[@aria-label='Verificado']")
            dados['verificado'] = True
        except NoSuchElementException:
            dados['verificado'] = False
        
        # ======================= INÍCIO DA ALTERAÇÃO (SOMENTE LEITURA DA BIO) =======================
        # 3. Extrai a biografia completa e o link externo com a nova lógica robusta
        try:
            # Seletor para a div que contém nome, bio, categoria e link.
            bio_container = driver.find_element(By.XPATH, "//div[contains(@class, 'x7a106v')]")
            
            # Pega todos os spans e o link dentro do container
            elementos_bio = bio_container.find_elements(By.XPATH, ".//span | .//a")
            
            textos_bio = []
            link_externo = ""

            for elemento in elementos_bio:
                # Se for um link, extrai o href para o campo de link externo
                if elemento.tag_name == 'a':
                    href = elemento.get_attribute('href')
                    # Garante que é um link externo e não um mention (@) ou hashtag (#)
                    if href and not href.startswith(f"https://www.instagram.com/"):
                        link_externo = href
                
                # Adiciona o texto do elemento à lista, exceto o texto do link que já capturamos
                texto_elemento = elemento.text.strip()
                if texto_elemento and elemento.get_attribute('href') is None:
                    # Ignora o nome do perfil, pois já temos essa informação
                    if 'h1' not in elemento.find_element(By.XPATH, '..').tag_name:
                        textos_bio.append(texto_elemento)
            
            # Junta as linhas da bio com quebras de linha
            dados["bio"] = "\n".join(textos_bio)
            dados["link_externo"] = link_externo

        except NoSuchElementException:
            logging.warning(f"   ⚠️ Bio ou link externo não encontrados para '{username}'.")
        # ======================= FIM DA ALTERAÇÃO =======================
            
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
        logging.error(f"O arquivo de entrada '{ARQUIVO_ENTRADA}' não foi encontrado!")
        exit()

    df_entrada = pd.read_csv(ARQUIVO_ENTRADA)
    if 'username' not in df_entrada.columns:
        logging.error("O arquivo de entrada '{ARQUIVO_ENTRADA}' deve conter uma coluna chamada 'username'.")
        exit()

    usernames_para_buscar = df_entrada['username'].tolist()
    colunas_finais = list(df_entrada.columns) + ["bio", "n_publicacoes", "n_seguidores", "n_seguindo", "link_externo", "verificado", "status_conta"]

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
            
            dados_originais = df_entrada[df_entrada['username'] == username].to_dict('records')[0]
            registro_completo = {**dados_originais, **dados_avancados}

            df_para_salvar = pd.DataFrame([registro_completo])
            df_para_salvar = df_para_salvar.reindex(columns=colunas_finais)
            df_para_salvar.to_csv(ARQUIVO_SAIDA, mode='a', header=False, index=False, encoding='utf-8')
            logging.info(f"✅ Dados de '{username}' salvos no CSV.")
            
            total_processados_sessao += 1
            
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