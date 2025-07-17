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
import logging # Importa o módulo de logging

# Configuração de logging para melhor depuração
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# CONFIGURAÇÕES
# As credenciais são mantidas diretamente no código, conforme solicitado.
INSTAGRAM_USERNAME = "antoniocassiorodrigueslima"
INSTAGRAM_PASSWORD = "Lc181340sl@?"
PERFIL_ALVO = "solaracquapark"
LIMITE_SEGUIDORES = float('inf') # Define float('inf') para coletar todos
ARQUIVO_SAIDA_SEGUIDORES = f"seguidores_{PERFIL_ALVO}.csv"
ARQUIVO_SAIDA_CURTIDAS = f"curtidas_{PERFIL_ALVO}.csv"

# INICIALIZA O NAVEGADOR
options = Options()
options.add_argument("--start-maximized")
# Adiciona argumento para silenciar mensagens de log do Chrome
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
    logging.info(f"URL atual após get: {driver.current_url}")

    try:
        # Aguarda a presença dos campos de usuário e senha
        wait.until(EC.presence_of_element_located((By.NAME, "username")))
        username_input = driver.find_element(By.NAME, "username")
        password_input = driver.find_element(By.NAME, "password")

        username_input.send_keys(username)
        password_input.send_keys(password)
        password_input.send_keys(Keys.RETURN)
        logging.info("Credenciais enviadas.")

        # Aguarda a URL mudar para a página principal ou um elemento indicativo de login bem-sucedido
        wait.until(EC.url_contains("instagram.com"))
        logging.info("✅ Login realizado com sucesso (URL principal alcançada).")

    except TimeoutException:
        logging.error("❌ Timeout: O campo de usuário não apareceu ou o login demorou demais.")
        with open("login_debug.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        return False
    except Exception as e:
        logging.error(f"❌ Erro inesperado durante o login: {e}")
        with open("login_debug.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        return False

    # Verificação de segurança (2FA)
    try:
        # Tenta encontrar o campo de código de segurança por um curto período
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.NAME, "security_code")))
        logging.warning("🔐 Instagram solicitou verificação de dois fatores.")
        input("👉 Digite o código no navegador e pressione ENTER aqui quando tiver confirmado.")
        # Após o usuário interagir, aguarda a página carregar novamente
        wait.until(EC.url_contains("instagram.com")) # Espera a URL principal novamente
        logging.info("Verificação de segurança concluída manualmente.")
    except TimeoutException:
        logging.info("✅ Login realizado sem verificação adicional.")
    except Exception as e:
        logging.warning(f"Erro inesperado ao verificar 2FA: {e}")
    return True

# Função para fechar popups
def fechar_popups_instagram(driver, wait):
    logging.info("Tentando fechar popups do Instagram...")
    popups_fechados = False
    # Tenta fechar o popup "Salvar informações de login?" e "Ativar Notificações"
    # Ambos frequentemente usam o texto "Agora não" ou "Not Now"
    try:
        # Use presence_of_all_elements_located para encontrar todos os botões e evitar NoSuchElementException imediato
        # Defina um timeout menor, pois popups podem não aparecer
        btns = wait.until(EC.presence_of_all_elements_located(
            (By.XPATH, "//button[contains(text(), 'Agora não') or contains(text(), 'Not Now')]")
        ))
        for btn in btns:
            try:
                if btn.is_displayed() and btn.is_enabled():
                    btn.click()
                    logging.info("  Botão 'Agora não'/'Not Now' clicado.")
                    time.sleep(1) # Pequena pausa para o popup fechar
                    popups_fechados = True
            except StaleElementReferenceException:
                logging.warning("  Elemento de popup ficou obsoleto, tentando próximo ou ignorando.")
                continue
            except Exception as e:
                logging.warning(f"  Erro ao clicar em botão de popup: {e}")
    except TimeoutException:
        logging.info("  Nenhum popup 'Agora não'/'Not Now' encontrado (timeout).")
    except Exception as e:
        logging.error(f"Erro geral ao tentar fechar popups: {e}")

    # Tenta fechar banner de cookies (geralmente texto "Aceitar" ou "Accept")
    try:
        # Use presence_of_all_elements_located
        cookies_btns = wait.until(EC.presence_of_all_elements_located(
            (By.XPATH, "//button[contains(text(), 'Aceitar') or contains(text(), 'Accept')]")
        ))
        for btn in cookies_btns:
            try:
                if btn.is_displayed() and btn.is_enabled():
                    btn.click()
                    logging.info("  Botão 'Aceitar' cookies clicado.")
                    time.sleep(1)
                    popups_fechados = True
            except StaleElementReferenceException:
                logging.warning("  Elemento de cookie ficou obsoleto, tentando próximo ou ignorando.")
                continue
            except Exception as e:
                logging.warning(f"  Erro ao clicar em botão de cookies: {e}")
    except TimeoutException:
        logging.info("  Nenhum popup de cookies encontrado (timeout).")
    except Exception as e:
        logging.error(f"Erro geral ao tentar fechar cookies: {e}")

    if popups_fechados:
        logging.info("✅ Popups de Instagram e/ou cookies tentados e fechados.")
    else:
        logging.info("ℹ️ Nenhum popup aparente para fechar.")


def garantir_perfil_alvo(driver, wait, perfil_alvo, tentativas=5):
    url_perfil = f"https://www.instagram.com/{perfil_alvo}/"
    for i in range(tentativas):
        logging.info(f"Navegando para o perfil {perfil_alvo} (tentativa {i+1}/{tentativas})...")
        driver.get(url_perfil)
        time.sleep(3) # Pequena pausa para a página começar a carregar
        fechar_popups_instagram(driver, wait)

        try:
            # Aguarda o elemento header do perfil para confirmar o carregamento
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "header")))
            # Confirma se a URL contém o perfil correto (Instagram pode redirecionar)
            if perfil_alvo in driver.current_url:
                logging.info(f"✅ Perfil {perfil_alvo} acessado com sucesso.")
                return True
        except TimeoutException:
            logging.warning(f"Timeout ao carregar o cabeçalho do perfil {perfil_alvo}.")
        except Exception as e:
            logging.warning(f"Erro ao verificar o perfil {perfil_alvo}: {e}")
    logging.error(f"❌ Não foi possível acessar o perfil {perfil_alvo} após {tentativas} tentativas. URL atual: {driver.current_url}")
    return False

# === FUNÇÃO: COLETAR CURTIDAS DOS POSTS ===
def coletar_curtidas_posts(driver, wait, perfil_alvo):
    logging.info("\n🔎 Coletando curtidas dos posts...")
    url_perfil = f"https://www.instagram.com/{perfil_alvo}/"
    driver.get(url_perfil)
    time.sleep(2)

    post_links = set()
    max_posts = 120
    max_scrolls = 30  # Limite de rolagens para evitar loop infinito
    last_height = driver.execute_script("return document.body.scrollHeight")
    scroll_count = 0

    # 1. Coletar até 120 links de posts
    while len(post_links) < max_posts and scroll_count < max_scrolls:
        posts = driver.find_elements(By.XPATH, "//a[contains(@href, '/p/')]")
        for post in posts:
            href = post.get_attribute('href')
            if href and '/p/' in href:
                if href.startswith('/'):
                    href_abs = f'https://www.instagram.com{href}'
                else:
                    href_abs = href
                if href_abs not in post_links:
                    post_links.add(href_abs)
                    if len(post_links) >= max_posts:
                        break
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            scroll_count += 1
        else:
            scroll_count = 0
        last_height = new_height

    logging.info(f"Total de links de post coletados: {len(post_links)} (limite: {max_posts})")
    if not post_links:
        logging.warning(f"❌ Nenhum post encontrado após rolar a página para o perfil {perfil_alvo}.")
        return

    # 2. Processar cada post coletado
    curtidas_data = []
    for idx, post_url in enumerate(list(post_links)):
        try:
            logging.info(f"\n➡️ Abrindo post {idx+1}/{len(post_links)}: {post_url}")
            driver.get(post_url)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "time")))
            time.sleep(1)

            data_post = ""
            try:
                time_elem = driver.find_element(By.TAG_NAME, "time")
                data_post = time_elem.get_attribute("datetime")
                logging.info(f"  Data do post: {data_post}")
            except NoSuchElementException:
                logging.warning("  ⚠️ Não foi possível obter a data do post.")
            except Exception as e:
                logging.warning(f"  Erro ao obter a data do post: {e}")

            # Botão de curtidas: tenta encontrar por vários seletores
            like_btn = None
            like_btn_selectors = [
                (By.XPATH, "//a[contains(@href, '/liked_by/') or contains(text(), 'curtidas') or contains(text(), 'likes') or contains(text(), 'visualizar curtidas') or contains(text(), 'Ver curtidas') or contains(text(), 'Ver likes') or contains(text(), 'others') or contains(text(), 'outras pessoas') or contains(text(), 'pessoas') or contains(text(), 'like') or contains(text(), 'Curtidas') or contains(text(), 'Likes')]"),
                (By.XPATH, "//span[contains(text(), 'curtidas') or contains(text(), 'likes') or contains(@aria-label, 'curtidas') or contains(@aria-label, 'likes')]") ,
                (By.CSS_SELECTOR, 'span.x193iq5w.xeuugli.x1fj9vlw.x13faqbe.x1vvkbs.xt0psk2.x1i0vuye.xvs91rp.x1s688f.x5n08af.x10wh9bi.xpm28yp.x8viiok.x1o7cslx'),
            ]
            for by, selector in like_btn_selectors:
                try:
                    like_btn = wait.until(EC.element_to_be_clickable((by, selector)))
                    logging.info(f"  ✅ Botão de curtidas encontrado e clicável pelo seletor: {by} {selector}")
                    break
                except TimeoutException:
                    logging.info(f"  ⚠️ Timeout ao encontrar botão de curtidas com: {by} {selector}")
                except Exception as e:
                    logging.warning(f"  ⚠️ Erro ao procurar botão de curtidas com {by} {selector}: {e}")
            if not like_btn:
                logging.warning(f"  ❌ Não foi possível encontrar nenhum botão de curtidas para o post: {post_url}")
                continue
            try:
                like_btn.click()
                logging.info("  ✅ Botão de curtidas clicado.")
            except Exception as e:
                logging.error(f"  ❌ Não foi possível clicar no botão de curtidas: {e}")
                continue
            time.sleep(2)

            usuarios_curtaram_por_post = set()
            try:
                logging.info("  Procurando container de curtidas (modal)...")
                dialog = wait.until(EC.presence_of_element_located((By.XPATH, "//div[@role='dialog']")))
                scroll_container = None
                possible_containers = [
                    By.CSS_SELECTOR, 'div.x6nl9eh.x1a5l9x9.x7vuprf.x1mg3h75.x1lliihq.x1iyjqo2.xs83m0k.xz65tgg.x1rife3k.x1n2onr6',
                    By.XPATH, ".//div[contains(@style, 'overflow-y: scroll')]",
                    By.XPATH, ".//ul",
                    By.XPATH, ".//div[@tabindex='0' or @tabindex='-1']",
                ]
                for i in range(0, len(possible_containers), 2):
                    by_method = possible_containers[i]
                    selector_value = possible_containers[i+1]
                    try:
                        scroll_container = dialog.find_element(by_method, selector_value)
                        logging.info(f"  ✅ Container de curtidas encontrado: {selector_value}")
                        break
                    except NoSuchElementException:
                        logging.debug(f"  Não encontrou container com {selector_value}.")
                        continue
                    except Exception as e:
                        logging.warning(f"  Erro ao buscar container com {selector_value}: {e}")
                        continue
                if not scroll_container:
                    logging.error("  ❌ Não foi possível encontrar o container rolável de curtidas dentro do modal.")
                    continue
            except TimeoutException:
                logging.error(f"  ❌ Timeout: O modal de curtidas não apareceu para o post: {post_url}.")
                continue
            except Exception as e:
                logging.error(f"  ❌ Erro ao encontrar modal ou lista de curtidas para: {post_url} - {e}")
                continue

            scrolls_likes = 0
            max_scrolls_likes = 200
            tentativas_sem_novos = 0
            max_tentativas_sem_novos = 5
            total_usuarios_antes = 0
            while scrolls_likes < max_scrolls_likes and tentativas_sem_novos < max_tentativas_sem_novos:
                try:
                    driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scroll_container)
                    time.sleep(1.5)
                except StaleElementReferenceException:
                    logging.warning("  Elemento de scroll de curtidas ficou obsoleto, tentando recarregar o container.")
                    try:
                        dialog = wait.until(EC.presence_of_element_located((By.XPATH, "//div[@role='dialog']")))
                        scroll_container = dialog.find_element(by_method, selector_value)
                        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scroll_container)
                        time.sleep(1.5)
                    except Exception as e_reacquire:
                        logging.error(f"  Falha ao recarregar o container de scroll após StaleElementReferenceException: {e_reacquire}")
                        break
                except Exception as e:
                    logging.error(f"  Erro durante o scroll das curtidas: {e}")
                    break
                links_likes = scroll_container.find_elements(By.XPATH, ".//a[contains(@href, '.com/') and not(contains(@href, '/p/'))]")
                total_usuarios = len(links_likes)
                if total_usuarios > total_usuarios_antes:
                    tentativas_sem_novos = 0
                    total_usuarios_antes = total_usuarios
                else:
                    tentativas_sem_novos += 1
                    logging.info(f"  ↕️ Nenhum novo usuário nesta rolagem. ({tentativas_sem_novos}/{max_tentativas_sem_novos})")
                scrolls_likes += 1
            links_likes = scroll_container.find_elements(By.XPATH, ".//a[contains(@href, '.com/') and not(contains(@href, '/p/'))]")
            for link in links_likes:
                try:
                    href = link.get_attribute("href")
                    if href and href.startswith("https://www.instagram.com/"):
                        path_parts = href.strip('/').split('/')
                        if len(path_parts) >= 2 and path_parts[-2] == "com":
                            username = path_parts[-1]
                        else:
                            username = path_parts[-1]
                        if username and username not in usuarios_curtaram_por_post and username != perfil_alvo:
                            usuarios_curtaram_por_post.add(username)
                            curtidas_data.append({
                                "data_post": data_post,
                                "username": username,
                                "post_url": post_url
                            })
                except StaleElementReferenceException:
                    logging.warning("  Elemento de link de curtida ficou obsoleto durante a extração.")
                    continue
                except Exception as e:
                    logging.warning(f"  Erro ao processar link de curtida: {e}")
            logging.info(f"  👍 {len(usuarios_curtaram_por_post)} curtidas únicas coletadas para este post.")
            try:
                close_btn = wait.until(EC.element_to_be_clickable((By.XPATH, '//div[@role="dialog"]//button[@aria-label="Fechar" or contains(text(), "Fechar") or contains(text(), "Close")]')))
                close_btn.click()
                logging.info("  Modal de curtidas fechado.")
            except TimeoutException:
                logging.warning("  Timeout ao tentar fechar o modal de curtidas.")
            except Exception as e:
                logging.warning(f"  Erro ao tentar fechar o modal de curtidas: {e}")
            time.sleep(1)
        except Exception as e:
            logging.error(f"❌ Erro geral ao processar o post {post_url}: {e}")
            try:
                close_btn = driver.find_element(By.XPATH, '//div[@role="dialog"]//button[@aria-label="Fechar" or contains(text(), "Fechar") or contains(text(), "Close")]')
                if close_btn.is_displayed():
                    close_btn.click()
                    logging.info("  Modal fechado após erro.")
                    time.sleep(1)
            except:
                pass
            continue

    if curtidas_data:
        df_curtidas = pd.DataFrame(curtidas_data)
        df_curtidas.to_csv(ARQUIVO_SAIDA_CURTIDAS, index=False, encoding='utf-8')
        logging.info(f"\n✅ Curtidas salvas em {ARQUIVO_SAIDA_CURTIDAS}\n")
    else:
        logging.info("\n⚠️ Nenhuma curtida coletada em nenhum post.")

# === FIM DA FUNÇÃO DE COLETAR CURTIDAS ===

# === FUNÇÃO: COLETAR SEGUIDORES ===
def coletar_seguidores(driver, wait, perfil_alvo, limite_seguidores, arquivo_saida):
    logging.info("📥 Coletando seguidores em tempo real...")
    seguidores = {}
    scrolls_sem_novos = 0
    scroll_limit = 30 # Limite de scrolls sem novos usuários para parar

    try:
        # Tenta encontrar e clicar no botão de "Seguidores"
        logging.info("🔍 Procurando botão de 'seguidores'...")
        seguidores_btn = wait.until(EC.presence_of_element_located(
            (By.XPATH, f"//a[contains(@href, '/{perfil_alvo}/followers/') or contains(@href, '/followers/')]")))
        seguidores_btn.click()
        logging.info("✅ Botão de seguidores clicado.")
    except TimeoutException:
        logging.error(f"❌ Timeout: Não foi possível encontrar o botão de seguidores para o perfil {perfil_alvo}.")
        return {}
    except Exception as e:
        logging.error(f"❌ Erro ao clicar no botão de seguidores: {e}")
        return {}

    # Aguarda a janela/modal de seguidores carregar
    logging.info("⏳ Aguardando carregamento da janela de seguidores...")
    try:
        dialog = wait.until(EC.presence_of_element_located((By.XPATH, "//div[@role='dialog']")))
        logging.info("✅ Janela de seguidores carregada.")
    except TimeoutException:
        logging.error("❌ Timeout: Falha ao carregar a janela de seguidores.")
        return {}
    except Exception as e:
        logging.error(f"❌ Erro ao carregar a janela de seguidores: {e}")
        return {}

    # Encontra o container rolável dentro do modal
    scroll_container = None
    possible_containers = [
        By.CSS_SELECTOR, 'div.x6nl9eh.x1a5l9x9.x7vuprf.x1mg3h75.x1lliihq.x1iyjqo2.xs83m0k.xz65tgg.x1rife3k.x1n2onr6', # Classe comum para modais roláveis do Instagram
        By.XPATH, ".//div[contains(@style, 'overflow-y: scroll')]", # Genérico, mas pode funcionar
        By.XPATH, ".//ul", # Às vezes, a lista está dentro de um UL
        By.XPATH, ".//div[@tabindex='0' or @tabindex='-1']", # Outros elementos com tabindex que podem ser roláveis
    ]

    for i in range(0, len(possible_containers), 2):
        by_method = possible_containers[i]
        selector_value = possible_containers[i+1]
        try:
            scroll_container = dialog.find_element(by_method, selector_value)
            logging.info(f"  ✅ Container rolável de seguidores encontrado: {selector_value}")
            break
        except NoSuchElementException:
            logging.debug(f"  Não encontrou container com {selector_value}.")
            continue
        except Exception as e:
            logging.warning(f"  Erro ao buscar container rolável com {selector_value}: {e}")
            continue

    if not scroll_container:
        logging.error("  ❌ Não foi possível encontrar o container rolável de seguidores dentro do modal.")
        return {}

    while len(seguidores) < limite_seguidores and scrolls_sem_novos < scroll_limit:
        try:
            qtd_antes = len(seguidores)

            # Scroll no container
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scroll_container)
            time.sleep(2) # Espera para carregar novos elementos

            novos = 0
            # Coleta todos os links de perfis visíveis no container
            # Usar um seletor mais robusto para os links de perfil dentro do modal
            links_depois = scroll_container.find_elements(By.XPATH, ".//a[contains(@href, '.com/') and not(contains(@href, '/p/'))]")
            
            for link in links_depois:
                try:
                    href = link.get_attribute("href")
                    if href and href.startswith("https://www.instagram.com/"):
                        # Extrai o username da URL
                        username_parts = href.strip('/').split('/')
                        username = username_parts[-1] if len(username_parts) > 1 else "" # Pega o último segmento
                        
                        # Tenta capturar o nome completo, se disponível
                        nome_completo = ""
                        try:
                            # A lógica de parent pode precisar de ajuste se o HTML mudar.
                            # Tenta encontrar um span com o nome completo próximo ao link.
                            # Esta é uma estimativa e pode precisar de ajuste.
                            # Por exemplo, procurar por um span que não seja o username
                            # e esteja na mesma "linha" visual do usuário.
                            # Este XPath é um chute, pode ser que você precise de um mais específico.
                            full_name_element = link.find_element(By.XPATH, "./following-sibling::div//span[not(@class) or contains(@class, 'x1lliihq')]")
                            nome_completo = full_name_element.text
                        except NoSuchElementException:
                            pass # Não encontrou nome completo, sem problemas
                        except Exception as e:
                            logging.debug(f"Erro ao tentar obter nome completo para {username}: {e}")

                        if username and username not in seguidores and username != perfil_alvo:
                            seguidores[username] = nome_completo
                            novos += 1
                            logging.info(f"{len(seguidores)}: {username} - {nome_completo}")
                            
                            # Condição de saída antecipada se o limite for atingido
                            if len(seguidores) >= limite_seguidores:
                                logging.info(f"✅ Limite de {limite_seguidores} seguidores atingido.")
                                break # Sai do loop for links_depois
                except StaleElementReferenceException:
                    logging.warning("  Elemento de link de seguidor ficou obsoleto durante a extração.")
                    continue
                except Exception as e:
                    logging.warning(f"  Erro ao processar link de seguidor: {e}")
                    continue

            # Verifica se novos usuários foram encontrados nesta rolagem
            if novos == 0:
                scrolls_sem_novos += 1
                logging.info(f"↕️ Nenhum novo usuário. Tentativa de scroll {scrolls_sem_novos}/{scroll_limit}")
            else:
                scrolls_sem_novos = 0 # Reseta o contador se novos usuários forem encontrados

            # Se o limite for atingido, quebra o loop principal também
            if len(seguidores) >= limite_seguidores:
                break

        except StaleElementReferenceException:
            logging.warning("♻️ Elemento desatualizado, tentando novamente...")
            time.sleep(2)
            # Tentar reencontrar o dialog e scroll_container aqui se necessário
            try:
                dialog = wait.until(EC.presence_of_element_located((By.XPATH, "//div[@role='dialog']")))
                scroll_container = dialog.find_element(by_method, selector_value) # Tenta usar o último seletor de container bem-sucedido
            except Exception as e_reacquire:
                logging.error(f"Falha ao recarregar o container de seguidores após StaleElementReferenceException: {e_reacquire}")
                break # Sai do loop se não conseguir recarregar
            continue
        except TimeoutException as e:
            logging.error(f"⚠️ Timeout ao tentar encontrar elementos durante a coleta de seguidores: {e}")
            break
        except Exception as e:
            logging.error(f"⚠️ Erro inesperado durante a coleta de seguidores: {e}")
            break
    
    # Após o loop de coleta, fecha o modal de seguidores
    try:
        close_btn = wait.until(EC.element_to_be_clickable((By.XPATH, '//div[@role="dialog"]//button[@aria-label="Fechar" or contains(text(), "Fechar") or contains(text(), "Close")]')))
        close_btn.click()
        logging.info("Modal de seguidores fechado.")
    except TimeoutException:
        logging.warning("Timeout ao tentar fechar o modal de seguidores.")
    except Exception as e:
        logging.warning(f"Erro ao tentar fechar o modal de seguidores: {e}")

    return seguidores

# === FIM DA FUNÇÃO DE COLETAR SEGUIDORES ===

# ==============================================================================
# FLUXO PRINCIPAL DO SCRIPT
# ==============================================================================
if __name__ == "__main__":
    try:
        # 1. Realizar login
        if not perform_login(driver, wait, INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD):
            logging.error("O login falhou. Encerrando o script.")
            driver.quit()
            exit()

        # 2. Garantir acesso ao perfil alvo antes de coletar curtidas
        if not garantir_perfil_alvo(driver, wait, PERFIL_ALVO):
            logging.error(f"Não foi possível acessar o perfil alvo ({PERFIL_ALVO}). Encerrando o script.")
            driver.quit()
            exit()

        # 3. Coletar curtidas dos posts
        coletar_curtidas_posts(driver, wait, PERFIL_ALVO)
        
        # 4. Garantir acesso ao perfil alvo novamente antes de coletar seguidores
        # Isso é importante porque a coleta de curtidas navega para URLs de posts.
        if not garantir_perfil_alvo(driver, wait, PERFIL_ALVO):
            logging.error(f"Não foi possível acessar o perfil alvo ({PERFIL_ALVO}) para coletar seguidores. Encerrando o script.")
            driver.quit()
            exit()

        # 5. Coletar seguidores
        todos_seguidores = coletar_seguidores(driver, wait, PERFIL_ALVO, LIMITE_SEGUIDORES, ARQUIVO_SAIDA_SEGUIDORES)

        # 6. Salvar seguidores (uma única vez no final)
        if todos_seguidores:
            df_seguidores = pd.DataFrame(list(todos_seguidores.items()), columns=["username", "nome_completo"])
            df_seguidores.to_csv(ARQUIVO_SAIDA_SEGUIDORES, index=False, encoding='utf-8')
            logging.info(f"\n✅ {len(todos_seguidores)} seguidores salvos em {ARQUIVO_SAIDA_SEGUIDORES}")
        else:
            logging.info("\n⚠️ Nenhum seguidor coletado para salvar.")

    except Exception as final_e:
        logging.critical(f"❌ Um erro inesperado ocorreu no fluxo principal do script: {final_e}")
    finally:
        # Garante que o navegador seja fechado em qualquer caso
        if driver:
            driver.quit()
            logging.info("Navegador fechado.")

