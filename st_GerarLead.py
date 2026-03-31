import streamlit as st
import pandas as pd
import asyncio
import random
from playwright.async_api import async_playwright

# ─────────────────────────────────────────────
# CONFIG UI
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
h1, h2 {
    color: white;
    text-align: center;
}
.card {
    background:#1e293b;
    padding:25px;
    border-radius:15px;
}
.stButton>button {
    background: linear-gradient(90deg, #6366f1, #8b5cf6);
    color: white;
    border-radius: 10px;
    height: 50px;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# LOGIN
# ─────────────────────────────────────────────

def tela_login():
    st.markdown("<h1>🔐 Acesso Restrito</h1>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1,2,1])

    with col2:
        st.markdown("<div class='card'>", unsafe_allow_html=True)

        user = st.text_input("Usuário")
        pwd = st.text_input("Senha", type="password")

        if st.button("Entrar", use_container_width=True):
            if user == "aiosa" and pwd == "@iosa31R":
                st.session_state["auth"] = True
                st.rerun()
            else:
                st.error("Credenciais inválidas")

        st.markdown("</div>", unsafe_allow_html=True)

if "auth" not in st.session_state:
    st.session_state["auth"] = False

if not st.session_state["auth"]:
    tela_login()
    st.stop()

# ─────────────────────────────────────────────
# CONFIG PLAYWRIGHT
# ─────────────────────────────────────────────

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
]

# ─────────────────────────────────────────────
# BROWSER
# ─────────────────────────────────────────────

async def iniciar():
    p = await async_playwright().start()

    browser = await p.chromium.launch(headless=True)

    context = await browser.new_context(
        user_agent=random.choice(USER_AGENTS),
        viewport={"width": 1920, "height": 1080}
    )

    page = await context.new_page()

    return p, browser, context, page

# ─────────────────────────────────────────────
# SCROLL TOTAL
# ─────────────────────────────────────────────

async def scroll(page):
    await page.wait_for_selector('div[role="feed"]')

    last = 0

    while True:
        await page.mouse.wheel(0, 5000)
        await asyncio.sleep(random.uniform(1.5, 2.5))

        elements = await page.query_selector_all("a.hfpxzc")
        count = len(elements)

        if count == last:
            break

        last = count

    return elements

# ─────────────────────────────────────────────
# DETALHES
# ─────────────────────────────────────────────

async def extrair(context, link):
    page = await context.new_page()

    try:
        await page.goto(link, timeout=30000)
        await page.wait_for_selector(".Io6YTe", timeout=10000)

        dados = {"Endereço": "N/A", "Telefone": "N/A", "Site": "N/A"}

        elements = await page.query_selector_all(".Io6YTe")

        for el in elements:
            txt = await el.inner_text()

            if "(" in txt and any(c.isdigit() for c in txt):
                dados["Telefone"] = txt

            if "," in txt and len(txt) > 10:
                dados["Endereço"] = txt

        try:
            site = await page.query_selector('a[data-item-id="authority"]')
            if site:
                dados["Site"] = await site.get_attribute("href")
        except:
            pass

        return dados

    except:
        return None

    finally:
        await page.close()

# ─────────────────────────────────────────────
# EXECUÇÃO
# ─────────────────────────────────────────────

async def run(termo):

    p, browser, context, page = await iniciar()

    url = f"https://www.google.com/maps/search/{termo.replace(' ', '+')}"
    await page.goto(url)

    elements = await scroll(page)

    lista = []

    for el in elements:
        try:
            nome = await el.get_attribute("aria-label")
            link = await el.get_attribute("href")

            if nome and link:
                lista.append({"Empresa": nome, "Link": link})
        except:
            continue

    tarefas = [extrair(context, item["Link"]) for item in lista]

    respostas = await asyncio.gather(*tarefas)

    resultados = []

    for item, detalhe in zip(lista, respostas):
        if detalhe:
            resultados.append({
                "Empresa": item["Empresa"],
                "Link": item["Link"],
                **detalhe
            })

    await browser.close()
    await p.stop()

    return pd.DataFrame(resultados)

# ─────────────────────────────────────────────
# UI PRINCIPAL
# ─────────────────────────────────────────────

st.title("🚀 Maps Extractor PRO")

termo = st.text_input("Buscar", placeholder="Ex: Clínicas em São Paulo")

if st.button("🚀 Iniciar Extração"):

    if not termo:
        st.warning("Digite um termo")
    else:
        with st.spinner("Executando extração..."):
            df = asyncio.run(run(termo))

        st.success(f"✅ {len(df)} empresas extraídas")

        st.dataframe(df, use_container_width=True)

        df.to_excel("leads.xlsx", index=False)

        with open("leads.xlsx", "rb") as f:
            st.download_button("📥 Baixar Excel", f, "leads.xlsx")

# ─────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────

st.markdown("---")
st.markdown(
    "<p style='text-align:center; color:gray;'>Desenvolvido por Rodrigo AIOSA</p>",
    unsafe_allow_html=True
)
