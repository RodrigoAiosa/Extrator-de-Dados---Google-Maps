import streamlit as st
import pandas as pd
import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# --- CONFIGURAÇÕES DO SELENIUM ---
def configurar_driver():
    options = Options()
    options.add_argument('--headless') 
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

def extrair_detalhes(driver, link):
    try:
        driver.get(link)
        time.sleep(2.5)
        dados = {'Endereço': 'N/A', 'Telefone': 'N/A', 'Site': 'N/A'}
        
        elementos_info = driver.find_elements(By.CLASS_NAME, "Io6YTe")
        for el in elementos_info:
            texto = el.text
            # Regex simples para telefone (ajustado para ser mais flexível)
            if "(" in texto and "-" in texto and any(char.isdigit() for char in texto):
                dados['Telefone'] = texto
            elif " - " in texto or "," in texto:
                if dados['Endereço'] == 'N/A':
                    dados['Endereço'] = texto
        
        try:
            elemento_site = driver.find_element(By.CSS_SELECTOR, 'a[data-item-id="authority"]')
            dados['Site'] = elemento_site.get_attribute("href")
        except:
            pass 

        return dados
    except Exception:
        return None

# --- INTERFACE STREAMLIT ---
st.set_page_config(page_title="Google Maps Scraper", layout="wide", page_icon="📍")
st.title("📍 Extrator de Dados - Google Maps")

termo_final = st.text_input("O que você deseja buscar?", placeholder="Ex: Fabricantes de móveis em SP")

# Arquivo para manter o histórico global (preservando conforme sua instrução)
arquivo_excel = 'base_dados_total.xlsx'

if st.button("🚀 Iniciar Extração"):
    if not termo_final:
        st.warning("Por favor, digite um termo de busca.")
    else:
        driver = configurar_driver()
        status_info = st.empty()
        barra_progresso = st.progress(0)
        log_erros = []
        
        try:
            url_busca = f"https://www.google.com.br/maps/search/{termo_final.replace(' ', '+')}"
            driver.get(url_busca)
            
            status_info.info(f"Buscando por: '{termo_final}'...")
            wait = WebDriverWait(driver, 15)
            wait.until(EC.presence_of_element_located((By.XPATH, '//div[@role="feed"]')))

            # Rolagem para carregar a lista
            painel = driver.find_element(By.XPATH, '//div[@role="feed"]')
            last_count = 0
            while True:
                driver.execute_script('arguments[0].scrollTop = arguments[0].scrollHeight', painel)
                time.sleep(2)
                elementos_atuais = driver.find_elements(By.CLASS_NAME, "hfpxzc")
                current_count = len(elementos_atuais)
                status_info.text(f"Locais identificados: {current_count}")
                if current_count == last_count: break
                last_count = current_count
                if current_count > 80: break # Limite de segurança para demonstração

            # Coleta inicial
            elementos = driver.find_elements(By.CLASS_NAME, "hfpxzc")
            
            # Criando o DataFrame APENAS da pesquisa atual
            df_atual = pd.DataFrame([{"Termo Pesquisado": termo_final, 
                                     "Empresa": el.get_attribute("aria-label"), 
                                     "Link": el.get_attribute("href"), 
                                     "Endereço": "Pendente", 
                                     "Telefone": "Pendente",
                                     "Site": "Pendente"} for el in elementos])

            # --- REMOÇÃO DE DUPLICADAS NA BUSCA ATUAL ---
            df_atual = df_atual.drop_duplicates(subset=['Link'], keep='first').reset_index(drop=True)
            
            total_locais = len(df_atual)
            st.info(f"Total de {total_locais} empresas únicas encontradas.")

            # Extração Detalhada
            for i in range(total_locais):
                empresa = df_atual.at[i, 'Empresa']
                status_info.text(f"Extraindo detalhes ({i+1}/{total_locais}): {empresa}")
                barra_progresso.progress((i + 1) / total_locais)
                
                detalhes = extrair_detalhes(driver, df_atual.at[i, 'Link'])
                
                if detalhes:
                    df_atual.at[i, 'Endereço'] = detalhes['Endereço']
                    df_atual.at[i, 'Telefone'] = detalhes['Telefone']
                    df_atual.at[i, 'Site'] = detalhes['Site']
                else:
                    log_erros.append(f"Erro em: {empresa}")

            # Salva na sessão (apenas os dados novos e limpos)
            st.session_state['df_resultado'] = df_atual

            # --- PRESERVAÇÃO DE DADOS NO ARQUIVO LOCAL (OPCIONAL) ---
            if os.path.exists(arquivo_excel):
                df_hist = pd.read_excel(arquivo_excel)
                df_full = pd.concat([df_hist, df_atual], ignore_index=True).drop_duplicates(subset=['Link'])
                df_full.to_excel(arquivo_excel, index=False)
            else:
                df_atual.to_excel(arquivo_excel, index=False)

            st.success(f"Extração concluída!")

            if log_erros:
                with st.expander("⚠️ Ver Log de Erros"):
                    for erro in log_erros: st.write(erro)

        except Exception as e:
            st.error(f"Erro crítico: {e}")
        finally:
            driver.quit()

# --- ÁREA DE EXPORTAÇÃO ---
if 'df_resultado' in st.session_state:
    st.divider()
    st.subheader("📊 Resultados da Pesquisa Atual")
    st.dataframe(st.session_state['df_resultado'], use_container_width=True)
    
    csv = st.session_state['df_resultado'].to_csv(index=False).encode('utf-8-sig')
    
    # Nome do arquivo dinâmico baseado no termo buscado
    nome_arquivo = f"leads_{termo_final.replace(' ', '_')}.csv"
    
    st.download_button(
        label=f"📥 Baixar {len(st.session_state['df_resultado'])} leads (CSV)",
        data=csv,
        file_name=nome_arquivo,
        mime='text/csv'
    )