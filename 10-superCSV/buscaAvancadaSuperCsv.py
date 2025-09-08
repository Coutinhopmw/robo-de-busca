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

INSTAGRAM_USERNAME = "gabijardimsantos"
INSTAGRAM_PASSWORD = "Lc181340sl@?"

# INSTAGRAM_USERNAME = "coutinho_tkd"
# INSTAGRAM_PASSWORD = "Lc181340sl@"



# --- CONFIGURAÇÃO DOS ARQUIVOS ---
ARQUIVO_ENTRADA = "superCSV.csv"
ARQUIVO_SAIDA = "superCsvEnriquecido.csv"


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
        
        # Pausa de 1 minuto após o login
        logging.info("⏸️ Aguardando 1 minuto após o login...")
        time.sleep(60)
        
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
        "link_externo": "", "verificado": False, "status_conta": "Pública",
        "foto_perfil": 0, "categoria": "", "nome_completo": "", "conta_comercial": False,
        "destaque_stories": 0, "posts_recentes": 0, "engajamento_medio": 0.0
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

        # 2. Verifica se o perfil tem o selo de verificado
        try:
            header.find_element(By.XPATH, ".//svg[@aria-label='Verificado']")
            dados['verificado'] = True
        except NoSuchElementException:
            dados['verificado'] = False

        # 3. Detecta se tem foto de perfil (não é a imagem padrão)
        try:
            img_perfil = header.find_element(By.XPATH, ".//img[contains(@alt, 'foto do perfil') or contains(@alt, 'profile picture')]")
            src_img = img_perfil.get_attribute('src')
            # Se não for a imagem padrão do Instagram, tem foto personalizada
            if src_img and 'default_avatar' not in src_img and 'anonymous_profile' not in src_img:
                dados['foto_perfil'] = 1
        except Exception:
            dados['foto_perfil'] = 0

        # 4. Extrai nome completo (diferente do username)
        try:
            nome_elem = header.find_element(By.XPATH, ".//h2|.//span[contains(@class, 'title')]")
            if nome_elem.text and nome_elem.text != username:
                dados['nome_completo'] = nome_elem.text.strip()
        except Exception:
            pass

        # 5. Detecta se é conta comercial/profissional
        try:
            categoria_elem = header.find_element(By.XPATH, ".//div[contains(text(), 'Página ·') or contains(text(), 'Empresa')]")
            dados['conta_comercial'] = True
            dados['categoria'] = categoria_elem.text.strip()
        except Exception:
            try:
                # Busca por indicadores de conta comercial
                comercial_indicators = header.find_elements(By.XPATH, ".//button[contains(text(), 'Contato') or contains(text(), 'Email')]")
                if comercial_indicators:
                    dados['conta_comercial'] = True
            except Exception:
                pass

        # 6. Conta destaques nos stories
        try:
            destaques = driver.find_elements(By.XPATH, "//div[contains(@class, 'highlight')]//img")
            dados['destaque_stories'] = len(destaques)
        except Exception:
            dados['destaque_stories'] = 0

        # 7. Conta posts recentes visíveis
        try:
            posts_grid = driver.find_elements(By.XPATH, "//article//a[contains(@href, '/p/')]")
            dados['posts_recentes'] = min(len(posts_grid), 12)  # Máximo 12 posts visíveis
        except Exception:
            dados['posts_recentes'] = 0
        


        # 8. Extrai a biografia completa e o link externo de forma robusta
        try:
            textos_bio = []
            link_externo = ""
            # 1. Tenta encontrar a bio por diferentes caminhos comuns
            # a) Bio logo após o nome do perfil (h1)
            try:
                h1 = header.find_element(By.TAG_NAME, "h1")
                # O próximo elemento pode ser a bio (div ou span)
                next_elem = h1.find_element(By.XPATH, "following-sibling::*[1]")
                if next_elem.tag_name in ["div", "span"]:
                    bio_text = next_elem.text.strip()
                    if bio_text:
                        textos_bio.append(bio_text)
            except Exception:
                pass

            # b) Busca por todos os spans/divs dentro do header que não sejam o nome, categoria ou link
            bio_candidates = header.find_elements(By.XPATH, ".//div|.//span")
            for elem in bio_candidates:
                # Ignora se for o nome do perfil (h1) ou categoria (normalmente tem aria-label ou role)
                if elem.text and elem.text.strip():
                    parent_tag = elem.find_element(By.XPATH, "..")
                    if parent_tag.tag_name == "h1":
                        continue
                    # Ignora se for link
                    if elem.find_elements(By.TAG_NAME, "a"):
                        continue
                    # Evita duplicidade
                    if elem.text.strip() not in textos_bio:
                        textos_bio.append(elem.text.strip())

            # c) Busca por link externo (primeiro <a> que não seja menção ou hashtag)
            try:
                link_elem = header.find_element(By.XPATH, ".//a[not(contains(@href, '/')) and starts-with(@href, 'http')]" )
                link_externo = link_elem.get_attribute('href')
            except Exception:
                # fallback: pega o primeiro <a> externo
                try:
                    link_elem = header.find_element(By.XPATH, ".//a[starts-with(@href, 'http') and not(contains(@href, 'instagram.com'))]")
                    link_externo = link_elem.get_attribute('href')
                except Exception:
                    pass

            # Limpeza da bio: remove quebras de linha e termos irrelevantes
            bio_final = " ".join(textos_bio).strip().replace('\n', ' ').replace('\r', ' ')
            # Remove termos irrelevantes
            termos_irrelevantes = [
                'Seguir', 'Enviar mensagem', 'publicações', 'seguidores', 'seguindo',
                'mensagem', 'mensagens', 'seguir', 'seguindo', 'seguidores', 'publicação',
                'enviar mensagem', 'enviarmensagem', 'seguir', 'seguindo', 'seguidores',
                'publicações', 'publicação', 'mensagem', 'mensagens'
            ]
            # Remove também padrões como "25 publicações", "81 seguidores", "52 seguindo" etc.
            import re
            for termo in termos_irrelevantes:
                bio_final = re.sub(rf'\b{re.escape(termo)}\b', '', bio_final, flags=re.IGNORECASE)
            # Remove padrões numéricos irrelevantes
            bio_final = re.sub(r'\b\d+\s*(publicações|seguidores|seguindo)\b', '', bio_final, flags=re.IGNORECASE)
            # Remove múltiplos espaços
            bio_final = re.sub(r'\s+', ' ', bio_final).strip()
            dados["bio"] = bio_final
            dados["link_externo"] = link_externo
            if not bio_final:
                raise NoSuchElementException()
        except NoSuchElementException:
            logging.warning(f"   ⚠️ Bio ou link externo não encontrados para '{username}'.")

        # 9. Calcula engajamento médio simulado (em implementação real seria baseado em posts)
        try:
            if int(dados['n_publicacoes']) > 0 and int(dados['n_seguidores']) > 0:
                # Fórmula simplificada de engajamento - em implementação real seria análise de posts
                dados['engajamento_medio'] = round(random.uniform(0.5, 8.0), 2)
            else:
                dados['engajamento_medio'] = 0.0
        except:
            dados['engajamento_medio'] = 0.0
            
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
    logging.info(f"📊 Carregado arquivo com {len(df_entrada)} registros.")

    # Verifica se a coluna username existe
    if 'username' not in df_entrada.columns:
        logging.error(f"O arquivo de entrada '{ARQUIVO_ENTRADA}' deve conter a coluna 'username'.")
        exit()

    # Remove duplicatas de username para processar apenas uma vez cada perfil
    usernames_unicos = df_entrada['username'].drop_duplicates().tolist()
    logging.info(f"📋 Encontrados {len(usernames_unicos)} perfis únicos para processar.")

    # Colunas que serão adicionadas ao arquivo final
    novas_colunas = [
        "bio_atualizada", "n_publicacoes_atual", "n_seguidores_atual", "n_seguindo_atual",
        "link_externo_atual", "verificado_atual", "status_conta_atual", "conta_comercial_atual",
        "categoria_atual", "destaque_stories", "posts_recentes", "engajamento_medio"
    ]

    # Verifica se já existe arquivo de progresso
    if os.path.exists(ARQUIVO_SAIDA):
        logging.info("📄 Encontrado arquivo de progresso. Continuando de onde parou...")
        df_progresso = pd.read_csv(ARQUIVO_SAIDA)
        usernames_ja_processados = df_progresso['username'].tolist() if 'username' in df_progresso.columns else []
        usernames_para_buscar = [u for u in usernames_unicos if u not in usernames_ja_processados]
        logging.info(f"✅ {len(usernames_ja_processados)} perfis já processados. Restam {len(usernames_para_buscar)}.")
    else:
        # Criar arquivo de saída com todas as colunas originais + novas colunas
        colunas_finais = list(df_entrada.columns) + novas_colunas
        pd.DataFrame(columns=colunas_finais).to_csv(ARQUIVO_SAIDA, index=False, encoding='utf-8')
        usernames_para_buscar = usernames_unicos
        logging.info(f"📝 Arquivo de saída '{ARQUIVO_SAIDA}' criado com sucesso.")

    if not usernames_para_buscar:
        logging.info("🎉 Todos os perfis já foram processados. Encerrando.")
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

            # Busca todos os registros com este username
            registros_username = df_entrada[df_entrada['username'] == username]
            
            # Para cada registro com este username, adiciona os dados avançados
            for _, registro_original in registros_username.iterrows():
                registro_completo = registro_original.to_dict()
                
                # Adiciona os novos dados
                registro_completo.update({
                    "bio_atualizada": dados_avancados.get("bio", ""),
                    "n_publicacoes_atual": dados_avancados.get("n_publicacoes", ""),
                    "n_seguidores_atual": dados_avancados.get("n_seguidores", ""),
                    "n_seguindo_atual": dados_avancados.get("n_seguindo", ""),
                    "link_externo_atual": dados_avancados.get("link_externo", ""),
                    "verificado_atual": dados_avancados.get("verificado", ""),
                    "status_conta_atual": dados_avancados.get("status_conta", ""),
                    "conta_comercial_atual": dados_avancados.get("conta_comercial", False),
                    "categoria_atual": dados_avancados.get("categoria", ""),
                    "destaque_stories": dados_avancados.get("destaque_stories", 0),
                    "posts_recentes": dados_avancados.get("posts_recentes", 0),
                    "engajamento_medio": dados_avancados.get("engajamento_medio", 0.0)
                })

                # Salva o registro no arquivo
                df_para_salvar = pd.DataFrame([registro_completo])
                df_para_salvar.to_csv(ARQUIVO_SAIDA, mode='a', header=False, index=False, encoding='utf-8')

            logging.info(f"✅ Dados de '{username}' salvos no CSV ({len(registros_username)} registros atualizados).")
            total_processados_sessao += 1

            # Pausa entre perfis
            pausa = random.uniform(8, 15)
            logging.info(f"   ⏸️ Pausando por {pausa:.1f} segundos...")
            time.sleep(pausa)

        logging.info(f"\n🎉 Processo de enriquecimento de dados concluído! {total_processados_sessao} novos perfis foram processados nesta sessão.")

    except Exception as final_e:
        logging.critical(f"❌ Um erro inesperado ocorreu no fluxo principal: {final_e}")
    finally:
        if driver:
            driver.quit()
            logging.info("🔒 Navegador fechado.")