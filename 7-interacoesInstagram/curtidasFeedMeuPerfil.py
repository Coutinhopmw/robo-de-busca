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
# 1. Defina o número máximo de posts que você quer curtir nesta sessão.
#    (Recomendação: comece com um valor baixo, como 15 ou 20)
MAX_CURTIDAS_SESSAO = 15

# 2. Defina o intervalo de tempo (em segundos) para a pausa entre as curtidas.
#    (Recomendação de segurança: MÍNIMO de 30 segundos)
PAUSA_MINIMA_ENTRE_CURTIDAS = 30
PAUSA_MAXIMA_ENTRE_CURTIDAS = 90
# =======================================================================================


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
        # Lida com pop-ups pós-login
        for _ in range(2):
            try:
                WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, "//*[text()='Agora não' or text()='Not Now' or text()='Dispensar']"))).click()
                logging.info("Pop-up de notificação/salvamento fechado.")
            except: pass
    except Exception as e:
        logging.error(f"❌ Erro inesperado durante o login: {e}")
        return False
    return True

def curtir_posts_do_feed(driver, wait):
    """Rola o feed e curte as postagens que ainda não foram curtidas."""
    logging.info("❤️ Iniciando processo de curtidas no feed...")
    curtidas_nesta_sessao = 0
    posts_processados = set() # Guarda os links dos posts já vistos para não reprocessar

    # Loop principal: continua até atingir o limite de curtidas
    while curtidas_nesta_sessao < MAX_CURTIDAS_SESSAO:
        try:
            # Encontra todos os artigos (posts) visíveis na tela
            # A tag <article> é um bom identificador para um post no feed
            posts_visiveis = wait.until(EC.presence_of_all_elements_located((By.TAG_NAME, "article")))
            
            if not posts_visiveis:
                logging.warning("Nenhum post encontrado na tela. Verificando...")
                time.sleep(5)
                continue

            for post in posts_visiveis:
                # Pega o link do post como um identificador único
                try:
                    link_post = post.find_element(By.XPATH, ".//a[contains(@href, '/p/')]").get_attribute('href')
                    if link_post in posts_processados:
                        continue # Pula se já vimos este post
                except:
                    continue # Se não conseguir ID, pula o post

                # A LÓGICA PRINCIPAL: Tenta encontrar o botão de "Curtir" (coração não preenchido)
                try:
                    # O seletor procura pelo SVG com o aria-label específico de "Curtir"
                    botao_curtir = post.find_element(By.XPATH, ".//svg[@aria-label='Curtir']")
                    
                    # Se encontrou o botão, significa que o post ainda não foi curtido
                    botao_curtir.click()
                    curtidas_nesta_sessao += 1
                    logging.info(f"   ❤️ Post curtido! ({curtidas_nesta_sessao}/{MAX_CURTIDAS_SESSAO})")

                    # Pausa de segurança longa e aleatória APÓS curtir
                    pausa = random.uniform(PAUSA_MINIMA_ENTRE_CURTIDAS, PAUSA_MAXIMA_ENTRE_CURTIDAS)
                    logging.info(f"   ⏸️ Pausando por {pausa:.1f} segundos...")
                    time.sleep(pausa)

                except NoSuchElementException:
                    # Se não encontrou o botão "Curtir", significa que o post já foi curtido (o botão agora é "Descurtir")
                    # ou é um anúncio sem o botão padrão. Em ambos os casos, apenas ignoramos.
                    pass
                
                finally:
                    # Marca o post como processado para não tentar de novo
                    posts_processados.add(link_post)

                # Verifica se já atingiu o limite da sessão
                if curtidas_nesta_sessao >= MAX_CURTIDAS_SESSAO:
                    break
            
            # Se o loop de posts terminou e ainda não atingimos o limite, rola a página
            if curtidas_nesta_sessao < MAX_CURTIDAS_SESSAO:
                logging.info("   ⏬ Rolando o feed para encontrar novos posts...")
                driver.execute_script("window.scrollBy(0, window.innerHeight * 1.5);") # Rola 1.5x a altura da tela
                time.sleep(3) # Pausa para o conteúdo carregar

        except TimeoutException:
            logging.warning("Não foram encontrados novos posts para carregar. Encerrando a rolagem.")
            break
        except Exception as e:
            logging.error(f"❌ Um erro ocorreu durante a rolagem/curtida: {e}")
            break
            
    return curtidas_nesta_sessao

# --- FLUXO PRINCIPAL ---
if __name__ == "__main__":
    driver = None
    try:
        options = Options()
        options.add_argument("--start-maximized")
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        wait = WebDriverWait(driver, 10) # Wait mais curto, pois o feed carrega rápido
        
        if perform_login(driver, wait, INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD):
            curtidas_feitas = curtir_posts_do_feed(driver, wait)
            logging.info(f"\n🎉 Processo concluído! {curtidas_feitas} post(s) foram curtidos nesta sessão.")

    except Exception as final_e:
        logging.critical(f"❌ Um erro inesperado ocorreu no fluxo principal: {final_e}")
    finally:
        if driver:
            driver.quit()
            logging.info("Navegador fechado.")