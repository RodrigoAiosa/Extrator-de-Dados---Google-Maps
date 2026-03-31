import streamlit as st
import pandas as pd
import time
import os
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/119.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64) Chrome/118.0.0.0"
]

MAX_THREADS = 3  # ⚠️ cuidado: mais que isso aumenta bloqueio

# ─────────────────────────────────────────────
# DRIVER COM ANTI-BLOQUEIO
# ─────────────────────────────────────────────

def configurar_driver():
    options = Options()

    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-extensions")
    options.add_argument("--window-size=1920,1080")

    # Rotação de user-agent
    options.add_argument(f"user-agent={random.choice(USER_AGENTS)}")

    service = Service("/usr/bin/chromedriver")

    driver = webdriver.Chrome(service=service, options=options)

    # Anti-detection JS
    driver.execute_script("""
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined})
    """)

    return driver

# ─────────────────────────────────────────────
# SCROLL COMPLETO
# ─────────────────────────────────────────────

def rolar_ate_o_fim(driver):
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.XPATH, '//div[@role="feed"]'))
    )

    painel = driver.find_element(By.XPATH, '//div[@role="feed"]')

    ultimo = 0

    while True:
        driver.execute_script(
            "arguments[0].scrollTop = arguments[0].scrollHeight", painel
        )

        time.sleep(random.uniform(2, 3))  # delay humano

        elementos = driver.find_elements(By.CLASS_NAME, "hfpxzc")
        atual = len(elementos)

        if atual == ultimo:
            break

        ultimo = atual

    return elementos

# ─────────────────────────────────────────────
# EXTRAÇÃO SEGURA (THREAD)
# ─────────────────────────────────────────────

def extrair_detalhes_thread(link):
    driver = configurar_driver()

    try:
        driver.get(link)

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "Io6YTe"))
        )

        time.sleep(random.uniform(1, 2))

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

    finally:
        driver.quit()

# ─────────────────────────────────────────────
# STREAMLIT UI
# ─────────────────────────────────────────────

st.set_page_config(page_title="Maps Extractor PRO", layout="wide")
st.title("🚀 Maps Extractor PRO")

termo = st.text_input("Busca", placeholder="Ex: Restaurantes em São Paulo")

if st.button("🚀 Extrair"):

    driver = configurar_driver()

    url = f"https://www.google.com/maps/search/{termo.replace(' ', '+')}"
    driver.get(url)

    st.info("🔄 Coletando lista de empresas...")

    elementos = rolar_ate_o_fim(driver)

    # 🔥 ANTI-STALE
    lista = []
    for el in elementos:
        try:
            nome = el.get_attribute("aria-label")
            link = el.get_attribute("href")

            if nome and link:
                lista.append({"Empresa": nome, "Link": link})
        except:
            continue

    driver.quit()

    total = len(lista)
    st.success(f"📊 {total} empresas encontradas")

    progresso = st.progress(0)

    resultados = []

    # ─────────────────────────────────────────
    # MULTITHREAD CONTROLADO
    # ─────────────────────────────────────────

    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:

        futures = {
            executor.submit(extrair_detalhes_thread, item["Link"]): item
            for item in lista
        }

        for i, future in enumerate(as_completed(futures)):
            item = futures[future]

            try:
                detalhes = future.result()

                if detalhes:
                    resultados.append({
                        "Empresa": item["Empresa"],
                        "Link": item["Link"],
                        **detalhes
                    })

            except:
                continue

            progresso.progress((i + 1) / total)

    df = pd.DataFrame(resultados)

    arquivo = "leads.xlsx"
    df.to_excel(arquivo, index=False)

    st.success("✅ Extração finalizada")
    st.dataframe(df)

    with open(arquivo, "rb") as f:
        st.download_button("📥 Baixar Excel", f, "leads.xlsx")
