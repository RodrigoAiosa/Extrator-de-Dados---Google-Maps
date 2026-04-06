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
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from functools import lru_cache, wraps
import asyncio
import aiohttp
from threading import Lock
import logging
from abc import ABC, abstractmethod

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# DECORATORS
# ─────────────────────────────────────────────
def timer_decorator(func):
    """Decorador para medir tempo de execução"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        logger.info(f"{func.__name__} executado em {elapsed:.2f} segundos")
        return result
    return wrapper

def retry_decorator(max_attempts=3, delay=1.0, backoff=2):
    """Decorador para retry automático"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempts = 0
            current_delay = delay
            while attempts < max_attempts:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    attempts += 1
                    if attempts == max_attempts:
                        raise
                    logger.warning(f"Tentativa {attempts} falhou para {func.__name__}: {e}. Retentando em {current_delay}s...")
                    time.sleep(current_delay)
                    current_delay *= backoff
            return None
        return wrapper
    return decorator

# ─────────────────────────────────────────────
# DATA CLASSES
# ─────────────────────────────────────────────
@dataclass
class BusinessData:
    """Classe de dados para armazenar informações da empresa"""
    empresa: str
    link: str
    termo_pesquisado: str
    endereco: str = "N/A"
    telefone: str = "N/A"
    site: str = "N/A"
    avaliacao: str = "N/A"
    numero_avaliacoes: str = "N/A"
    categoria: str = "N/A"
    
    def to_dict(self) -> Dict:
        """Converte para dicionário"""
        return {
            "Termo Pesquisado": self.termo_pesquisado,
            "Empresa": self.empresa,
            "Link": self.link,
            "Endereço": self.endereco,
            "Telefone": self.telefone,
            "Site": self.site,
            "Avaliação": self.avaliacao,
            "Nº Avaliações": self.numero_avaliacoes,
            "Categoria": self.categoria,
        }

@dataclass
class ExtractionConfig:
    """Configuração da extração"""
    max_workers: int = 5
    scroll_wait_time: float = 1.5
    detail_wait_time: float = 1.0
    max_no_new_items: int = 5
    batch_size: int = 10

# ─────────────────────────────────────────────
# ABSTRACT BASE CLASSES
# ─────────────────────────────────────────────
class WebDriverFactory(ABC):
    """Factory abstrata para criação de WebDriver"""
    
    @abstractmethod
    def create_driver(self) -> webdriver.Chrome:
        pass

class DataExtractor(ABC):
    """Extrator abstrato de dados"""
    
    @abstractmethod
    def extract_businesses(self, driver: webdriver.Chrome, search_term: str) -> List[BusinessData]:
        pass
    
    @abstractmethod
    def extract_business_details(self, driver: webdriver.Chrome, business: BusinessData) -> BusinessData:
        pass

# ─────────────────────────────────────────────
# CONCRETE IMPLEMENTATIONS
# ─────────────────────────────────────────────
class ChromeDriverFactory(WebDriverFactory):
    """Factory para criação de ChromeDriver otimizado"""
    
    @staticmethod
    def _get_chrome_options() -> Options:
        """Configura opções otimizadas do Chrome"""
        options = Options()
        
        # Otimizações de performance
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--remote-debugging-port=9222")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-setuid-sandbox")
        options.add_argument("--disable-web-security")
        options.add_argument("--disable-features=VizDisplayCompositor")
        options.add_argument("--disable-logging")
        options.add_argument("--log-level=3")
        options.add_argument("--silent")
        
        # Cache e performance
        options.add_argument("--disk-cache-size=0")
        options.add_argument("--media-cache-size=0")
        options.add_argument("--aggressive-cache-discard")
        
        # User agent realista
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        # Preferências de performance
        prefs = {
            "profile.default_content_setting_values.notifications": 2,
            "profile.default_content_settings.popups": 0,
            "profile.managed_default_content_settings.images": 2,
            "disk-cache-size": 4096,
        }
        options.add_experimental_option("prefs", prefs)
        
        return options
    
    def create_driver(self) -> webdriver.Chrome:
        """Cria e retorna uma instância do ChromeDriver"""
        options = self._get_chrome_options()
        
        # Tenta webdriver-manager
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            from webdriver_manager.core.os_manager import ChromeType
            
            for chrome_type in [ChromeType.CHROMIUM, None]:
                try:
                    if chrome_type:
                        service = Service(ChromeDriverManager(chrome_type=chrome_type).install())
                        binary = shutil.which("chromium") or shutil.which("chromium-browser")
                        if binary:
                            options.binary_location = binary
                    else:
                        service = Service(ChromeDriverManager().install())
                    
                    driver = webdriver.Chrome(service=service, options=options)
                    driver.set_page_load_timeout(30)
                    return driver
                except Exception:
                    continue
        except Exception:
            pass
        
        # Fallback para paths conhecidos
        BROWSER_PATHS = ["/usr/bin/chromium", "/usr/bin/chromium-browser", "/usr/bin/google-chrome"]
        DRIVER_PATHS = ["/usr/bin/chromedriver", "/usr/local/bin/chromedriver", shutil.which("chromedriver") or ""]
        
        browser = next((p for p in BROWSER_PATHS if os.path.exists(p)), None)
        driver_bin = next((p for p in DRIVER_PATHS if p and os.path.exists(p)), None)
        
        if browser:
            options.binary_location = browser
        if driver_bin:
            return webdriver.Chrome(service=Service(driver_bin), options=options)
        
        return webdriver.Chrome(options=options)

class MapsDataExtractor(DataExtractor):
    """Extrator de dados do Google Maps"""
    
    def __init__(self, config: ExtractionConfig):
        self.config = config
        self._lock = Lock()
        self._selectors_cache = {}
    
    @timer_decorator
    def extract_businesses(self, driver: webdriver.Chrome, search_term: str) -> List[BusinessData]:
        """Extrai lista de empresas da página de busca"""
        url = f"https://www.google.com.br/maps/search/{search_term.replace(' ', '+')}"
        driver.get(url)
        
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, '//div[@role="feed"]'))
        )
        
        businesses = self._scroll_and_collect(driver)
        return self._create_business_objects(businesses, search_term)
    
    def _scroll_and_collect(self, driver: webdriver.Chrome) -> List:
        """Rola a página e coleta elementos"""
        painel = driver.find_element(By.XPATH, '//div[@role="feed"]')
        sem_novos = 0
        ultimo = 0
        elementos = []
        
        while True:
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", painel)
            time.sleep(self.config.scroll_wait_time)
            
            novos_elementos = driver.find_elements(By.CLASS_NAME, "hfpxzc")
            elementos = novos_elementos
            
            total = len(elementos)
            
            if total == ultimo:
                sem_novos += 1
            else:
                sem_novos = 0
            
            ultimo = total
            
            fim = driver.find_elements(
                By.XPATH,
                '//*[contains(text(),"Você chegou ao fim")]|//*[contains(text(),"end of the list")]'
            )
            
            if fim or sem_novos >= self.config.max_no_new_items:
                break
        
        return elementos
    
    def _create_business_objects(self, elements: List, search_term: str) -> List[BusinessData]:
        """Cria objetos BusinessData a partir dos elementos"""
        businesses = []
        seen_links = set()
        
        for el in elements:
            link = el.get_attribute("href")
            if link and link not in seen_links:
                seen_links.add(link)
                businesses.append(BusinessData(
                    empresa=el.get_attribute("aria-label") or "N/A",
                    link=link,
                    termo_pesquisado=search_term
                ))
        
        return businesses
    
    @retry_decorator(max_attempts=2, delay=1.0)
    def extract_business_details(self, driver: webdriver.Chrome, business: BusinessData) -> BusinessData:
        """Extrai detalhes de uma empresa específica"""
        driver.get(business.link)
        WebDriverWait(driver, 12).until(
            EC.presence_of_element_located((By.CLASS_NAME, "Io6YTe"))
        )
        time.sleep(self.config.detail_wait_time)
        
        # Extrai dados usando métodos otimizados
        business.endereco = self._extract_address(driver)
        business.telefone = self._extract_phone(driver)
        business.site = self._extract_website(driver)
        business.avaliacao = self._extract_rating(driver)
        business.numero_avaliacoes = self._extract_review_count(driver)
        business.categoria = self._extract_category(driver)
        
        # Fallback para dados perdidos
        self._fallback_extraction(driver, business)
        
        return business
    
    def _extract_address(self, driver: webdriver.Chrome) -> str:
        """Extrai endereço usando múltiplos seletores"""
        selectors = [
            'button[data-item-id="address"]',
            'button[aria-label*="Endereço"]',
            'button[aria-label*="Address"]'
        ]
        return self._try_extract_text(driver, selectors)
    
    def _extract_phone(self, driver: webdriver.Chrome) -> str:
        """Extrai telefone usando múltiplos seletores"""
        selectors = [
            'button[data-item-id^="phone:tel"]',
            'button[aria-label*="Telefone"]',
            'button[aria-label*="Phone"]'
        ]
        return self._try_extract_text(driver, selectors)
    
    def _extract_website(self, driver: webdriver.Chrome) -> str:
        """Extrai website"""
        selectors = [
            'a[data-item-id="authority"]',
            'a[aria-label*="Site"]',
            'a[aria-label*="Website"]'
        ]
        
        for selector in selectors:
            try:
                element = driver.find_element(By.CSS_SELECTOR, selector)
                href = element.get_attribute("href")
                if href:
                    return href
            except Exception:
                continue
        return "N/A"
    
    def _extract_rating(self, driver: webdriver.Chrome) -> str:
        """Extrai avaliação"""
        try:
            return driver.find_element(
                By.CSS_SELECTOR,
                'span[aria-hidden="true"].ceNzKf, div.F7nice span[aria-hidden="true"]'
            ).text.strip()
        except Exception:
            return "N/A"
    
    def _extract_review_count(self, driver: webdriver.Chrome) -> str:
        """Extrai número de avaliações"""
        try:
            element = driver.find_element(
                By.CSS_SELECTOR,
                'span[aria-label*="avaliações"], span[aria-label*="reviews"]'
            )
            txt = element.get_attribute("aria-label") or element.text
            return "".join(c for c in txt if c.isdigit() or c == ".")
        except Exception:
            return "N/A"
    
    def _extract_category(self, driver: webdriver.Chrome) -> str:
        """Extrai categoria"""
        try:
            return driver.find_element(
                By.CSS_SELECTOR,
                'button[jsaction*="category"], span.DkEaL'
            ).text.strip()
        except Exception:
            return "N/A"
    
    def _try_extract_text(self, driver: webdriver.Chrome, selectors: List[str]) -> str:
        """Tenta extrair texto usando múltiplos seletores"""
        for selector in selectors:
            try:
                element = driver.find_element(By.CSS_SELECTOR, selector)
                text = element.find_element(By.CLASS_NAME, "Io6YTe").text.strip()
                if text:
                    return text
            except Exception:
                continue
        return "N/A"
    
    def _fallback_extraction(self, driver: webdriver.Chrome, business: BusinessData):
        """Fallback para extrair dados perdidos"""
        if business.endereco == "N/A" or business.telefone == "N/A":
            elements = driver.find_elements(By.CLASS_NAME, "Io6YTe")
            for el in elements:
                txt = el.text.strip()
                if not txt:
                    continue
                
                if business.telefone == "N/A" and (any(c.isdigit() for c in txt) and 
                   ("(" in txt or txt.startswith("+") or txt.startswith("0"))):
                    business.telefone = txt
                elif business.endereco == "N/A" and ("," in txt or " - " in txt) and len(txt) > 10:
                    business.endereco = txt

class BatchProcessor:
    """Processador em lote para extração paralela"""
    
    def __init__(self, extractor: DataExtractor, config: ExtractionConfig):
        self.extractor = extractor
        self.config = config
        self._driver_pool = []
        self._driver_lock = Lock()
    
    def _create_driver_pool(self, size: int):
        """Cria pool de drivers"""
        factory = ChromeDriverFactory()
        self._driver_pool = [factory.create_driver() for _ in range(min(size, 10))]
    
    def _get_driver(self) -> webdriver.Chrome:
        """Obtém um driver do pool"""
        with self._driver_lock:
            if not self._driver_pool:
                self._create_driver_pool(self.config.max_workers)
            return self._driver_pool.pop()
    
    def _return_driver(self, driver: webdriver.Chrome):
        """Retorna driver ao pool"""
        with self._driver_lock:
            self._driver_pool.append(driver)
    
    @timer_decorator
    def process_batch(self, businesses: List[BusinessData], progress_callback=None) -> List[BusinessData]:
        """Processa lote de empresas em paralelo"""
        results = []
        total = len(businesses)
        
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            futures = {}
            
            for i, business in enumerate(businesses):
                driver = self._get_driver()
                future = executor.submit(self._process_business, driver, business)
                futures[future] = (i, driver)
            
            for future in as_completed(futures):
                i, driver = futures[future]
                try:
                    result = future.result(timeout=30)
                    results.append((i, result))
                except Exception as e:
                    logger.error(f"Erro ao processar empresa {i}: {e}")
                    results.append((i, businesses[i]))
                finally:
                    self._return_driver(driver)
                
                if progress_callback:
                    progress_callback(len(results), total)
        
        # Ordena resultados pelo índice original
        results.sort(key=lambda x: x[0])
        return [r[1] for r in results]
    
    def _process_business(self, driver: webdriver.Chrome, business: BusinessData) -> BusinessData:
        """Processa uma empresa individual"""
        return self.extractor.extract_business_details(driver, business)
    
    def cleanup(self):
        """Limpa pool de drivers"""
        for driver in self._driver_pool:
            try:
                driver.quit()
            except Exception:
                pass
        self._driver_pool.clear()

class DataManager:
    """Gerencia persistência de dados"""
    
    def __init__(self, filename: str = "base_dados_total.xlsx"):
        self.filename = filename
        self._lock = Lock()
    
    def save_batch(self, businesses: List[BusinessData]) -> pd.DataFrame:
        """Salva lote de empresas no arquivo"""
        df_new = pd.DataFrame([b.to_dict() for b in businesses])
        df_new = df_new.drop_duplicates(subset=["Link"], keep="last")
        
        with self._lock:
            if os.path.exists(self.filename):
                df_existing = pd.read_excel(self.filename)
                df_combined = pd.concat([df_existing, df_new], ignore_index=True)
                df_combined = df_combined.drop_duplicates(subset=["Link"], keep="last")
            else:
                df_combined = df_new
            
            df_combined.to_excel(self.filename, index=False)
        
        return df_new
    
    def load_data(self) -> Optional[pd.DataFrame]:
        """Carrega dados existentes"""
        if os.path.exists(self.filename):
            return pd.read_excel(self.filename)
        return None

# ─────────────────────────────────────────────
# STREAMLIT UI MANAGER
# ─────────────────────────────────────────────
class StreamlitUIManager:
    """Gerencia a interface do Streamlit"""
    
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
    
    @staticmethod
    def render_login_page(error: bool = False):
        """Renderiza página de login"""
        st.markdown(StreamlitUIManager.CSS, unsafe_allow_html=True)
        
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
        
        st.markdown("""
            <div class="login-icon">🔐</div>
            <div class="login-title">Acesso Restrito</div>
            <div class="login-sub">Entre com suas credenciais para continuar</div>
        """, unsafe_allow_html=True)
        
        if error:
            st.markdown('<div class="login-error">⚠️ Usuário ou senha incorretos. Tente novamente.</div>', unsafe_allow_html=True)
    
    @staticmethod
    def render_footer():
        """Renderiza footer"""
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
    
    @staticmethod
    def render_app_header():
        """Renderiza header do app"""
        st.markdown("""
        <div class="app-header">
            <div class="app-logo">📍</div>
            <div>
                <div class="app-logo-text">Gerar Lead</div>
                <div class="app-logo-sub">Google Maps Scraper</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    @staticmethod
    def render_results(df: pd.DataFrame):
        """Renderiza resultados da extração"""
        st.divider()
        st.markdown("### 📊 Resultados")
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total extraído", len(df))
        col2.metric("Com telefone", (df["Telefone"] != "N/A").sum())
        col3.metric("Com site", (df["Site"] != "N/A").sum())
        col4.metric("Com endereço", (df["Endereço"] != "N/A").sum())
        
        st.dataframe(df, use_container_width=True)

# ─────────────────────────────────────────────
# MAIN APPLICATION
# ─────────────────────────────────────────────
class LeadGeneratorApp:
    """Classe principal da aplicação"""
    
    def __init__(self):
        self.ui_manager = StreamlitUIManager()
        self.data_manager = DataManager()
        self.config = ExtractionConfig(
            max_workers=5,
            scroll_wait_time=1.5,
            detail_wait_time=0.8,
            max_no_new_items=5
        )
        self.extractor = MapsDataExtractor(self.config)
        self.processor = None
        
        # Credenciais
        self.USUARIO_CORRETO = "aiosa"
        self.SENHA_CORRETA = "qazwsxedc@"
        
        self._init_session_state()
    
    def _init_session_state(self):
        """Inicializa session state"""
        if "logado" not in st.session_state:
            st.session_state["logado"] = False
        if "login_erro" not in st.session_state:
            st.session_state["login_erro"] = False
    
    def _check_login(self, username: str, password: str) -> bool:
        """Verifica credenciais"""
        return username == self.USUARIO_CORRETO and password == self.SENHA_CORRETA
    
    def run_login_page(self):
        """Executa página de login"""
        self.ui_manager.render_login_page(st.session_state["login_erro"])
        
        usuario = st.text_input("Usuário", placeholder="Digite seu usuário", key="inp_user")
        senha = st.text_input("Senha", placeholder="Digite sua senha", type="password", key="inp_pass")
        
        if st.button("Entrar →", use_container_width=True):
            if self._check_login(usuario, senha):
                st.session_state["logado"] = True
                st.session_state["login_erro"] = False
                st.rerun()
            else:
                st.session_state["login_erro"] = True
                st.rerun()
        
        self.ui_manager.render_footer()
        st.stop()
    
    @timer_decorator
    def run_extraction(self, search_term: str):
        """Executa extração de dados"""
        driver = None
        try:
            # Cria driver para extração inicial
            factory = ChromeDriverFactory()
            driver = factory.create_driver()
            
            # Extrai lista de empresas
            status_placeholder = st.empty()
            status_placeholder.info(f"🔎 Buscando por: '{search_term}'...")
            
            businesses = self.extractor.extract_businesses(driver, search_term)
            total = len(businesses)
            
            if total == 0:
                st.warning("Nenhuma empresa encontrada para este termo.")
                return
            
            status_placeholder.info(f"📋 Encontradas {total} empresas. Iniciando extração detalhada...")
            
            # Prepara processamento paralelo
            self.processor = BatchProcessor(self.extractor, self.config)
            
            # Progresso
            progress_bar = st.progress(0)
            progress_text = st.empty()
            
            def update_progress(current, total):
                progress_bar.progress(current / total)
                progress_text.text(f"⚙️ Processando: {current}/{total} empresas")
            
            # Processa em paralelo
            processed_businesses = self.processor.process_batch(businesses, update_progress)
            
            # Salva resultados
            df_new = self.data_manager.save_batch(processed_businesses)
            
            # Mostra resultados
            success_count = sum(1 for b in processed_businesses if b.telefone != "N/A")
            error_count = total - success_count
            
            if error_count > 0:
                with st.expander(f"⚠️ {error_count} empresa(s) com erro"):
                    for b in processed_businesses:
                        if b.telefone == "N/A":
                            st.write(f"• {b.empresa}")
            
            st.success(f"✅ Concluído! **{success_count}** extraídos | **{error_count}** com erro.")
            
            # Armazena no session state
            st.session_state["df_resultado"] = df_new
            
        except Exception as e:
            logger.error(f"Erro na extração: {e}")
            st.error(f"Erro crítico: {e}")
        finally:
            if driver:
                driver.quit()
            if self.processor:
                self.processor.cleanup()
    
    def run_main_app(self):
        """Executa aplicação principal pós-login"""
        st.set_page_config(page_title="Gerar Lead | Google Maps Scraper", layout="wide", page_icon="📍")
        st.markdown(StreamlitUIManager.CSS, unsafe_allow_html=True)
        
        self.ui_manager.render_app_header()
        
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
                self.run_extraction(termo_final)
        
        # Resultados
        if "df_resultado" in st.session_state:
            self.ui_manager.render_results(st.session_state["df_resultado"])
            
            if os.path.exists("base_dados_total.xlsx"):
                with open("base_dados_total.xlsx", "rb") as f:
                    st.download_button(
                        label="📥 Baixar Base Completa (Excel)",
                        data=f,
                        file_name="base_leads_acumulada.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                    )
        
        self.ui_manager.render_footer()
    
    def run(self):
        """Ponto de entrada da aplicação"""
        st.set_page_config(page_title="Gerar Lead | Google Maps Scraper", layout="wide", page_icon="📍")
        
        if not st.session_state["logado"]:
            self.run_login_page()
        else:
            self.run_main_app()

# ─────────────────────────────────────────────
# EXECUÇÃO
# ─────────────────────────────────────────────
if __name__ == "__main__":
    app = LeadGeneratorApp()
    app.run()
