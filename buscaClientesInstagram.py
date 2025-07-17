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
from webdriver_manager.chrome import ChromeDriverManager

# --- CONFIGURAÇÕES ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

INSTAGRAM_USERNAME = "antoniocassiorodrigueslima"
INSTAGRAM_PASSWORD = "Lc181340sl@?"

PALAVRAS_CHAVE = [
    "salão de beleza",
    "salão de estética",
    "salão de cabeleireiro",
    "salão feminino",
    "salão masculino",
    "barbearia",
    "nail designer",
    "espaço de beleza",
    "espaço estético",
    "centro de estética",
    "clínica de estética",
    "studio de beleza",
    "studio de sobrancelhas",
    "studio de maquiagem",
    "spa de beleza",
    "spa urbano",
    "salão de unhas",
    "ateliê de beleza",
    "espaço de autocuidado",
    "estúdio de beleza"
]



ARQUIVO_SAIDA = os.path.join("buscaClientesInstagram", "perfis_comerciais_encontrados.csv")


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
            # Lida com pop-ups de "Salvar informações" ou "Ativar notificações"
            WebDriverWait(driver, 7).until(
                EC.element_to_be_clickable((By.XPATH, "//*[text()='Agora não' or text()='Not Now']"))
            ).click()
            logging.info("Pop-up 'Agora não' fechado.")
        except: pass
    except Exception as e:
        logging.error(f"❌ Erro inesperado durante o login: {e}")
        return False
    return True

def buscar_e_coletar_perfis(driver, wait, keywords):
    """Pede ajuda para o clique inicial e depois busca e coleta os perfis."""
    perfis_encontrados = {}
    
    # ========================== INTERAÇÃO MANUAL NECESSÁRIA ==========================
    input("\n" + "="*60 +
          "\n   AÇÃO NECESSÁRIA: Por favor, clique no ícone de 'Pesquisa' (a lupa) na\n" +
          "   janela do navegador que foi aberta.\n\n" +
          "   Após o painel de busca aparecer, volte aqui e pressione ENTER para continuar...\n" +
          "="*60 + "\n")
    logging.info("✅ Interação manual recebida. Assumindo o controle...")
    # ===============================================================================

    # Seletor para a linha de resultado (baseado na sua última captura bem-sucedida)
    SELETOR_LINHA_RESULTADO = (By.XPATH, "//a[contains(@class, '_a6hd')]")

    # Cria o arquivo CSV e escreve o cabeçalho se não existir
    if not os.path.exists(ARQUIVO_SAIDA):
        import csv
        with open(ARQUIVO_SAIDA, mode='w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["username", "nome_completo", "subtitulo", "palavra_chave_origem"])

    for keyword in keywords:
        logging.info(f"\n🔎 Buscando pela palavra-chave: '{keyword}'")
        try:
            # A caixa de busca já deve estar visível após o clique manual
            search_box = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@aria-label='Entrada da pesquisa']")))
            search_box.send_keys(Keys.CONTROL + "a")
            search_box.send_keys(Keys.DELETE)
            time.sleep(1)
            search_box.send_keys(keyword)
            
            logging.info("⏳ Aguardando resultados...")
            time.sleep(5)

            resultados = wait.until(EC.presence_of_all_elements_located(SELETOR_LINHA_RESULTADO))
            logging.info(f"   ✅ Encontrados {len(resultados)} resultados para '{keyword}'.")

            for resultado in resultados:
                try:
                    href = resultado.get_attribute('href')
                    username = href.strip('/').split('/')[-1]

                    if username in perfis_encontrados: continue

                    spans = resultado.find_elements(By.TAG_NAME, 'span')
                    textos = [s.text.strip() for s in spans if s.text.strip()]
                    
                    nome_completo = textos[0] if textos else ""
                    subtitulo = textos[1] if len(textos) > 1 else ""
                    
                    if username and nome_completo:
                        perfis_encontrados[username] = {
                            "nome_completo": nome_completo,
                            "subtitulo": subtitulo,
                            "palavra_chave_origem": keyword
                        }
                        logging.info(f"      -> Coletado: {username} ({nome_completo})")

                        # Salva imediatamente no CSV
                        import csv
                        with open(ARQUIVO_SAIDA, mode='a', encoding='utf-8', newline='') as f:
                            writer = csv.writer(f)
                            writer.writerow([username, nome_completo, subtitulo, keyword])

                except Exception: continue
            
            pausa = random.uniform(3, 7)
            logging.info(f"   ⏸️ Pausando por {pausa:.1f} segundos antes da próxima busca...")
            time.sleep(pausa)

        except Exception as e:
            logging.error(f"❌ Falha ao processar a palavra-chave '{keyword}'. Erro: {e}")
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
                logging.info(f"\n✅ SUCESSO! {len(perfis)} perfis únicos foram encontrados e salvos em '{ARQUIVO_SAIDA}'")
            else:
                logging.info("\n⚠️ Nenhum perfil foi encontrado para as palavras-chave fornecidas.")

    except Exception as final_e:
        logging.critical(f"❌ Um erro inesperado ocorreu no fluxo principal: {final_e}")
    finally:
        if driver:
            driver.quit()
            logging.info("Navegador fechado.")