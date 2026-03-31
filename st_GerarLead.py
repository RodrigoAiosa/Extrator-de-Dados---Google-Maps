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
# CREDENCIAIS
# ─────────────────────────────────────────────
USUARIO_CORRETO = "aiosa"
SENHA_CORRETA   = "@iosa31R"

# ─────────────────────────────────────────────
# CSS — LANDING PAGE STYLE
# ─────────────────────────────────────────────
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500&display=swap');

/* ── Reset & base ───────────────────────────── */
html, body, [data-testid="stAppViewContainer"] {
    background: #080C14 !important;
}
[data-testid="stAppViewContainer"] {
    font-family: 'DM Sans', sans-serif;
    color: #E8EDF5;
}
[data-testid="stHeader"],
[data-testid="stToolbar"],
footer { display: none !important; }

/* ── Hide sidebar ───────────────────────────── */
[data-testid="stSidebar"] { display: none !important; }

/* ── Scrollbar ──────────────────────────────── */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: #080C14; }
::-webkit-scrollbar-thumb { background: #1E4AE9; border-radius: 2px; }

/* ── HERO ───────────────────────────────────── */
.hero {
    position: relative;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 60px 24px 80px;
    overflow: hidden;
}
.hero::before {
    content: '';
    position: absolute;
    inset: 0;
    background:
        radial-gradient(ellipse 80% 60% at 50% -10%, rgba(30,74,233,0.35) 0%, transparent 70%),
        radial-gradient(ellipse 50% 40% at 80% 80%, rgba(0,212,255,0.10) 0%, transparent 60%);
    pointer-events: none;
}
.grid-bg {
    position: absolute;
    inset: 0;
    background-image:
        linear-gradient(rgba(30,74,233,0.06) 1px, transparent 1px),
        linear-gradient(90deg, rgba(30,74,233,0.06) 1px, transparent 1px);
    background-size: 48px 48px;
    mask-image: radial-gradient(ellipse 80% 70% at 50% 0%, black 30%, transparent 80%);
    pointer-events: none;
}
.badge {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: rgba(30,74,233,0.15);
    border: 1px solid rgba(30,74,233,0.4);
    border-radius: 100px;
    padding: 6px 18px;
    font-size: 12px;
    font-weight: 500;
    letter-spacing: .08em;
    text-transform: uppercase;
    color: #7BA7FF;
    margin-bottom: 28px;
    animation: fadeUp .7s ease both;
}
.badge-dot {
    width: 6px; height: 6px;
    background: #1E4AE9;
    border-radius: 50%;
    box-shadow: 0 0 8px #1E4AE9;
    animation: pulse 2s infinite;
}
@keyframes pulse {
    0%,100% { opacity:1; transform:scale(1); }
    50% { opacity:.5; transform:scale(1.4); }
}
.hero-title {
    font-family: 'Syne', sans-serif;
    font-size: clamp(2.6rem, 6vw, 5rem);
    font-weight: 800;
    line-height: 1.05;
    letter-spacing: -.02em;
    margin: 0 0 24px;
    animation: fadeUp .8s .1s ease both;
}
.hero-title span {
    background: linear-gradient(135deg, #1E4AE9 0%, #00D4FF 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.hero-sub {
    font-size: 1.15rem;
    font-weight: 300;
    color: #8A96B0;
    max-width: 560px;
    line-height: 1.7;
    margin: 0 auto 48px;
    animation: fadeUp .8s .2s ease both;
}

/* ── STATS ──────────────────────────────────── */
.stats-row {
    display: flex;
    justify-content: center;
    gap: 40px;
    flex-wrap: wrap;
    margin-bottom: 60px;
    animation: fadeUp .8s .3s ease both;
}
.stat-item { text-align: center; }
.stat-num {
    font-family: 'Syne', sans-serif;
    font-size: 2rem;
    font-weight: 800;
    background: linear-gradient(135deg, #fff 0%, #7BA7FF 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.stat-label {
    font-size: .75rem;
    font-weight: 500;
    letter-spacing: .1em;
    text-transform: uppercase;
    color: #4A5568;
    margin-top: 2px;
}
.stat-div {
    width: 1px;
    height: 40px;
    background: rgba(255,255,255,0.06);
    align-self: center;
}

/* ── LOGIN CARD ─────────────────────────────── */
.login-wrap {
    display: flex;
    justify-content: center;
    padding: 20px 24px 80px;
    animation: fadeUp .8s .25s ease both;
}
.login-card {
    width: 100%;
    max-width: 440px;
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 20px;
    padding: 44px 40px 40px;
    backdrop-filter: blur(12px);
    box-shadow: 0 0 80px rgba(30,74,233,0.12), 0 20px 60px rgba(0,0,0,0.4);
}
.login-icon {
    width: 52px; height: 52px;
    background: linear-gradient(135deg, #1E4AE9 0%, #00D4FF 100%);
    border-radius: 14px;
    display: flex; align-items: center; justify-content: center;
    font-size: 22px;
    margin: 0 auto 20px;
    box-shadow: 0 8px 24px rgba(30,74,233,0.4);
}
.login-title {
    font-family: 'Syne', sans-serif;
    font-size: 1.5rem;
    font-weight: 700;
    text-align: center;
    margin-bottom: 6px;
    color: #F0F4FF;
}
.login-sub {
    text-align: center;
    font-size: .875rem;
    color: #4A5568;
    margin-bottom: 32px;
}
.login-error {
    background: rgba(239,68,68,0.1);
    border: 1px solid rgba(239,68,68,0.25);
    border-radius: 10px;
    padding: 12px 16px;
    font-size: .875rem;
    color: #FCA5A5;
    text-align: center;
    margin-bottom: 16px;
}

/* ── FEATURES ───────────────────────────────── */
.features {
    display: flex;
    justify-content: center;
    gap: 20px;
    flex-wrap: wrap;
    padding: 0 24px 80px;
    animation: fadeUp .8s .4s ease both;
}
.feat-card {
    background: rgba(255,255,255,0.02);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 16px;
    padding: 28px 24px;
    width: 220px;
    transition: border-color .3s, transform .3s;
}
.feat-card:hover {
    border-color: rgba(30,74,233,0.4);
    transform: translateY(-4px);
}
.feat-icon { font-size: 1.8rem; margin-bottom: 12px; }
.feat-title {
    font-family: 'Syne', sans-serif;
    font-size: .95rem;
    font-weight: 700;
    margin-bottom: 6px;
    color: #E8EDF5;
}
.feat-desc { font-size: .8rem; color: #4A5568; line-height: 1.6; }

/* ── MAIN APP ───────────────────────────────── */
.app-header {
    background: linear-gradient(180deg, rgba(30,74,233,0.08) 0%, transparent 100%);
    border-bottom: 1px solid rgba(255,255,255,0.05);
    padding: 24px 40px;
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 40px;
}
.app-logo {
    width: 40px; height: 40px;
    background: linear-gradient(135deg, #1E4AE9, #00D4FF);
    border-radius: 10px;
    display: flex; align-items:center; justify-content:center;
    font-size: 18px;
}
.app-logo-text {
    font-family: 'Syne', sans-serif;
    font-size: 1.1rem;
    font-weight: 700;
    color: #F0F4FF;
}
.app-logo-sub { font-size: .75rem; color: #4A5568; }

/* ── Streamlit overrides ────────────────────── */
[data-testid="stTextInput"] label,
[data-testid="stNumberInput"] label {
    font-family: 'DM Sans', sans-serif !important;
    font-size: .8rem !important;
    font-weight: 500 !important;
    letter-spacing: .06em !important;
    text-transform: uppercase !important;
    color: #4A5568 !important;
    margin-bottom: 6px !important;
}
[data-testid="stTextInput"] input {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 10px !important;
    color: #E8EDF5 !important;
    padding: 12px 16px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: .95rem !important;
    transition: border-color .2s !important;
}
[data-testid="stTextInput"] input:focus {
    border-color: #1E4AE9 !important;
    box-shadow: 0 0 0 3px rgba(30,74,233,0.2) !important;
}
[data-testid="stButton"] button {
    background: linear-gradient(135deg, #1E4AE9 0%, #1638B8 100%) !important;
    border: none !important;
    border-radius: 10px !important;
    color: #fff !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important;
    font-size: .95rem !important;
    letter-spacing: .04em !important;
    padding: 14px 24px !important;
    transition: opacity .2s, transform .1s !important;
    box-shadow: 0 4px 20px rgba(30,74,233,0.35) !important;
}
[data-testid="stButton"] button:hover {
    opacity: .9 !important;
    transform: translateY(-1px) !important;
}
[data-testid="stButton"] button:active { transform: translateY(0) !important; }

.stProgress > div > div {
    background: linear-gradient(90deg, #1E4AE9, #00D4FF) !important;
    border-radius: 4px !important;
}
[data-testid="stDataFrame"] {
    border: 1px solid rgba(255,255,255,0.06) !important;
    border-radius: 12px !important;
}
[data-testid="metric-container"] {
    background: rgba(255,255,255,0.02) !important;
    border: 1px solid rgba(255,255,255,0.06) !important;
    border-radius: 12px !important;
    padding: 16px !important;
}

/* ── Animations ─────────────────────────────── */
@keyframes fadeUp {
    from { opacity:0; transform:translateY(24px); }
    to   { opacity:1; transform:translateY(0); }
}

/* ── Footer ─────────────────────────────────── */
.custom-footer {
    text-align: center;
    padding: 40px 24px;
    border-top: 1px solid rgba(255,255,255,0.04);
    color: #2D3748;
    font-size: .8rem;
}
.custom-footer b { color: #4A5568; }
.footer-icons { display:flex; justify-content:center; gap:16px; margin-top:12px; }
</style>
"""

# ─────────────────────────────────────────────
# SELENIUM
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
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    options.binary_location = "/usr/bin/chromium"
    service = Service("/usr/bin/chromedriver")
    return webdriver.Chrome(service=service, options=options)


def rolar_ate_o_fim(driver, status_widget, max_sem_novos=5):
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.XPATH, '//div[@role="feed"]'))
    )
    painel = driver.find_element(By.XPATH, '//div[@role="feed"]')
    sem_novos = 0
    ultimo = 0
    while True:
        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", painel)
        time.sleep(2.5)
        elementos = driver.find_elements(By.CLASS_NAME, "hfpxzc")
        total = len(elementos)
        status_widget.text(f"🔍 Locais identificados: {total} — carregando mais...")
        if total == ultimo:
            sem_novos += 1
        else:
            sem_novos = 0
        ultimo = total
        fim = driver.find_elements(
            By.XPATH,
            '//*[contains(text(),"Você chegou ao fim")]|//*[contains(text(),"end of the list")]'
        )
        if fim or sem_novos >= max_sem_novos:
            status_widget.text(f"✅ Lista completa: {total} locais encontrados.")
            break
    return driver.find_elements(By.CLASS_NAME, "hfpxzc")


def extrair_detalhes(driver, link, tentativas=3):
    for t in range(tentativas):
        try:
            driver.get(link)
            WebDriverWait(driver, 12).until(
                EC.presence_of_element_located((By.CLASS_NAME, "Io6YTe"))
            )
            time.sleep(1.5)
            dados = {"Endereço": "N/A", "Telefone": "N/A", "Site": "N/A",
                     "Avaliação": "N/A", "Nº Avaliações": "N/A", "Categoria": "N/A"}

            for sel in ['button[data-item-id="address"]', 'button[aria-label*="Endereço"]', 'button[aria-label*="Address"]']:
                try:
                    dados["Endereço"] = driver.find_element(By.CSS_SELECTOR, sel).find_element(By.CLASS_NAME, "Io6YTe").text.strip()
                    break
                except Exception: pass

            for sel in ['button[data-item-id^="phone:tel"]', 'button[aria-label*="Telefone"]', 'button[aria-label*="Phone"]']:
                try:
                    dados["Telefone"] = driver.find_element(By.CSS_SELECTOR, sel).find_element(By.CLASS_NAME, "Io6YTe").text.strip()
                    break
                except Exception: pass

            for sel in ['a[data-item-id="authority"]', 'a[aria-label*="Site"]', 'a[aria-label*="Website"]']:
                try:
                    href = driver.find_element(By.CSS_SELECTOR, sel).get_attribute("href")
                    if href: dados["Site"] = href; break
                except Exception: pass

            if dados["Endereço"] == "N/A" or dados["Telefone"] == "N/A":
                for el in driver.find_elements(By.CLASS_NAME, "Io6YTe"):
                    txt = el.text.strip()
                    if not txt: continue
                    if dados["Telefone"] == "N/A" and any(c.isdigit() for c in txt) and ("(" in txt or txt.startswith("+") or txt.startswith("0")):
                        dados["Telefone"] = txt
                    elif dados["Endereço"] == "N/A" and ("," in txt or " - " in txt) and len(txt) > 10:
                        dados["Endereço"] = txt

            try:
                dados["Avaliação"] = driver.find_element(By.CSS_SELECTOR, 'span[aria-hidden="true"].ceNzKf, div.F7nice span[aria-hidden="true"]').text.strip()
            except Exception: pass
            try:
                el = driver.find_element(By.CSS_SELECTOR, 'span[aria-label*="avaliações"], span[aria-label*="reviews"]')
                txt = el.get_attribute("aria-label") or el.text
                dados["Nº Avaliações"] = "".join(c for c in txt if c.isdigit() or c == ".")
            except Exception: pass
            try:
                dados["Categoria"] = driver.find_element(By.CSS_SELECTOR, 'button[jsaction*="category"], span.DkEaL').text.strip()
            except Exception: pass

            return dados
        except Exception:
            if t < tentativas - 1: time.sleep(2)
    return None


# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(page_title="Gerar Lead | Google Maps Scraper", layout="wide", page_icon="📍")
st.markdown(CSS, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────
if "logado" not in st.session_state:
    st.session_state["logado"] = False
if "login_erro" not in st.session_state:
    st.session_state["login_erro"] = False

# ─────────────────────────────────────────────
# ── TELA DE LOGIN ─────────────────────────────
# ─────────────────────────────────────────────
if not st.session_state["logado"]:

    # HERO
    st.markdown("""
    <div class="hero">
        <div class="grid-bg"></div>
        <div class="badge"><span class="badge-dot"></span>Plataforma de Geração de Leads</div>
        <div class="hero-title">Extraia leads do<br><span>Google Maps</span><br>em segundos.</div>
        <p class="hero-sub">
            Encontre empresas, telefones, sites e avaliações de qualquer segmento,
            em qualquer cidade — de forma automática e escalável.
        </p>
        <div class="stats-row">
            <div class="stat-item">
                <div class="stat-num">100%</div>
                <div class="stat-label">dos resultados</div>
            </div>
            <div class="stat-div"></div>
            <div class="stat-item">
                <div class="stat-num">6+</div>
                <div class="stat-label">campos extraídos</div>
            </div>
            <div class="stat-div"></div>
            <div class="stat-item">
                <div class="stat-num">Excel</div>
                <div class="stat-label">exportação direta</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # FEATURES
    st.markdown("""
    <div class="features">
        <div class="feat-card">
            <div class="feat-icon">📍</div>
            <div class="feat-title">Busca Inteligente</div>
            <div class="feat-desc">Pesquise qualquer nicho em qualquer cidade do Brasil.</div>
        </div>
        <div class="feat-card">
            <div class="feat-icon">⚡</div>
            <div class="feat-title">Extração Total</div>
            <div class="feat-desc">Sem limites. Todos os resultados do Google Maps extraídos.</div>
        </div>
        <div class="feat-card">
            <div class="feat-icon">📊</div>
            <div class="feat-title">Base Acumulada</div>
            <div class="feat-desc">Histórico persistente de todas as suas pesquisas anteriores.</div>
        </div>
        <div class="feat-card">
            <div class="feat-icon">📥</div>
            <div class="feat-title">Export Excel</div>
            <div class="feat-desc">Download imediato em .xlsx pronto para seu CRM.</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # LOGIN CARD
    st.markdown('<div class="login-wrap"><div class="login-card">', unsafe_allow_html=True)
    st.markdown("""
        <div class="login-icon">🔐</div>
        <div class="login-title">Acesso Restrito</div>
        <div class="login-sub">Entre com suas credenciais para continuar</div>
    """, unsafe_allow_html=True)

    if st.session_state["login_erro"]:
        st.markdown('<div class="login-error">⚠️ Usuário ou senha incorretos. Tente novamente.</div>', unsafe_allow_html=True)

    usuario = st.text_input("Usuário", placeholder="Digite seu usuário", key="inp_user")
    senha   = st.text_input("Senha",   placeholder="Digite sua senha",   type="password", key="inp_pass")

    if st.button("Entrar →", use_container_width=True):
        if usuario == USUARIO_CORRETO and senha == SENHA_CORRETA:
            st.session_state["logado"] = True
            st.session_state["login_erro"] = False
            st.rerun()
        else:
            st.session_state["login_erro"] = True
            st.rerun()

    st.markdown('</div></div>', unsafe_allow_html=True)

    # FOOTER
    st.markdown("""
    <div class="custom-footer">
        Desenvolvido por <b>Rodrigo AIOSA</b>
        <div class="footer-icons">
            <a href="https://wa.me/5511977019335" target="_blank">
                <img src="https://cdn-icons-png.flaticon.com/512/733/733585.png" width="22">
            </a>
            <a href="https://www.linkedin.com/in/rodrigoaiosa/" target="_blank">
                <img src="https://cdn-icons-png.flaticon.com/512/174/174857.png" width="22">
            </a>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.stop()


# ─────────────────────────────────────────────
# ── APP PRINCIPAL (pós-login) ─────────────────
# ─────────────────────────────────────────────
arquivo_excel = "base_dados_total.xlsx"

# Header do app
col_logo, col_sair = st.columns([8, 1])
with col_logo:
    st.markdown("""
    <div class="app-header">
        <div class="app-logo">📍</div>
        <div>
            <div class="app-logo-text">Gerar Lead</div>
            <div class="app-logo-sub">Google Maps Scraper</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
with col_sair:
    st.markdown("<br><br>", unsafe_allow_html=True)
    if st.button("Sair ↗"):
        st.session_state["logado"] = False
        st.rerun()

# Busca
st.markdown("### 🔎 Nova Extração")
termo_final = st.text_input(
    "O que você deseja buscar?",
    placeholder="Ex: Farmácias em Osasco SP",
)

if st.button("🚀 Iniciar Extração", use_container_width=True):
    if not termo_final:
        st.warning("Por favor, digite um termo de busca.")
    else:
        driver = configurar_driver()
        status_info  = st.empty()
        barra_progresso = st.progress(0)
        log_erros = []

        try:
            url_busca = f"https://www.google.com.br/maps/search/{termo_final.replace(' ', '+')}"
            driver.get(url_busca)
            status_info.info(f"🔎 Buscando por: '{termo_final}'...")

            elementos = rolar_ate_o_fim(driver, status_info)
            df_atual = pd.DataFrame([{
                "Termo Pesquisado": termo_final,
                "Empresa": el.get_attribute("aria-label"),
                "Link": el.get_attribute("href"),
                "Endereço": "Pendente", "Telefone": "Pendente",
                "Site": "Pendente", "Avaliação": "Pendente",
                "Nº Avaliações": "Pendente", "Categoria": "Pendente",
            } for el in elementos])

            df_atual = df_atual.drop_duplicates(subset=["Link"]).reset_index(drop=True)
            total = len(df_atual)
            st.info(f"📋 Processando **{total}** empresas únicas...")

            for i in range(total):
                empresa = df_atual.at[i, "Empresa"]
                status_info.text(f"⚙️ Extraindo ({i+1}/{total}): {empresa}")
                barra_progresso.progress((i + 1) / total)
                detalhes = extrair_detalhes(driver, df_atual.at[i, "Link"])
                if detalhes:
                    for campo in ["Endereço", "Telefone", "Site", "Avaliação", "Nº Avaliações", "Categoria"]:
                        df_atual.at[i, campo] = detalhes.get(campo, "N/A")
                else:
                    log_erros.append(empresa)
                    for campo in ["Endereço", "Telefone", "Site", "Avaliação", "Nº Avaliações", "Categoria"]:
                        df_atual.at[i, campo] = "Erro"

            if os.path.exists(arquivo_excel):
                df_hist  = pd.read_excel(arquivo_excel)
                df_final = pd.concat([df_hist, df_atual], ignore_index=True)
                df_final = df_final.drop_duplicates(subset=["Link"], keep="last")
                df_final.to_excel(arquivo_excel, index=False)
            else:
                df_atual.to_excel(arquivo_excel, index=False)

            st.session_state["df_resultado"] = df_atual

            if log_erros:
                with st.expander(f"⚠️ {len(log_erros)} empresa(s) com erro"):
                    for e in log_erros: st.write(f"• {e}")

            st.success(f"✅ Concluído! **{total - len(log_erros)}** extraídos | **{len(log_erros)}** com erro.")

        except Exception as e:
            st.error(f"Erro crítico: {e}")
        finally:
            driver.quit()

# Resultados
if "df_resultado" in st.session_state:
    st.divider()
    st.markdown("### 📊 Resultados")
    df = st.session_state["df_resultado"]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total extraído",   len(df))
    c2.metric("Com telefone",     (df["Telefone"] != "N/A").sum())
    c3.metric("Com site",         (df["Site"]     != "N/A").sum())
    c4.metric("Com endereço",     (df["Endereço"] != "N/A").sum())

    st.dataframe(df, use_container_width=True)

    if os.path.exists(arquivo_excel):
        with open(arquivo_excel, "rb") as f:
            st.download_button(
                label="📥 Baixar Base Completa (Excel)",
                data=f,
                file_name="base_leads_acumulada.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

# Footer
st.markdown("""
<div class="custom-footer">
    Desenvolvido por <b>Rodrigo AIOSA</b>
    <div class="footer-icons">
        <a href="https://wa.me/5511977019335" target="_blank">
            <img src="https://cdn-icons-png.flaticon.com/512/733/733585.png" width="22">
        </a>
        <a href="https://www.linkedin.com/in/rodrigoaiosa/" target="_blank">
            <img src="https://cdn-icons-png.flaticon.com/512/174/174857.png" width="22">
        </a>
    </div>
</div>
""", unsafe_allow_html=True)
