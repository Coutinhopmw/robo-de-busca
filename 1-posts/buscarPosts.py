import pandas as pd
import time
import logging
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

# --- CONFIGURAÇÕES ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# INSTAGRAM_USERNAME = "antoniocassiorodrigueslima@gmail.com"
# INSTAGRAM_PASSWORD = "Lc181340@#LSA$(*C"
# PERFIL_ALVO = "titaniumparaiso" 

# INSTAGRAM_USERNAME = "proescola.com.br"
# INSTAGRAM_PASSWORD = "Pro35c0l@2025"
INSTAGRAM_USERNAME = "gabijardimsantos"
INSTAGRAM_PASSWORD = "Lc181340sl@?"

# Lista de perfis para análise sequencial (até 5 perfis)
PERFIS_ALVO = [
    "clinicavidacfs",
    "saudeamemedicina",
    "doutorsorrisoconfresa",
    "clinicaimedconfresa",
    "hospitaldriron",
    "ses.mt",
    "confresamilgrau_",
]

# Limites (ajuste conforme necessário)
MAX_POSTS_PARA_ANALISAR = 200
MAX_CURTIDAS_POR_POST = float('inf') # Use float('inf') para pegar todos


# --- FUNÇÕES AUXILIARES ---

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
            # Tenta fechar pop-ups de "Salvar informações" ou "Ativar notificações"
            WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, "//button[text()='Agora não']"))).click()
        except: pass
    except Exception as e:
        logging.error(f"❌ Erro inesperado durante o login: {e}")
        return False
    return True

# --- FUNÇÕES PRINCIPAIS DE SCRAPING ---

def get_post_links(driver, wait, perfil_alvo, max_posts):
    """Navega pelo perfil e coleta os links dos posts mais recentes."""
    url_perfil = f"https://www.instagram.com/{perfil_alvo}/"
    logging.info(f"Navegando para o perfil {perfil_alvo} para coletar links de posts...")
    driver.get(url_perfil)
    post_links = set()
    scrolls = 0
    max_scrolls = 20
    last_height = driver.execute_script("return document.body.scrollHeight")
    
    while len(post_links) < max_posts and scrolls < max_scrolls:
        try:
            elements = wait.until(EC.presence_of_all_elements_located((By.XPATH, "//a[contains(@href, '/p/')]")))
            for el in elements:
                post_links.add(el.get_attribute('href'))
                if len(post_links) >= max_posts: break
            
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
            
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height: scrolls += 1
            else: scrolls = 0
            last_height = new_height
        except Exception as e:
            logging.error(f"Erro ao rolar e coletar links de posts: {e}")
            break
            
    logging.info(f"✅ Encontrados {len(post_links)} links de posts para analisar.")
    return list(post_links)[:max_posts]

def get_post_details(driver, wait):
    """Na página de um post, extrai a data e a legenda usando seletores precisos."""
    data_post, texto_post = "", ""
    try:
        # Usa espera explícita para garantir que a tag <time> carregou
        time_element = wait.until(EC.presence_of_element_located((By.TAG_NAME, "time")))
        data_post = time_element.get_attribute('datetime')
    except: logging.warning("   ⚠️ Data do post não encontrada.")
        
    try:
        # Seletor preciso para a legenda, baseado no HTML capturado
        caption_element = wait.until(EC.presence_of_element_located((By.XPATH, "//h1//span")))
        texto_post = caption_element.text
    except: logging.warning("   ⚠️ Legenda do post não encontrada.")
    
    return data_post, texto_post

def scrape_likes_from_modal(driver, wait, max_likes):
    """Com o modal de curtidas aberto, rola e extrai os dados detalhados dos usuários."""
    likers = {}
    SELETOR_CONTAINER_SCROLL = (By.XPATH, "//div[contains(@class, 'x1kb659o')]//div[contains(@style, 'overflow')]")
    SELETOR_LINHA_USUARIO = (By.CSS_SELECTOR, "div.x9f619.x1ja2u2z.x78zum5.x2lah0s.x1n2onr6.x1qughib.x6s0dn4.xozqiw3.x1q0g3np")

    try:
        scroll_container = wait.until(EC.presence_of_element_located(SELETOR_CONTAINER_SCROLL))
        logging.info("      ✅ Container de rolagem de curtidas encontrado.")
    except Exception as e:
        logging.error(f"      ❌ Não foi possível encontrar o container de rolagem de curtidas: {e}")
        return {}

    tentativas_sem_novos = 0
    total_anterior = 0
    import pandas as pd
    from datetime import datetime
    # Recebe contexto do post para salvar incrementalmente
    global data_post_global, texto_post_global, ARQUIVO_SAIDA_CURTIDAS
    max_tentativas_sem_novos = 5  # Reduzido para 5 tentativas conforme solicitado
    scroll_position = 0  # Posição atual do scroll
    
    while len(likers) < max_likes and tentativas_sem_novos < max_tentativas_sem_novos:
        try:
            linhas_de_usuario = scroll_container.find_elements(*SELETOR_LINHA_USUARIO)
            novos = 0
            for linha in linhas_de_usuario:
                try:
                    username_link_element = linha.find_element(By.TAG_NAME, "a")
                    username = username_link_element.get_attribute('href').strip('/').split('/')[-1]
                    if username in likers:
                        continue
                    verificado = True if linha.find_elements(By.XPATH, ".//svg[@aria-label='Verificado']") else False
                    url_foto_perfil = linha.find_element(By.TAG_NAME, "img").get_attribute('src')
                    status_relacao = linha.find_element(By.TAG_NAME, "button").text
                    nome_completo = ""
                    spans = linha.find_elements(By.TAG_NAME, 'span')
                    textos = [s.text.strip() for s in spans if s.text.strip() and "·" not in s.text]
                    if len(textos) > 1 and textos[0].lower() == username.lower():
                        nome_completo = textos[1]
                    elif len(textos) > 0 and textos[0].lower() != username.lower():
                        nome_completo = textos[0]
                    likers[username] = {"nome_completo": nome_completo, "verificado": verificado, "url_foto_perfil": url_foto_perfil, "status_relacao": status_relacao}
                    # Salva incrementalmente no CSV
                    dados_post = [{
                        "data_post": data_post_global if 'data_post_global' in globals() else '',
                        "texto_post": texto_post_global if 'texto_post_global' in globals() else '',
                        "username_curtiu": username,
                        "nome_completo_curtiu": nome_completo,
                        "verificado": verificado,
                        "url_foto_perfil": url_foto_perfil,
                        "status_relacao": status_relacao
                    }]
                    df_post = pd.DataFrame(dados_post)
                    df_post.to_csv(ARQUIVO_SAIDA_CURTIDAS, mode='a', header=False, index=False, encoding='utf-8')
                    novos += 1
                    if len(likers) >= max_likes:
                        break
                except Exception:
                    continue
            
            if novos > 0:
                logging.info(f"      ...coletadas {len(likers)} curtidas.")
                tentativas_sem_novos = 0
            else:
                tentativas_sem_novos += 1
                
            # Rolagem suave de 20px por vez
            scroll_position += 20
            driver.execute_script("arguments[0].scrollTop = arguments[1]", scroll_container, scroll_position)
            time.sleep(0.5)  # Tempo menor para rolagem mais fluida
            
        except Exception as e:
            logging.error(f"      ❌ Erro ao rolar ou coletar usuários: {e}")
            break
    return likers

def coletar_curtidas_de_posts(driver, wait, perfil_alvo, max_posts, max_curtidas):
    """Função principal que orquestra todo o processo de coleta de curtidas."""
    
    # Define o arquivo de saída específico para este perfil
    arquivo_saida_curtidas = os.path.join(os.path.dirname(__file__), f"curtidas_completo_{perfil_alvo}.csv")
    
    post_links = get_post_links(driver, wait, perfil_alvo, max_posts)
    if not post_links:
        return []

    colunas = [
        "data_post", "texto_post", "username_curtiu",
        "nome_completo_curtiu", "verificado",
        "url_foto_perfil", "status_relacao"
    ]

    # Cria o arquivo CSV com cabeçalho antes de começar
    if not os.path.exists(arquivo_saida_curtidas):
        pd.DataFrame(columns=colunas).to_csv(arquivo_saida_curtidas, index=False, encoding='utf-8')

    global data_post_global, texto_post_global, ARQUIVO_SAIDA_CURTIDAS
    ARQUIVO_SAIDA_CURTIDAS = arquivo_saida_curtidas  # Define globalmente para uso no scrape_likes_from_modal
    
    for i, post_url in enumerate(post_links):
        try:
            logging.info(f"\n➡️  Analisando Post {i+1}/{len(post_links)} do perfil {perfil_alvo}")
            driver.get(post_url)

            data_post, texto_post = get_post_details(driver, wait)
            logging.info(f"   Data: {data_post} | Legenda: {texto_post[:30]}...")

            # Define variáveis globais para uso incremental
            data_post_global = data_post
            texto_post_global = texto_post

            wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, '/liked_by/')]"))).click()
            wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, '/liked_by/')]"))).click()

            likers = scrape_likes_from_modal(driver, wait, max_curtidas)
            logging.info(f"   ✅ Coletadas {len(likers)} curtidas para este post.")

            try:
                driver.find_element(By.XPATH, "//div[@role='dialog']//div[contains(@aria-label, 'Fechar')] | //div[@role='dialog']//button").click()
            except:
                driver.get(f"https://www.instagram.com/{perfil_alvo}/")
            time.sleep(1)
        except Exception as e:
            logging.error(f"   ❌ Falha ao processar o post {post_url}. Erro: {e}")
            continue

    logging.info(f"✅ Finalizada a coleta do perfil {perfil_alvo}! Dados salvos em {arquivo_saida_curtidas}")
    # Não retorna mais os dados, pois já foram salvos incrementalmente
    return None

# --- FLUXO PRINCIPAL DE EXECUÇÃO ---
if __name__ == "__main__":
    driver = None
    try:
        options = Options()
        options.add_argument("--start-maximized")
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        wait = WebDriverWait(driver, 2)
        
        if perform_login(driver, wait, INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD):
            logging.info(f"\n🚀 Iniciando coleta sequencial de {len(PERFIS_ALVO)} perfis...")
            
            for i, perfil_atual in enumerate(PERFIS_ALVO, 1):
                logging.info(f"\n📊 === PERFIL {i}/{len(PERFIS_ALVO)}: @{perfil_atual} ===")
                
                try:
                    coletar_curtidas_de_posts(driver, wait, perfil_atual, MAX_POSTS_PARA_ANALISAR, MAX_CURTIDAS_POR_POST)
                    logging.info(f"✅ Perfil @{perfil_atual} concluído com sucesso!")
                    
                    # Pausa entre perfis para evitar sobrecarga
                    if i < len(PERFIS_ALVO):
                        logging.info("⏳ Aguardando 10 segundos antes do próximo perfil...")
                        time.sleep(10)
                        
                except Exception as e:
                    logging.error(f"❌ Erro ao processar perfil @{perfil_atual}: {e}")
                    logging.info("➡️ Continuando para o próximo perfil...")
                    continue
            
            logging.info(f"\n🎉 PROCESSO COMPLETAMENTE FINALIZADO! Todos os {len(PERFIS_ALVO)} perfis foram processados.")

    except Exception as final_e:
        logging.critical(f"❌ Um erro inesperado ocorreu no fluxo principal: {final_e}")
    finally:
        if driver:
            driver.quit()
            logging.info("Navegador fechado.")