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

# ─────────────────────────────────────────────
# CONFIG GLOBAL + DESIGN (LANDING PAGE)
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="Maps Extractor PRO",
    page_icon="🚀",
    layout="wide"
)

st.markdown("""
<style>
body {
    background: linear-gradient(135deg, #0f172a, #1e293b);
}
.main {
    background-color: #0f172a;
}
h1, h2, h3 {
    color: #e2e8f0;
}
.small-text {
    color: #94a3b8;
}
.stButton>button {
    background: linear-gradient(90deg, #6366f1, #8b5cf6);
    color: white;
    border-radius: 10px;
    height: 50px;
    font-weight: bold;
    border: none;
}
.stButton>button:hover {
    background: linear-gradient(90deg, #4f46e5, #7c3aed);
}
.stTextInput>div>div>input {
    border-radius: 10px;
    padding: 10px;
}
.card {
    background: #1e293b;
    padding: 25px;
    border-radius: 15px;
    box-shadow: 0px 0px 20px rgba(0,0,0,0.3);
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# LOGIN
# ─────────────────────────────────────────────

def tela_login():
    st.markdown("<h1 style='text-align:center;'>🔐 Acesso Restrido</h1>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1,2,1])

    with col2:
        st.markdown("<div class='card'>", unsafe_allow_html=True)

        usuario = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")

        if st.button("Entrar", use_container_width=True):
            if usuario == "aiosa" and senha == "@iosa31R":
                st.session_state["logado"] = True
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos")

        st.markdown("</div>", unsafe_allow_html=True)

if "logado" not in st.session_state:
    st.session_state["logado"] = False

if not st.session_state["logado"]:
    tela_login()
    st.stop()

# ─────────────────────────────────────────────
# HERO (LANDING PAGE)
# ─────────────────────────────────────────────

st.markdown("""
<div style="text-align:center; padding: 40px 0;">
    <h1 style="font-size: 48px;">🚀 Maps Extractor PRO</h1>
    <p class="small-text" style="font-size:18px;">
        Extraia dados completos do Google Maps com automação inteligente
    </p>
</div>
""", unsafe_allow_html=True)

c1, c2, c3 = st.columns(3)

with c1:
    st.markdown("""
    <div class="card">
        <h3>📍 Leads Qualificados</h3>
        <p class="small-text">Empresas com telefone, site e endereço.</p>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown("""
    <div class="card">
        <h3>⚡ Automação Total</h3>
        <p class="small-text">Captura completa dos resultados.</p>
    </div>
    """, unsafe_allow_html=True)

with c3:
    st.markdown("""
    <div class="card">
        <h3>📊 Exportação Excel</h3>
        <p class="small-text">Dados prontos para uso imediato.</p>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ─────────────────────────────────────────────
# DRIVER
# ─────────────────────────────────────────────

def configurar_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    )
    options.binary_location = "/usr/bin/chromium"
    service = Service("/usr/bin/chromedriver")
    return webdriver.Chrome(service=service, options=options)

# ─────────────────────────────────────────────
# SCROLL
# ─────────────────────────────────────────────

def rolar_ate_o_fim(driver, status_widget):
    wait = WebDriverWait(driver, 15)
    wait.until(EC.presence_of_element_located((By.XPATH, '//div[@role="feed"]')))

    painel = driver.find_element(By.XPATH, '//div[@role="feed"]')
    ultimo_count = 0

    while True:
        driver.execute_script(
            "arguments[0].scrollTop = arguments[0].scrollHeight", painel
        )
        time.sleep(2)

        elementos = driver.find_elements(By.CLASS_NAME, "hfpxzc")
        count = len(elementos)

        status_widget.text(f"🔍 Encontrados: {count}")

        if count == ultimo_count:
            break

        ultimo_count = count

    return driver.find_elements(By.CLASS_NAME, "hfpxzc")

# ─────────────────────────────────────────────
# DETALHES
# ─────────────────────────────────────────────

def extrair_detalhes(driver, link):
    try:
        driver.get(link)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "Io6YTe"))
        )
        time.sleep(1)

        dados = {
            "Endereço": "N/A",
            "Telefone": "N/A",
            "Site": "N/A",
        }

        elementos = driver.find_elements(By.CLASS_NAME, "Io6YTe")

        for el in elementos:
            txt = el.text.strip()

            if "(" in txt and any(c.isdigit() for c in txt):
                dados["Telefone"] = txt

            if "," in txt and len(txt) > 10:
                dados["Endereço"] = txt

        try:
            site = driver.find_element(By.CSS_SELECTOR, 'a[data-item-id="authority"]')
            dados["Site"] = site.get_attribute("href")
        except:
            pass

        return dados

    except:
        return None

# ─────────────────────────────────────────────
# INPUT
# ─────────────────────────────────────────────

st.markdown("### 🔎 Buscar empresas")

termo_final = st.text_input("", placeholder="Ex: Restaurantes em São Paulo")

arquivo_excel = "base_dados_total.xlsx"

# ─────────────────────────────────────────────
# EXECUÇÃO
# ─────────────────────────────────────────────

if st.button("🚀 Iniciar Extração", use_container_width=True):

    driver = configurar_driver()
    status = st.empty()
    progresso = st.progress(0)

    url = f"https://www.google.com/maps/search/{termo_final.replace(' ', '+')}"
    driver.get(url)

    elementos = rolar_ate_o_fim(driver, status)

    dados = []

    total = len(elementos)

    for i, el in enumerate(elementos):
        nome = el.get_attribute("aria-label")
        link = el.get_attribute("href")

        status.text(f"Extraindo {i+1}/{total}: {nome}")
        progresso.progress((i+1)/total)

        detalhes = extrair_detalhes(driver, link)

        if detalhes:
            dados.append({
                "Empresa": nome,
                "Link": link,
                **detalhes
            })

    df = pd.DataFrame(dados)

    df.to_excel(arquivo_excel, index=False)

    st.success(f"✅ {len(df)} empresas extraídas!")

    st.dataframe(df, use_container_width=True)

    with open(arquivo_excel, "rb") as f:
        st.download_button(
            "📥 Baixar Excel",
            f,
            "leads.xlsx"
        )

    driver.quit()

# ─────────────────────────────────────────────
# RODAPÉ
# ─────────────────────────────────────────────

st.markdown("---")
st.markdown(
    "<p style='text-align:center; color:gray;'>Desenvolvido por Rodrigo AIOSA</p>",
    unsafe_allow_html=True
)
