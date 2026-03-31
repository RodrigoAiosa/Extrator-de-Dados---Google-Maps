import streamlit as st
import pandas as pd
import time
import os
import shutil
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ─────────────────────────────────────────────
# CREDENCIAIS
# ─────────────────────────────────────────────
USUARIO_CORRETO = "aiosa"
SENHA_CORRETA   = "@iosa31R"

# ─────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────
CSS = """<style>
[data-testid="stSidebar"] { display: none !important; }
[data-testid="stHeader"], footer { display:none !important; }
</style>"""

# ─────────────────────────────────────────────
# SELENIUM
# ─────────────────────────────────────────────
def _chrome_options():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    return options


def configurar_driver():
    options = _chrome_options()

    try:
        from webdriver_manager.chrome import ChromeDriverManager
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=options)
    except:
        return webdriver.Chrome(options=options)


def rolar_ate_o_fim(driver):
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.XPATH, '//div[@role="feed"]'))
    )
    painel = driver.find_element(By.XPATH, '//div[@role="feed"]')

    ultimo = 0
    while True:
        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", painel)
        time.sleep(2)
        elementos = driver.find_elements(By.CLASS_NAME, "hfpxzc")
        if len(elementos) == ultimo:
            break
        ultimo = len(elementos)

    return elementos


def extrair_detalhes(driver, link):
    try:
        driver.get(link)
        time.sleep(2)

        dados = {
            "Endereço": "N/A",
            "Telefone": "N/A",
            "Site": "N/A"
        }

        try:
            dados["Endereço"] = driver.find_element(By.CSS_SELECTOR, 'button[data-item-id="address"]').text
        except: pass

        try:
            dados["Telefone"] = driver.find_element(By.CSS_SELECTOR, 'button[data-item-id^="phone"]').text
        except: pass

        try:
            dados["Site"] = driver.find_element(By.CSS_SELECTOR, 'a[data-item-id="authority"]').get_attribute("href")
        except: pass

        return dados
    except:
        return None


# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
st.set_page_config(page_title="Gerar Lead", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# SESSION
# ─────────────────────────────────────────────
if "logado" not in st.session_state:
    st.session_state["logado"] = False

# ─────────────────────────────────────────────
# LOGIN
# ─────────────────────────────────────────────
if not st.session_state["logado"]:

    st.title("🔐 Login")

    user = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        if user == USUARIO_CORRETO and senha == SENHA_CORRETA:
            st.session_state["logado"] = True
            st.rerun()
        else:
            st.error("Credenciais inválidas")

    st.stop()

# ─────────────────────────────────────────────
# APP PRINCIPAL (SEM BOTÃO SAIR)
# ─────────────────────────────────────────────
st.title("📍 Gerador de Leads")

termo = st.text_input("Digite sua busca")

if st.button("Buscar"):
    driver = configurar_driver()

    try:
        url = f"https://www.google.com/maps/search/{termo.replace(' ', '+')}"
        driver.get(url)

        elementos = rolar_ate_o_fim(driver)

        dados = []

        for el in elementos:
            nome = el.get_attribute("aria-label")
            link = el.get_attribute("href")

            detalhes = extrair_detalhes(driver, link)

            if detalhes:
                dados.append({
                    "Empresa": nome,
                    "Endereço": detalhes["Endereço"],
                    "Telefone": detalhes["Telefone"],
                    "Site": detalhes["Site"]
                })

        df = pd.DataFrame(dados)
        st.dataframe(df)

        st.download_button(
            "Baixar Excel",
            df.to_excel(index=False),
            file_name="leads.xlsx"
        )

    finally:
        driver.quit()
