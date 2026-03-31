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
# CONFIGURAÇÃO DO DRIVER
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
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
    options.binary_location = "/usr/bin/chromium"
    service = Service("/usr/bin/chromedriver")
    driver = webdriver.Chrome(service=service, options=options)
    return driver


# ─────────────────────────────────────────────
# ROLAGEM COMPLETA — carrega TODOS os resultados
# ─────────────────────────────────────────────

def rolar_ate_o_fim(driver, status_widget, max_tentativas_sem_novos=5):
    """
    Rola o painel de resultados até que nenhum novo item apareça
    em `max_tentativas_sem_novos` tentativas consecutivas.
    Não há limite máximo de itens.
    """
    wait = WebDriverWait(driver, 15)
    wait.until(EC.presence_of_element_located((By.XPATH, '//div[@role="feed"]')))

    painel = driver.find_element(By.XPATH, '//div[@role="feed"]')
    tentativas_sem_novos = 0
    ultimo_count = 0

    while True:
        # Rola até o fim do painel
        driver.execute_script(
            "arguments[0].scrollTop = arguments[0].scrollHeight", painel
        )
        time.sleep(2.5)  # aguarda carregamento lazy

        elementos = driver.find_elements(By.CLASS_NAME, "hfpxzc")
        count_atual = len(elementos)
        status_widget.text(f"🔍 Locais identificados: {count_atual} — aguardando mais resultados...")

        if count_atual == ultimo_count:
            tentativas_sem_novos += 1
        else:
            tentativas_sem_novos = 0  # resetar contador se novos itens aparecerem

        ultimo_count = count_atual

        # Verifica se chegou ao fim da lista (mensagem do Google Maps)
        fim_lista = driver.find_elements(
            By.XPATH,
            '//*[contains(text(),"Você chegou ao fim da lista")]'
            '| //*[contains(text(),"You\'ve reached the end of the list")]'
        )
        if fim_lista:
            status_widget.text(f"✅ Fim da lista detectado! Total: {count_atual} locais.")
            break

        if tentativas_sem_novos >= max_tentativas_sem_novos:
            status_widget.text(f"✅ Nenhum novo resultado após {max_tentativas_sem_novos} tentativas. Total: {count_atual} locais.")
            break

    return driver.find_elements(By.CLASS_NAME, "hfpxzc")


# ─────────────────────────────────────────────
# EXTRAÇÃO DE DETALHES — múltiplas estratégias
# ─────────────────────────────────────────────

def extrair_detalhes(driver, link, tentativas=3):
    """
    Acessa a página do local e extrai endereço, telefone e site
    usando múltiplas estratégias de seleção CSS/XPath.
    """
    for tentativa in range(tentativas):
        try:
            driver.get(link)
            # Aguarda o painel de detalhes carregar
            WebDriverWait(driver, 12).until(
                EC.presence_of_element_located((By.CLASS_NAME, "Io6YTe"))
            )
            time.sleep(1.5)

            dados = {"Endereço": "N/A", "Telefone": "N/A", "Site": "N/A", "Avaliação": "N/A", "Nº Avaliações": "N/A", "Categoria": "N/A"}

            # ── Endereço ──────────────────────────────────────────────────
            seletores_endereco = [
                'button[data-item-id="address"]',
                '[data-tooltip="Copiar endereço"]',
                'button[aria-label*="Endereço"]',
                'button[aria-label*="Address"]',
            ]
            for sel in seletores_endereco:
                try:
                    el = driver.find_element(By.CSS_SELECTOR, sel)
                    texto = el.find_element(By.CLASS_NAME, "Io6YTe").text.strip()
                    if texto:
                        dados["Endereço"] = texto
                        break
                except Exception:
                    pass

            # ── Telefone ──────────────────────────────────────────────────
            seletores_telefone = [
                'button[data-item-id^="phone:tel"]',
                '[data-tooltip="Copiar número de telefone"]',
                'button[aria-label*="Telefone"]',
                'button[aria-label*="Phone"]',
            ]
            for sel in seletores_telefone:
                try:
                    el = driver.find_element(By.CSS_SELECTOR, sel)
                    texto = el.find_element(By.CLASS_NAME, "Io6YTe").text.strip()
                    if texto:
                        dados["Telefone"] = texto
                        break
                except Exception:
                    pass

            # ── Site ──────────────────────────────────────────────────────
            seletores_site = [
                'a[data-item-id="authority"]',
                'a[aria-label*="Site"]',
                'a[aria-label*="Website"]',
            ]
            for sel in seletores_site:
                try:
                    el = driver.find_element(By.CSS_SELECTOR, sel)
                    href = el.get_attribute("href")
                    if href:
                        dados["Site"] = href
                        break
                except Exception:
                    pass

            # ── Fallback geral: varre todos os Io6YTe ─────────────────────
            if dados["Endereço"] == "N/A" or dados["Telefone"] == "N/A":
                elementos_info = driver.find_elements(By.CLASS_NAME, "Io6YTe")
                for el in elementos_info:
                    texto = el.text.strip()
                    if not texto:
                        continue
                    # Heurística telefone: contém dígitos e parênteses ou traço
                    if dados["Telefone"] == "N/A":
                        if any(c.isdigit() for c in texto) and (
                            "(" in texto or texto.startswith("+") or texto.startswith("0")
                        ):
                            dados["Telefone"] = texto
                            continue
                    # Heurística endereço: contém vírgula ou traço entre texto
                    if dados["Endereço"] == "N/A":
                        if ("," in texto or " - " in texto) and len(texto) > 10:
                            dados["Endereço"] = texto

            # ── Avaliação ─────────────────────────────────────────────────
            try:
                rating_el = driver.find_element(
                    By.CSS_SELECTOR, 'span[aria-hidden="true"].ceNzKf, div.F7nice span[aria-hidden="true"]'
                )
                dados["Avaliação"] = rating_el.text.strip()
            except Exception:
                pass

            try:
                reviews_el = driver.find_element(
                    By.CSS_SELECTOR, 'span[aria-label*="avaliações"], span[aria-label*="reviews"]'
                )
                txt = reviews_el.get_attribute("aria-label") or reviews_el.text
                # Extrai só os números
                numeros = "".join(filter(lambda c: c.isdigit() or c == ".", txt))
                dados["Nº Avaliações"] = numeros if numeros else txt
            except Exception:
                pass

            # ── Categoria ─────────────────────────────────────────────────
            try:
                cat_el = driver.find_element(
                    By.CSS_SELECTOR,
                    'button[jsaction*="category"], span.DkEaL'
                )
                dados["Categoria"] = cat_el.text.strip()
            except Exception:
                pass

            return dados

        except Exception:
            if tentativa < tentativas - 1:
                time.sleep(2)
            else:
                return None

    return None


# ─────────────────────────────────────────────
# INTERFACE STREAMLIT
# ─────────────────────────────────────────────

st.set_page_config(page_title="Google Maps Scraper", layout="wide", page_icon="📍")
st.title("📍 Extrator de Dados — Google Maps")
st.caption("Extrai **100% dos resultados** da busca: endereço, telefone, site, avaliação, categoria e mais.")

termo_final = st.text_input(
    "O que você deseja buscar?",
    placeholder="Ex: Fabricantes de móveis em SP",
)

arquivo_excel = "base_dados_total.xlsx"

if st.button("🚀 Iniciar Extração", use_container_width=True):
    if not termo_final:
        st.warning("Por favor, digite um termo de busca.")
    else:
        driver = configurar_driver()
        status_info = st.empty()
        barra_progresso = st.progress(0)
        log_erros = []

        try:
            url_busca = (
                f"https://www.google.com.br/maps/search/{termo_final.replace(' ', '+')}"
            )
            driver.get(url_busca)
            status_info.info(f"🔎 Buscando por: '{termo_final}'...")

            # ── Rolagem total ──────────────────────────────────────────────
            elementos = rolar_ate_o_fim(driver, status_info)

            # ── Monta DataFrame inicial ───────────────────────────────────
            df_atual = pd.DataFrame(
                [
                    {
                        "Termo Pesquisado": termo_final,
                        "Empresa": el.get_attribute("aria-label"),
                        "Link": el.get_attribute("href"),
                        "Endereço": "Pendente",
                        "Telefone": "Pendente",
                        "Site": "Pendente",
                        "Avaliação": "Pendente",
                        "Nº Avaliações": "Pendente",
                        "Categoria": "Pendente",
                    }
                    for el in elementos
                ]
            )
            df_atual = df_atual.drop_duplicates(subset=["Link"]).reset_index(drop=True)
            total_locais = len(df_atual)
            st.info(f"📋 Processando **{total_locais}** empresas únicas...")

            # ── Extração de detalhes ──────────────────────────────────────
            for i in range(total_locais):
                empresa = df_atual.at[i, "Empresa"]
                status_info.text(f"⚙️ Extraindo ({i+1}/{total_locais}): {empresa}")
                barra_progresso.progress((i + 1) / total_locais)

                detalhes = extrair_detalhes(driver, df_atual.at[i, "Link"])

                if detalhes:
                    for campo in ["Endereço", "Telefone", "Site", "Avaliação", "Nº Avaliações", "Categoria"]:
                        df_atual.at[i, campo] = detalhes.get(campo, "N/A")
                else:
                    log_erros.append(empresa)
                    for campo in ["Endereço", "Telefone", "Site", "Avaliação", "Nº Avaliações", "Categoria"]:
                        df_atual.at[i, campo] = "Erro"

            # ── Persistência acumulada ────────────────────────────────────
            if os.path.exists(arquivo_excel):
                df_hist = pd.read_excel(arquivo_excel)
                df_final = pd.concat([df_hist, df_atual], ignore_index=True)
                df_final = df_final.drop_duplicates(subset=["Link"], keep="last")
                df_final.to_excel(arquivo_excel, index=False)
            else:
                df_atual.to_excel(arquivo_excel, index=False)

            st.session_state["df_resultado"] = df_atual

            if log_erros:
                with st.expander(f"⚠️ {len(log_erros)} empresa(s) com erro na extração"):
                    for e in log_erros:
                        st.write(f"• {e}")

            st.success(
                f"✅ Extração finalizada! **{total_locais - len(log_erros)}** extraídos com sucesso, "
                f"**{len(log_erros)}** com erro."
            )

        except Exception as e:
            st.error(f"Ocorreu um erro crítico: {e}")
        finally:
            driver.quit()

# ─────────────────────────────────────────────
# EXIBIÇÃO E DOWNLOAD
# ─────────────────────────────────────────────

if "df_resultado" in st.session_state:
    st.divider()
    st.subheader("📊 Resultados desta pesquisa")

    df_show = st.session_state["df_resultado"]
    st.dataframe(df_show, use_container_width=True)

    # Métricas rápidas
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total extraído", len(df_show))
    c2.metric("Com telefone", (df_show["Telefone"] != "N/A").sum())
    c3.metric("Com site", (df_show["Site"] != "N/A").sum())
    c4.metric("Com endereço", (df_show["Endereço"] != "N/A").sum())

    if os.path.exists(arquivo_excel):
        with open(arquivo_excel, "rb") as f:
            st.download_button(
                label="📥 Baixar Base Completa (Excel)",
                data=f,
                file_name="base_leads_acumulada.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

# ─────────────────────────────────────────────
# RODAPÉ
# ─────────────────────────────────────────────

st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray;'>
        <p style='margin-bottom: 5px;'>Desenvolvido por <b>Rodrigo AIOSA</b></p>
        <div style='display: flex; justify-content: center; gap: 20px;'>
            <a href='https://wa.me/5511977019335' target='_blank'>
                <img src='https://cdn-icons-png.flaticon.com/512/733/733585.png' width='25' height='25' title='WhatsApp'>
            </a>
            <a href='https://www.linkedin.com/in/rodrigoaiosa/' target='_blank'>
                <img src='https://cdn-icons-png.flaticon.com/512/174/174857.png' width='25' height='25' title='LinkedIn'>
            </a>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)
