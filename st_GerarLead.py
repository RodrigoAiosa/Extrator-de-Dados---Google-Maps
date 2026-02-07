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

# --- CONFIGURAÇÕES DO SELENIUM PARA STREAMLIT CLOUD ---

def configurar_driver():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-blink-features=AutomationControlled')

    # Caminhos específicos do ambiente Linux do Streamlit
    options.binary_location = "/usr/bin/chromium"

    # Utilizamos o driver instalado via packages.txt
    service = Service("/usr/bin/chromedriver")

    driver = webdriver.Chrome(service=service, options=options)
    return driver


def extrair_detalhes(driver, link):
    try:
        driver.get(link)
        time.sleep(2.5)
        dados = {'Endereço': 'N/A', 'Telefone': 'N/A', 'Site': 'N/A'}

        elementos_info = driver.find_elements(By.CLASS_NAME, "Io6YTe")
        for el in elementos_info:
            texto = el.text
            # Identificação básica de telefone
            if "(" in texto and "-" in texto and any(char.isdigit() for char in texto):
                dados['Telefone'] = texto
            # Identificação básica de endereço
            elif " - " in texto or "," in texto:
                if dados['Endereço'] == 'N/A':
                    dados['Endereço'] = texto

        try:
            elemento_site = driver.find_element(
                By.CSS_SELECTOR, 'a[data-item-id="authority"]')
            dados['Site'] = elemento_site.get_attribute("href")
        except:
            pass

        return dados
    except Exception:
        return None


# --- INTERFACE STREAMLIT ---
st.set_page_config(page_title="Google Maps Scraper",
                    layout="wide", page_icon="📍")
st.title("📍 Extrator de Dados - Google Maps")

termo_final = st.text_input(
    "O que você deseja buscar?", placeholder="Ex: Fabricantes de móveis em SP")

# Arquivo para manter o histórico global
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
            wait.until(EC.presence_of_element_located(
                (By.XPATH, '//div[@role="feed"]')))

            # Rolagem para carregar a lista
            painel = driver.find_element(By.XPATH, '//div[@role="feed"]')
            last_count = 0
            while True:
                driver.execute_script(
                    'arguments[0].scrollTop = arguments[0].scrollHeight', painel)
                time.sleep(2)
                elementos_atuais = driver.find_elements(
                    By.CLASS_NAME, "hfpxzc")
                current_count = len(elementos_atuais)
                status_info.text(f"Locais identificados: {current_count}")
                if current_count == last_count:
                    break
                last_count = current_count
                if current_count > 60:
                    break 

            # Coleta dos links e nomes
            elementos = driver.find_elements(By.CLASS_NAME, "hfpxzc")
            df_atual = pd.DataFrame([{"Termo Pesquisado": termo_final,
                                     "Empresa": el.get_attribute("aria-label"),
                                      "Link": el.get_attribute("href"),
                                      "Endereço": "Pendente",
                                      "Telefone": "Pendente",
                                      "Site": "Pendente"} for el in elementos])

            # Limpeza de duplicados
            df_atual = df_atual.drop_duplicates(
                subset=['Link']).reset_index(drop=True)
            total_locais = len(df_atual)
            st.info(f"Processando {total_locais} empresas únicas...")

            # Extração dos Detalhes
            for i in range(total_locais):
                empresa = df_atual.at[i, 'Empresa']
                status_info.text(
                    f"Extraindo ({i+1}/{total_locais}): {empresa}")
                barra_progresso.progress((i + 1) / total_locais)

                detalhes = extrair_detalhes(driver, df_atual.at[i, 'Link'])

                if detalhes:
                    df_atual.at[i, 'Endereço'] = detalhes['Endereço']
                    df_atual.at[i, 'Telefone'] = detalhes['Telefone']
                    df_atual.at[i, 'Site'] = detalhes['Site']
                else:
                    log_erros.append(f"Erro em: {empresa}")

            # Persistência de dados
            if os.path.exists(arquivo_excel):
                df_hist = pd.read_excel(arquivo_excel)
                df_final = pd.concat([df_hist, df_atual], ignore_index=True)
                df_final = df_final.drop_duplicates(
                    subset=['Link'], keep='last')
                df_final.to_excel(arquivo_excel, index=False)
                st.session_state['df_resultado'] = df_atual
            else:
                df_atual.to_excel(arquivo_excel, index=False)
                st.session_state['df_resultado'] = df_atual

            st.success("Extração finalizada e base de dados atualizada!")

        except Exception as e:
            st.error(f"Ocorreu um erro: {e}")
        finally:
            driver.quit()

# --- EXIBIÇÃO E DOWNLOAD ---
if 'df_resultado' in st.session_state:
    st.divider()
    st.subheader("📊 Resultados desta pesquisa")
    st.dataframe(st.session_state['df_resultado'], use_container_width=True)

    if os.path.exists(arquivo_excel):
        with open(arquivo_excel, "rb") as f:
            st.download_button(
                label="📥 Baixar Base de Dados Completa (Excel)",
                data=f,
                file_name="base_leads_acumulada.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

# --- RODAPÉ (FOOTER) ---
st.markdown("---")
footer_html = """
<div style='text-align: center; color: gray;'>
    <p style='margin-bottom: 5px;'>Desenvolvido por <b>Rodrigo AIOSA</b></p>
    <div style='display: flex; justify-content: center; gap: 20px; font-size: 24px;'>
        <a href='https://wa.me/5511977019335' target='_blank' style='text-decoration: none;'>
            <img src='https://cdn-icons-png.flaticon.com/512/733/733585.png' width='25' height='25' title='WhatsApp'>
        </a>
        <a href='https://www.linkedin.com/in/rodrigoaiosa/' target='_blank' style='text-decoration: none;'>
            <img src='https://cdn-icons-png.flaticon.com/512/174/174857.png' width='25' height='25' title='LinkedIn'>
        </a>
    </div>
</div>
"""
st.markdown(footer_html, unsafe_allow_html=True)
