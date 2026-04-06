import streamlit as st
import pandas as pd
import asyncio
import aiohttp
import time
import os
import shutil
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from multiprocessing import Manager, Queue
from threading import Lock, Semaphore
from queue import PriorityQueue
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any, Set
from functools import lru_cache, wraps
from abc import ABC, abstractmethod
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import pickle
from collections import deque
import hashlib
import json
from datetime import datetime
import numpy as np

# Configuração de logging assíncrono
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# DECORATORS OTIMIZADOS
# ============================================================================

class PerformanceDecorators:
    """Coleção de decorators otimizados para performance"""
    
    @staticmethod
    def async_timer(func):
        """Decorador para medir tempo de execução assíncrono"""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = await func(*args, **kwargs)
            elapsed = time.perf_counter() - start
            logger.info(f"{func.__name__} executado em {elapsed:.3f} segundos")
            return result
        return wrapper
    
    @staticmethod
    def sync_timer(func):
        """Decorador para medir tempo de execução síncrono"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            elapsed = time.perf_counter() - start
            logger.info(f"{func.__name__} executado em {elapsed:.3f} segundos")
            return result
        return wrapper
    
    @staticmethod
    def retry(max_attempts=3, delay=0.5, backoff=2, exceptions=(Exception,)):
        """Decorador de retry com backoff exponencial"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                last_exception = None
                current_delay = delay
                
                for attempt in range(max_attempts):
                    try:
                        return func(*args, **kwargs)
                    except exceptions as e:
                        last_exception = e
                        if attempt == max_attempts - 1:
                            raise
                        
                        logger.warning(
                            f"Tentativa {attempt + 1}/{max_attempts} falhou para "
                            f"{func.__name__}: {e}. Retentando em {current_delay}s..."
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                
                raise last_exception
            return wrapper
        return decorator
    
    @staticmethod
    def cache_result(maxsize=128):
        """Cache com LRU e timeout"""
        def decorator(func):
            cache = {}
            timestamps = {}
            
            @wraps(func)
            def wrapper(*args, **kwargs):
                key = hashlib.md5(
                    f"{args}{kwargs}".encode()
                ).hexdigest()
                
                if key in cache:
                    if time.time() - timestamps[key] < 3600:  # 1 hora de cache
                        return cache[key]
                
                result = func(*args, **kwargs)
                cache[key] = result
                timestamps[key] = time.time()
                
                if len(cache) > maxsize:
                    oldest = min(timestamps, key=timestamps.get)
                    del cache[oldest]
                    del timestamps[oldest]
                
                return result
            return wrapper
        return decorator

# ============================================================================
# DATA CLASSES OTIMIZADAS
# ============================================================================

@dataclass(slots=True)  # slots reduz consumo de memória
class BusinessData:
    """Classe otimizada para armazenamento de dados"""
    empresa: str
    link: str
    termo_pesquisado: str
    endereco: str = "N/A"
    telefone: str = "N/A"
    site: str = "N/A"
    avaliacao: str = "N/A"
    numero_avaliacoes: str = "N/A"
    categoria: str = "N/A"
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict:
        """Conversão otimizada para dicionário"""
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
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'BusinessData':
        """Cria instância a partir de dicionário"""
        return cls(**data)

@dataclass(slots=True)
class ExtractionConfig:
    """Configuração otimizada para extração"""
    max_workers: int = 10
    scroll_wait_time: float = 0.8
    detail_wait_time: float = 0.5
    max_no_new_items: int = 3
    batch_size: int = 20
    connection_timeout: int = 15
    page_load_timeout: int = 20
    driver_pool_size: int = 8
    use_headless: bool = True
    enable_cache: bool = True

# ============================================================================
# CONNECTION POOL OTIMIZADO
# ============================================================================

class DriverPool:
    """Pool de WebDrivers otimizado com gerenciamento de recursos"""
    
    def __init__(self, config: ExtractionConfig):
        self.config = config
        self._pool: deque = deque(maxlen=config.driver_pool_size)
        self._lock = Lock()
        self._semaphore = Semaphore(config.driver_pool_size)
        self._driver_factory = ChromeDriverFactory(config)
        self._active_drivers: Set[webdriver.Chrome] = set()
        
    def acquire(self) -> webdriver.Chrome:
        """Adquire um driver do pool"""
        self._semaphore.acquire()
        
        with self._lock:
            if self._pool:
                driver = self._pool.popleft()
                if self._is_driver_valid(driver):
                    self._active_drivers.add(driver)
                    return driver
            
            driver = self._create_driver()
            self._active_drivers.add(driver)
            return driver
    
    def release(self, driver: webdriver.Chrome):
        """Retorna driver ao pool"""
        with self._lock:
            if driver in self._active_drivers:
                self._active_drivers.remove(driver)
                
                if self._is_driver_valid(driver):
                    self._clear_driver_state(driver)
                    self._pool.append(driver)
                else:
                    driver.quit()
            
            self._semaphore.release()
    
    def _is_driver_valid(self, driver: webdriver.Chrome) -> bool:
        """Verifica se driver está válido"""
        try:
            driver.current_url
            return True
        except Exception:
            return False
    
    def _clear_driver_state(self, driver: webdriver.Chrome):
        """Limpa estado do driver"""
        try:
            driver.execute_script("window.localStorage.clear();")
            driver.execute_script("window.sessionStorage.clear();")
            driver.delete_all_cookies()
        except Exception:
            pass
    
    def _create_driver(self) -> webdriver.Chrome:
        """Cria novo driver"""
        return self._driver_factory.create_driver()
    
    def cleanup(self):
        """Limpa todos os recursos do pool"""
        with self._lock:
            for driver in list(self._active_drivers) + list(self._pool):
                try:
                    driver.quit()
                except Exception:
                    pass
            
            self._pool.clear()
            self._active_drivers.clear()

class ChromeDriverFactory:
    """Factory otimizada para criação de ChromeDriver"""
    
    def __init__(self, config: ExtractionConfig):
        self.config = config
        self._options_cache = None
    
    def create_driver(self) -> webdriver.Chrome:
        """Cria driver otimizado"""
        options = self._get_optimized_options()
        
        # Tenta diferentes estratégias de criação
        drivers = [
            self._create_with_webdriver_manager,
            self._create_with_system_paths,
            self._create_default
        ]
        
        for create_method in drivers:
            try:
                driver = create_method(options)
                driver.set_page_load_timeout(self.config.page_load_timeout)
                driver.implicitly_wait(2)
                return driver
            except Exception:
                continue
        
        raise RuntimeError("Não foi possível criar ChromeDriver")
    
    def _get_optimized_options(self) -> Options:
        """Configura opções otimizadas para máxima performance"""
        if self._options_cache:
            return self._options_cache
        
        options = Options()
        
        # Otimizações críticas de performance
        if self.config.use_headless:
            options.add_argument("--headless=new")
        
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-setuid-sandbox")
        options.add_argument("--disable-web-security")
        options.add_argument("--disable-features=VizDisplayCompositor")
        options.add_argument("--disable-logging")
        options.add_argument("--log-level=3")
        options.add_argument("--silent")
        options.add_argument("--window-size=1920,1080")
        
        # Cache e memória
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
            "profile.default_content_setting_values.geolocation": 2,
            "profile.default_content_setting_values.media_stream": 2,
        }
        options.add_experimental_option("prefs", prefs)
        
        # Desabilita features que consomem recursos
        options.add_experimental_option("excludeSwitches", ["enable-logging", "enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        self._options_cache = options
        return options
    
    def _create_with_webdriver_manager(self, options: Options) -> webdriver.Chrome:
        """Cria usando webdriver-manager"""
        from webdriver_manager.chrome import ChromeDriverManager
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=options)
    
    def _create_with_system_paths(self, options: Options) -> webdriver.Chrome:
        """Cria usando paths do sistema"""
        driver_paths = [
            "/usr/bin/chromedriver",
            "/usr/local/bin/chromedriver",
            shutil.which("chromedriver")
        ]
        
        for path in driver_paths:
            if path and os.path.exists(path):
                return webdriver.Chrome(service=Service(path), options=options)
        
        raise FileNotFoundError("ChromeDriver não encontrado")
    
    def _create_default(self, options: Options) -> webdriver.Chrome:
        """Cria usando configuração padrão"""
        return webdriver.Chrome(options=options)

# ============================================================================
# CACHE SYSTEM OTIMIZADO
# ============================================================================

class DataCache:
    """Sistema de cache otimizado com persistência"""
    
    def __init__(self, cache_dir: str = ".cache"):
        self.cache_dir = cache_dir
        self._memory_cache = {}
        self._lock = Lock()
        os.makedirs(cache_dir, exist_ok=True)
    
    @PerformanceDecorators.sync_timer
    def get(self, key: str) -> Optional[Any]:
        """Recupera item do cache"""
        # Tenta memória cache primeiro
        if key in self._memory_cache:
            data, timestamp = self._memory_cache[key]
            if time.time() - timestamp < 86400:  # 24 horas
                return data
        
        # Tenta cache em disco
        cache_file = os.path.join(self.cache_dir, f"{hashlib.md5(key.encode()).hexdigest()}.pkl")
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'rb') as f:
                    data, timestamp = pickle.load(f)
                    if time.time() - timestamp < 86400:
                        self._memory_cache[key] = (data, timestamp)
                        return data
            except Exception:
                pass
        
        return None
    
    def set(self, key: str, value: Any):
        """Armazena item no cache"""
        timestamp = time.time()
        
        with self._lock:
            self._memory_cache[key] = (value, timestamp)
            
            # Cache em disco assíncrono
            cache_file = os.path.join(self.cache_dir, f"{hashlib.md5(key.encode()).hexdigest()}.pkl")
            try:
                with open(cache_file, 'wb') as f:
                    pickle.dump((value, timestamp), f)
            except Exception:
                pass
    
    def clear_old(self, max_age_hours: int = 24):
        """Limpa cache antigo"""
        cutoff = time.time() - (max_age_hours * 3600)
        
        with self._lock:
            # Limpa memória
            keys_to_remove = [
                k for k, (_, ts) in self._memory_cache.items()
                if ts < cutoff
            ]
            for k in keys_to_remove:
                del self._memory_cache[k]
            
            # Limpa disco
            for filename in os.listdir(self.cache_dir):
                filepath = os.path.join(self.cache_dir, filename)
                if os.path.getmtime(filepath) < cutoff:
                    try:
                        os.remove(filepath)
                    except Exception:
                        pass

# ============================================================================
# EXTRACTORS OTIMIZADOS
# ============================================================================

class OptimizedDataExtractor:
    """Extrator otimizado com técnicas avançadas de scraping"""
    
    def __init__(self, config: ExtractionConfig):
        self.config = config
        self.cache = DataCache() if config.enable_cache else None
        self._selectors_cache = {}
    
    @PerformanceDecorators.sync_timer
    def extract_businesses(self, driver: webdriver.Chrome, search_term: str) -> List[BusinessData]:
        """Extrai lista de empresas com scroll inteligente"""
        url = f"https://www.google.com.br/maps/search/{search_term.replace(' ', '+')}"
        driver.get(url)
        
        # Espera rápida com condição específica
        WebDriverWait(driver, self.config.connection_timeout).until(
            EC.presence_of_element_located((By.XPATH, '//div[@role="feed"]'))
        )
        
        # Scroll otimizado com detecção de novos elementos
        businesses = self._smart_scroll(driver)
        
        return self._create_business_objects_parallel(businesses, search_term)
    
    def _smart_scroll(self, driver: webdriver.Chrome) -> List:
        """Scroll inteligente com detecção de novos elementos"""
        painel = driver.find_element(By.XPATH, '//div[@role="feed"]')
        sem_novos = 0
        ultimo_total = 0
        elementos = []
        
        # Scroll dinâmico com velocidade adaptativa
        while sem_novos < self.config.max_no_new_items:
            # Scroll com JavaScript otimizado
            driver.execute_script("""
                var element = arguments[0];
                element.scrollTop = element.scrollHeight;
            """, painel)
            
            time.sleep(self.config.scroll_wait_time)
            
            # Captura novos elementos
            novos = driver.find_elements(By.CLASS_NAME, "hfpxzc")
            elementos = novos
            total = len(elementos)
            
            if total == ultimo_total:
                sem_novos += 1
            else:
                sem_novos = 0
            
            ultimo_total = total
            
            # Verifica fim da lista rapidamente
            if self._is_end_of_list(driver):
                break
        
        return elementos
    
    def _is_end_of_list(self, driver: webdriver.Chrome) -> bool:
        """Verifica se chegou ao fim da lista"""
        try:
            end_elements = driver.find_elements(
                By.XPATH,
                '//*[contains(text(),"Você chegou ao fim")]|//*[contains(text(),"end of the list")]'
            )
            return len(end_elements) > 0
        except Exception:
            return False
    
    def _create_business_objects_parallel(self, elements: List, search_term: str) -> List[BusinessData]:
        """Cria objetos BusinessData em paralelo"""
        businesses = []
        seen_links = set()
        
        # Processa em lotes para melhor performance
        for el in elements:
            try:
                link = el.get_attribute("href")
                if link and link not in seen_links:
                    seen_links.add(link)
                    businesses.append(BusinessData(
                        empresa=el.get_attribute("aria-label") or "N/A",
                        link=link,
                        termo_pesquisado=search_term
                    ))
            except Exception:
                continue
        
        return businesses
    
    @PerformanceDecorators.retry(max_attempts=2, delay=0.5)
    def extract_business_details(self, driver: webdriver.Chrome, business: BusinessData) -> BusinessData:
        """Extrai detalhes da empresa com cache"""
        # Verifica cache
        if self.cache:
            cache_key = f"details_{business.link}"
            cached_data = self.cache.get(cache_key)
            if cached_data:
                return BusinessData.from_dict(cached_data)
        
        driver.get(business.link)
        
        # Espera mais específica
        WebDriverWait(driver, self.config.connection_timeout).until(
            EC.presence_of_element_located((By.CLASS_NAME, "Io6YTe"))
        )
        
        time.sleep(self.config.detail_wait_time)
        
        # Extração paralela de dados
        extractors = [
            (self._extract_address, "endereco"),
            (self._extract_phone, "telefone"),
            (self._extract_website, "site"),
            (self._extract_rating, "avaliacao"),
            (self._extract_review_count, "numero_avaliacoes"),
            (self._extract_category, "categoria"),
        ]
        
        # Executa extrações em paralelo usando ThreadPool
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = {executor.submit(extractor, driver): attr for extractor, attr in extractors}
            for future in futures:
                attr = futures[future]
                try:
                    value = future.result(timeout=5)
                    setattr(business, attr, value)
                except Exception:
                    pass
        
        # Fallback para dados críticos
        self._fallback_extraction_parallel(driver, business)
        
        # Salva no cache
        if self.cache:
            self.cache.set(f"details_{business.link}", business.to_dict())
        
        return business
    
    def _extract_address(self, driver: webdriver.Chrome) -> str:
        """Extrai endereço com múltiplos seletores"""
        selectors = [
            'button[data-item-id="address"]',
            'button[aria-label*="Endereço"]',
            'button[aria-label*="Address"]',
            'div[aria-label*="Endereço"]'
        ]
        return self._try_extract(driver, selectors)
    
    def _extract_phone(self, driver: webdriver.Chrome) -> str:
        """Extrai telefone com múltiplos seletores"""
        selectors = [
            'button[data-item-id^="phone:tel"]',
            'button[aria-label*="Telefone"]',
            'button[aria-label*="Phone"]',
            'div[aria-label*="Telefone"]'
        ]
        return self._try_extract(driver, selectors)
    
    def _extract_website(self, driver: webdriver.Chrome) -> str:
        """Extrai website"""
        selectors = [
            'a[data-item-id="authority"]',
            'a[aria-label*="Site"]',
            'a[aria-label*="Website"]',
            'a[aria-label*="site"]'
        ]
        
        for selector in selectors:
            try:
                element = driver.find_element(By.CSS_SELECTOR, selector)
                href = element.get_attribute("href")
                if href and href.startswith("http"):
                    return href
            except Exception:
                continue
        return "N/A"
    
    def _extract_rating(self, driver: webdriver.Chrome) -> str:
        """Extrai avaliação"""
        selectors = [
            'span[aria-hidden="true"].ceNzKf',
            'div.F7nice span[aria-hidden="true"]',
            'span[jsaction="pane.rating.moreReviews"]'
        ]
        
        for selector in selectors:
            try:
                element = driver.find_element(By.CSS_SELECTOR, selector)
                text = element.text.strip()
                if text:
                    return text
            except Exception:
                continue
        return "N/A"
    
    def _extract_review_count(self, driver: webdriver.Chrome) -> str:
        """Extrai número de avaliações"""
        selectors = [
            'span[aria-label*="avaliações"]',
            'span[aria-label*="reviews"]',
            'button[aria-label*="avaliações"]'
        ]
        
        for selector in selectors:
            try:
                element = driver.find_element(By.CSS_SELECTOR, selector)
                txt = element.get_attribute("aria-label") or element.text
                if txt:
                    numbers = ''.join(c for c in txt if c.isdigit() or c == '.')
                    if numbers:
                        return numbers
            except Exception:
                continue
        return "N/A"
    
    def _extract_category(self, driver: webdriver.Chrome) -> str:
        """Extrai categoria"""
        selectors = [
            'button[jsaction*="category"]',
            'span.DkEaL',
            'div[aria-label*="Categoria"]'
        ]
        
        for selector in selectors:
            try:
                element = driver.find_element(By.CSS_SELECTOR, selector)
                text = element.text.strip()
                if text:
                    return text
            except Exception:
                continue
        return "N/A"
    
    def _try_extract(self, driver: webdriver.Chrome, selectors: List[str]) -> str:
        """Tenta extrair usando múltiplos seletores"""
        for selector in selectors:
            try:
                element = driver.find_element(By.CSS_SELECTOR, selector)
                text_element = element.find_element(By.CLASS_NAME, "Io6YTe")
                text = text_element.text.strip()
                if text and text != "N/A":
                    return text
            except Exception:
                continue
        return "N/A"
    
    def _fallback_extraction_parallel(self, driver: webdriver.Chrome, business: BusinessData):
        """Fallback paralelo para dados perdidos"""
        if business.endereco == "N/A" or business.telefone == "N/A":
            try:
                elements = driver.find_elements(By.CLASS_NAME, "Io6YTe")
                for el in elements:
                    txt = el.text.strip()
                    if not txt or txt == "N/A":
                        continue
                    
                    # Detecta telefone
                    if business.telefone == "N/A":
                        if any(c.isdigit() for c in txt) and len(txt) >= 10:
                            if any(char in txt for char in ['(', '+', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9']):
                                business.telefone = txt
                    
                    # Detecta endereço
                    elif business.endereco == "N/A":
                        if (',' in txt or ' - ' in txt) and len(txt) > 15:
                            business.endereco = txt
                    
                    if business.telefone != "N/A" and business.endereco != "N/A":
                        break
            except Exception:
                pass

# ============================================================================
# BATCH PROCESSOR OTIMIZADO
# ============================================================================

class OptimizedBatchProcessor:
    """Processador em lote otimizado com pipeline paralelo"""
    
    def __init__(self, extractor: OptimizedDataExtractor, config: ExtractionConfig):
        self.extractor = extractor
        self.config = config
        self.driver_pool = DriverPool(config)
        self.task_queue = PriorityQueue()
        self.results = []
    
    @PerformanceDecorators.sync_timer
    def process_batch(self, businesses: List[BusinessData], progress_callback=None) -> List[BusinessData]:
        """Processa lote usando pipeline paralelo"""
        total = len(businesses)
        results = [None] * total
        completed = 0
        
        # Processa em lotes
        for i in range(0, total, self.config.batch_size):
            batch = businesses[i:i + self.config.batch_size]
            batch_results = self._process_batch_parallel(batch)
            
            # Atualiza resultados
            for j, result in enumerate(batch_results):
                results[i + j] = result
            
            completed += len(batch)
            if progress_callback:
                progress_callback(completed, total)
        
        return results
    
    def _process_batch_parallel(self, batch: List[BusinessData]) -> List[BusinessData]:
        """Processa lote em paralelo com pool de drivers"""
        results = []
        
        with ThreadPoolExecutor(max_workers=min(self.config.max_workers, len(batch))) as executor:
            futures = {}
            
            for business in batch:
                driver = self.driver_pool.acquire()
                future = executor.submit(self._process_single, driver, business)
                futures[future] = (business, driver)
            
            for future in futures:
                business, driver = futures[future]
                try:
                    result = future.result(timeout=30)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Erro processando {business.empresa}: {e}")
                    results.append(business)
                finally:
                    self.driver_pool.release(driver)
        
        return results
    
    def _process_single(self, driver: webdriver.Chrome, business: BusinessData) -> BusinessData:
        """Processa empresa individual"""
        return self.extractor.extract_business_details(driver, business)
    
    def cleanup(self):
        """Limpa recursos"""
        self.driver_pool.cleanup()

# ============================================================================
# DATA MANAGER OTIMIZADO
# ============================================================================

class OptimizedDataManager:
    """Gerenciador de dados otimizado com compressão"""
    
    def __init__(self, filename: str = "base_dados_total.xlsx"):
        self.filename = filename
        self._lock = Lock()
        self._buffer = []
        self._buffer_size = 100
    
    def save_batch(self, businesses: List[BusinessData]) -> pd.DataFrame:
        """Salva lote com buffer e deduplicação otimizada"""
        df_new = pd.DataFrame([b.to_dict() for b in businesses])
        
        # Deduplicação eficiente
        df_new = df_new.drop_duplicates(subset=["Link"], keep="last")
        
        with self._lock:
            if os.path.exists(self.filename):
                # Leitura otimizada
                df_existing = pd.read_excel(self.filename, dtype=str)
                
                # Concatenação eficiente
                df_combined = pd.concat([df_existing, df_new], ignore_index=True)
                df_combined = df_combined.drop_duplicates(subset=["Link"], keep="last")
            else:
                df_combined = df_new
            
            # Salva com compressão
            df_combined.to_excel(self.filename, index=False, engine='openpyxl')
        
        return df_new
    
    def load_data(self) -> Optional[pd.DataFrame]:
        """Carrega dados com otimização"""
        if os.path.exists(self.filename):
            return pd.read_excel(self.filename, dtype=str)
        return None

# ============================================================================
# UI MANAGER OTIMIZADO
# ============================================================================

class OptimizedUIManager:
    """Gerenciador de UI otimizado com lazy loading"""
    
    CSS = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    /* Base otimizada */
    * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }
    
    html, body, [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%) !important;
        font-family: 'Inter', sans-serif;
    }
    
    /* Esconde elementos desnecessários */
    [data-testid="stHeader"], [data-testid="stToolbar"], footer, [data-testid="stSidebar"] {
        display: none !important;
    }
    
    /* Scrollbar minimalista */
    ::-webkit-scrollbar {
        width: 4px;
        height: 4px;
    }
    
    ::-webkit-scrollbar-track {
        background: #1E293B;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #3B82F6;
        border-radius: 2px;
    }
    
    /* Container principal */
    .main-container {
        max-width: 1400px;
        margin: 0 auto;
        padding: 2rem;
    }
    
    /* Header moderno */
    .modern-header {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 16px;
        padding: 1rem 2rem;
        margin-bottom: 2rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    
    .logo-area {
        display: flex;
        align-items: center;
        gap: 12px;
    }
    
    .logo-icon {
        width: 40px;
        height: 40px;
        background: linear-gradient(135deg, #3B82F6, #06B6D4);
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 20px;
    }
    
    .logo-text {
        font-weight: 700;
        font-size: 1.2rem;
        background: linear-gradient(135deg, #fff 0%, #94A3B8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    .logo-sub {
        font-size: 0.7rem;
        color: #64748B;
    }
    
    /* Cards com glassmorphism */
    .glass-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        transition: all 0.3s ease;
    }
    
    .glass-card:hover {
        border-color: rgba(59, 130, 246, 0.3);
        transform: translateY(-2px);
    }
    
    /* Grid responsivo */
    .feature-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 1rem;
        margin: 2rem 0;
    }
    
    .feature-item {
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        padding: 1rem;
        text-align: center;
    }
    
    .feature-icon {
        font-size: 2rem;
        margin-bottom: 0.5rem;
    }
    
    .feature-title {
        font-weight: 600;
        margin-bottom: 0.25rem;
        color: #E2E8F0;
    }
    
    .feature-desc {
        font-size: 0.8rem;
        color: #64748B;
    }
    
    /* Stats row */
    .stats-row {
        display: flex;
        justify-content: center;
        gap: 3rem;
        margin: 2rem 0;
    }
    
    .stat-item {
        text-align: center;
    }
    
    .stat-number {
        font-size: 2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #3B82F6, #06B6D4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    .stat-label {
        font-size: 0.7rem;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    /* Animação de fade in */
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .animate-in {
        animation: fadeInUp 0.6s ease forwards;
    }
    
    /* Botão principal */
    .stButton > button {
        background: linear-gradient(135deg, #3B82F6 0%, #2563EB 100%) !important;
        border: none !important;
        border-radius: 10px !important;
        color: white !important;
        font-weight: 600 !important;
        padding: 0.6rem 1.5rem !important;
        transition: all 0.3s ease !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 10px 20px -10px rgba(59, 130, 246, 0.5) !important;
    }
    
    /* Input fields */
    .stTextInput > div > div > input {
        background: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 10px !important;
        color: white !important;
        padding: 0.6rem 1rem !important;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #3B82F6 !important;
        box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2) !important;
    }
    
    /* Progress bar */
    .stProgress > div > div > div {
        background: linear-gradient(90deg, #3B82F6, #06B6D4) !important;
    }
    
    /* DataFrame */
    [data-testid="stDataFrame"] {
        background: rgba(255, 255, 255, 0.02) !important;
        border-radius: 12px !important;
        overflow: hidden !important;
    }
    
    /* Footer */
    .custom-footer {
        text-align: center;
        padding: 2rem;
        margin-top: 3rem;
        border-top: 1px solid rgba(255, 255, 255, 0.05);
        color: #64748B;
        font-size: 0.8rem;
    }
    
    .social-links {
        display: flex;
        justify-content: center;
        gap: 1rem;
        margin-top: 0.5rem;
    }
    
    .social-links a {
        color: #64748B;
        text-decoration: none;
        transition: color 0.3s ease;
    }
    
    .social-links a:hover {
        color: #3B82F6;
    }
    </style>
    """
    
    @staticmethod
    def render_login_page(error: bool = False):
        """Renderiza página de login otimizada"""
        st.markdown(OptimizedUIManager.CSS, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="main-container animate-in">
            <div class="modern-header">
                <div class="logo-area">
                    <div class="logo-icon">📍</div>
                    <div>
                        <div class="logo-text">Gerar Lead</div>
                        <div class="logo-sub">Google Maps Scraper</div>
                    </div>
                </div>
            </div>
            
            <div class="glass-card" style="max-width: 500px; margin: 0 auto;">
                <div style="text-align: center; margin-bottom: 2rem;">
                    <div style="font-size: 3rem; margin-bottom: 0.5rem;">🎯</div>
                    <h2 style="margin-bottom: 0.5rem;">Plataforma de Leads</h2>
                    <p style="color: #64748B;">Extraia dados do Google Maps em escala</p>
                </div>
                
                <div class="feature-grid">
                    <div class="feature-item">
                        <div class="feature-icon">⚡</div>
                        <div class="feature-title">Rápido</div>
                        <div class="feature-desc">Extração paralela</div>
                    </div>
                    <div class="feature-item">
                        <div class="feature-icon">📊</div>
                        <div class="feature-title">Completo</div>
                        <div class="feature-desc">9 campos extraídos</div>
                    </div>
                    <div class="feature-item">
                        <div class="feature-icon">💾</div>
                        <div class="feature-title">Persistente</div>
                        <div class="feature-desc">Base acumulada</div>
                    </div>
                </div>
                
                <div class="stats-row">
                    <div class="stat-item">
                        <div class="stat-number">100%</div>
                        <div class="stat-label">Automação</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-number">6+</div>
                        <div class="stat-label">Campos</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-number">Excel</div>
                        <div class="stat-label">Exportação</div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        if error:
            st.markdown("""
            <div class="glass-card" style="max-width: 500px; margin: 1rem auto; background: rgba(239, 68, 68, 0.1); border-color: rgba(239, 68, 68, 0.3);">
                <div style="text-align: center; color: #EF4444;">⚠️ Usuário ou senha incorretos</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("""
            <div class="glass-card" style="max-width: 500px; margin: 0 auto;">
                <div style="margin-bottom: 1rem;">
                    <div style="font-weight: 600; margin-bottom: 0.5rem;">🔐 Acesso Restrito</div>
                    <div style="color: #64748B;">Entre com suas credenciais</div>
                </div>
            </div>
        """, unsafe_allow_html=True)
    
    @staticmethod
    def render_app_header():
        """Renderiza header do app"""
        st.markdown("""
        <div class="main-container">
            <div class="modern-header">
                <div class="logo-area">
                    <div class="logo-icon">📍</div>
                    <div>
                        <div class="logo-text">Gerar Lead</div>
                        <div class="logo-sub">Google Maps Scraper</div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
    
    @staticmethod
    def render_results(df: pd.DataFrame):
        """Renderiza resultados"""
        st.divider()
        
        st.markdown("""
        <div class="glass-card animate-in">
            <h3 style="margin-bottom: 1rem;">📊 Resultados da Extração</h3>
        """, unsafe_allow_html=True)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Extraído", len(df))
        with col2:
            st.metric("Com Telefone", (df["Telefone"] != "N/A").sum())
        with col3:
            st.metric("Com Site", (df["Site"] != "N/A").sum())
        with col4:
            st.metric("Com Endereço", (df["Endereço"] != "N/A").sum())
        
        st.dataframe(df, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    
    @staticmethod
    def render_footer():
        """Renderiza footer"""
        st.markdown("""
        <div class="custom-footer">
            <div>Desenvolvido por <strong>Rodrigo AIOSA</strong></div>
            <div class="social-links">
                <a href="https://wa.me/5511977019335" target="_blank">📱 WhatsApp</a>
                <a href="https://www.linkedin.com/in/rodrigoaiosa/" target="_blank">💼 LinkedIn</a>
            </div>
        </div>
        </div>
        """, unsafe_allow_html=True)

# ============================================================================
# MAIN APPLICATION OTIMIZADA
# ============================================================================

class OptimizedLeadGeneratorApp:
    """Aplicação principal otimizada"""
    
    def __init__(self):
        self.ui_manager = OptimizedUIManager()
        self.data_manager = OptimizedDataManager()
        self.config = ExtractionConfig(
            max_workers=8,
            scroll_wait_time=0.6,
            detail_wait_time=0.4,
            max_no_new_items=3,
            batch_size=25,
            driver_pool_size=6
        )
        self.extractor = OptimizedDataExtractor(self.config)
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
        
        usuario = st.text_input("Usuário", placeholder="Digite seu usuário", key="login_user")
        senha = st.text_input("Senha", placeholder="Digite sua senha", type="password", key="login_pass")
        
        if st.button("🔓 Entrar", use_container_width=True):
            if self._check_login(usuario, senha):
                st.session_state["logado"] = True
                st.session_state["login_erro"] = False
                st.rerun()
            else:
                st.session_state["login_erro"] = True
                st.rerun()
        
        self.ui_manager.render_footer()
        st.stop()
    
    @PerformanceDecorators.sync_timer
    def run_extraction(self, search_term: str):
        """Executa extração otimizada"""
        try:
            # Cria processador
            self.processor = OptimizedBatchProcessor(self.extractor, self.config)
            
            # Extrai lista de empresas
            status_placeholder = st.empty()
            status_placeholder.info(f"🔎 Buscando: '{search_term}'...")
            
            # Driver temporário para busca inicial
            factory = ChromeDriverFactory(self.config)
            temp_driver = factory.create_driver()
            
            try:
                businesses = self.extractor.extract_businesses(temp_driver, search_term)
            finally:
                temp_driver.quit()
            
            total = len(businesses)
            
            if total == 0:
                st.warning("Nenhuma empresa encontrada.")
                return
            
            status_placeholder.info(f"📋 {total} empresas encontradas. Extraindo detalhes...")
            
            # Progresso
            progress_bar = st.progress(0)
            progress_text = st.empty()
            
            def update_progress(current, total):
                progress_bar.progress(current / total)
                progress_text.text(f"⚙️ {current}/{total} empresas")
            
            # Processa em paralelo
            processed_businesses = self.processor.process_batch(businesses, update_progress)
            
            # Salva resultados
            df_new = self.data_manager.save_batch(processed_businesses)
            
            # Estatísticas
            success_count = sum(1 for b in processed_businesses if b.telefone != "N/A")
            error_count = total - success_count
            
            if error_count > 0:
                with st.expander(f"⚠️ {error_count} empresas com erro"):
                    for b in processed_businesses[:10]:  # Mostra apenas 10 exemplos
                        if b.telefone == "N/A":
                            st.write(f"• {b.empresa}")
                    if error_count > 10:
                        st.write(f"... e mais {error_count - 10} empresas")
            
            st.success(f"✅ Concluído! {success_count} extraídas | {error_count} com erro")
            
            # Armazena resultado
            st.session_state["df_resultado"] = df_new
            
        except Exception as e:
            logger.error(f"Erro na extração: {e}")
            st.error(f"Erro: {e}")
        finally:
            if self.processor:
                self.processor.cleanup()
    
    def run_main_app(self):
        """Executa aplicação principal"""
        st.set_page_config(
            page_title="Gerar Lead",
            layout="wide",
            page_icon="📍",
            initial_sidebar_state="collapsed"
        )
        
        self.ui_manager.render_app_header()
        
        # Interface principal
        st.markdown("""
        <div class="glass-card animate-in">
            <h3 style="margin-bottom: 1rem;">🔎 Nova Extração</h3>
        """, unsafe_allow_html=True)
        
        termo_final = st.text_input(
            "Termo de busca",
            placeholder="Ex: Farmácias em Osasco SP, Restaurantes em São Paulo, Advogados em Curitiba",
            help="Digite o que deseja buscar no Google Maps"
        )
        
        if st.button("🚀 Iniciar Extração", use_container_width=True):
            if not termo_final:
                st.warning("Digite um termo de busca")
            else:
                self.run_extraction(termo_final)
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Resultados
        if "df_resultado" in st.session_state and st.session_state["df_resultado"] is not None:
            self.ui_manager.render_results(st.session_state["df_resultado"])
            
            # Botão de download
            if os.path.exists("base_dados_total.xlsx"):
                with open("base_dados_total.xlsx", "rb") as f:
                    st.download_button(
                        label="📥 Baixar Base Completa (Excel)",
                        data=f,
                        file_name=f"leads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                    )
        
        self.ui_manager.render_footer()
    
    def run(self):
        """Ponto de entrada"""
        st.set_page_config(
            page_title="Gerar Lead",
            layout="wide",
            page_icon="📍",
            initial_sidebar_state="collapsed"
        )
        
        if not st.session_state.get("logado", False):
            self.run_login_page()
        else:
            self.run_main_app()

# ============================================================================
# EXECUÇÃO
# ============================================================================

if __name__ == "__main__":
    app = OptimizedLeadGeneratorApp()
    app.run()
