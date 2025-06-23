import time
import json
import random
import re 
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select 
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from urllib.parse import urlencode, urljoin, urlparse

# --- Configuración Global y Carga de API Key ---
API_KEY = "" 
try:
    with open("config.json", "r") as config_file:
        config = json.load(config_file)
        API_KEY = config.get("api_key", "")
        if API_KEY: print(f"API Key cargada.")
        else: print("Advertencia: 'api_key' no encontrada o vacía en config.json.")
except FileNotFoundError: print("Advertencia: El archivo config.json no fue encontrado."); exit() if not API_KEY else None
except KeyError: print("Advertencia: 'api_key' no encontrada en config.json."); exit() if not API_KEY else None
if not API_KEY: print("Error crítico: API_KEY de ScrapeOps no está configurada. El script se detendrá."); exit()

# --- Funciones Auxiliares ---
def get_scrapeops_url(target_url, residential=True, render_js=True, country="us"):
    if not API_KEY: print("ADVERTENCIA: API_KEY de ScrapeOps no está configurada. Accediendo a la URL directamente."); return target_url
    payload = { "api_key": API_KEY, "url": target_url, "country": country, "residential": residential, "render_js": render_js, "timeout": 180000 }
    return "https://proxy.scrapeops.io/v1/?" + urlencode(payload)

def configurar_driver():
    options = Options()
    # options.add_argument("--headless") 
    options.add_argument("--no-sandbox"); options.add_argument("--disable-dev-shm-usage"); options.add_argument("--disable-gpu")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")
    options.add_argument("--start-maximized")
    options.add_experimental_option("excludeSwitches", ["enable-automation"]); options.add_experimental_option('useAutomationExtension', False)
    options.add_argument('--disable-blink-features=AutomationControlled')
    try:
        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"})
        print("Driver de Selenium configurado.")
        return driver
    except Exception as e: print(f"Error al configurar el driver de Selenium: {e}"); return None

def formatear_ubicacion_zillow(ubicacion_str):
    if not ubicacion_str: return ""
    try:
        partes = ubicacion_str.split(','); ciudad = partes[0].strip().lower().replace(' ', '-'); estado = ""
        if len(partes) > 1: estado = partes[1].strip().lower()
        return f"{ciudad}-{estado}" if ciudad and estado else ciudad
    except Exception as e: print(f"Error formateando ubicación '{ubicacion_str}': {e}"); return ""


# --- Funciones para Aplicar Filtros (VISTA MÓVIL) ---
def aplicar_filtro_sort_mobile(driver, sort_by="Newest"):
    try:
        print(f"  [Mobile] Aplicando filtro de orden: '{sort_by}'...")
        sort_button = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label="Sort Properties"]')))
        sort_button.click(); time.sleep(random.uniform(1.5, 2.5))
        newest_option = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-key="days"]')))
        newest_option.click(); time.sleep(random.uniform(4, 6))
        print("  [Mobile] Filtro 'Newest' aplicado.")
        return True
    except Exception: print(f"    ERROR [Mobile]: No se pudo aplicar el filtro de orden 'Newest'."); return False

def aplicar_filtro_precio_mobile(driver, min_price):
    try:
        print(f"  [Mobile] Aplicando filtro de precio mínimo: ${min_price}")
        price_button = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.XPATH, "//button[.//span[text()='Price']]")))
        price_button.click(); time.sleep(random.uniform(1.5, 2.5))
        min_price_input = WebDriverWait(driver, 15).until(EC.visibility_of_element_located((By.CSS_SELECTOR, 'input[placeholder="No Min"]')))
        min_price_input.clear(); min_price_input.send_keys(str(min_price)); time.sleep(random.uniform(0.5, 1))
        apply_button = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'See') and contains(text(), 'rentals')]")))
        apply_button.click(); time.sleep(random.uniform(4, 6))
        print("  [Mobile] Filtro de precio aplicado.")
        return True
    except Exception: print(f"    ERROR [Mobile]: No se pudo aplicar el filtro de precio."); return False

def aplicar_filtro_dias_mobile(driver, days="1"):
    try:
        print(f"  [Mobile] Aplicando filtro 'Days on Zillow': {days} day(s)")
        more_button = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-test="more-filters-button"]')))
        more_button.click(); time.sleep(random.uniform(1.5, 2.5))
        days_dropdown_element = WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'select#doz')))
        Select(days_dropdown_element).select_by_value(str(days))
        time.sleep(random.uniform(0.5, 1))
        apply_button = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-test="close-filters-button"]')))
        apply_button.click(); time.sleep(random.uniform(4, 6))
        print("  [Mobile] Filtro 'Days on Zillow' aplicado.")
        return True
    except Exception: print(f"    ERROR [Mobile]: No se pudo aplicar el filtro 'Days on Zillow'."); return False

def aplicar_filtros_vista_mobile(driver, sort_by_newest, min_price, days_on_zillow, tipo_listado):
    """Agrupa y ejecuta la secuencia de filtros para la vista móvil."""
    if sort_by_newest:
        if not aplicar_filtro_sort_mobile(driver): return False
    if min_price is not None:
        if not aplicar_filtro_precio_mobile(driver, min_price): return False
    if days_on_zillow is not None:
        if not aplicar_filtro_dias_mobile(driver, days_on_zillow): return False
    print("¡ÉXITO! Todos los filtros de la vista móvil solicitados se aplicaron correctamente.")
    return True

# --- Funciones para Aplicar Filtros (VISTA WEB) ---
def aplicar_filtro_sort_web(driver, sort_by="Newest"):
    """Aplica el filtro 'Newest' en la vista web."""
    try:
        print(f"  [Web] Intentando aplicar filtro de orden: '{sort_by}'...")
        selector_boton_sort_web = 'button#sort-popover'
        sort_button = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector_boton_sort_web)))
        sort_button.click(); time.sleep(random.uniform(1.5, 2.5))
        selector_opcion_newest_web = 'button[data-value="days"]'
        newest_option = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector_opcion_newest_web)))
        newest_option.click(); time.sleep(random.uniform(4, 6))
        print("  [Web] Filtro 'Newest' aplicado.")
        return True
    except Exception as e: print(f"    ERROR [Web]: No se pudo aplicar el filtro de orden 'Newest'. Causa: {e}"); return False

def aplicar_filtro_precio_web(driver, min_price):
    """Aplica el filtro de precio en la vista web."""
    try:
        print(f"  [Web] Intentando aplicar filtro de precio mínimo: ${min_price}")
        price_button = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-test="price-filters-button"]')))
        price_button.click(); time.sleep(random.uniform(1.5, 2.5))
        min_price_input = WebDriverWait(driver, 15).until(EC.visibility_of_element_located((By.CSS_SELECTOR, 'input[aria-label="Price min"]')))
        min_price_input.clear(); min_price_input.send_keys(str(min_price)); time.sleep(random.uniform(0.5, 1))
        apply_button = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-test="close-filters-button"]')))
        apply_button.click(); time.sleep(random.uniform(4, 6))
        print("  [Web] Filtro de precio aplicado.")
        return True
    except Exception as e: print(f"    ERROR [Web]: No se pudo aplicar el filtro de precio. Causa: {e}"); return False

def aplicar_filtro_dias_web(driver, days="1"):
    """Aplica el filtro 'Days on Zillow' en la vista web (usa los mismos selectores que la móvil)."""
    try:
        print(f"  [Web] Aplicando filtro 'Days on Zillow': {days} day(s)")
        more_button = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-test="more-filters-button"]')))
        more_button.click(); time.sleep(random.uniform(1.5, 2.5))
        days_dropdown_element = WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'select#doz')))
        Select(days_dropdown_element).select_by_value(str(days))
        time.sleep(random.uniform(0.5, 1))
        apply_button = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-test="close-filters-button"]')))
        apply_button.click(); time.sleep(random.uniform(4, 6))
        print("  [Web] Filtro 'Days on Zillow' aplicado.")
        return True
    except Exception as e: print(f"    ERROR [Web]: No se pudo aplicar el filtro 'Days on Zillow'. Causa: {e}"); return False

def aplicar_filtros_vista_web(driver, sort_by_newest, min_price, days_on_zillow, tipo_listado):
    """Agrupa y ejecuta la secuencia de filtros para la vista web."""
    if days_on_zillow is not None: # Aplicar 'More' primero puede ser más estable.
        if not aplicar_filtro_dias_web(driver, days_on_zillow): return False
    if sort_by_newest:
        if not aplicar_filtro_sort_web(driver): return False
    if min_price is not None:
        if not aplicar_filtro_precio_web(driver, min_price): return False
    print("¡ÉXITO! Todos los filtros de la vista web se aplicaron correctamente.")
    return True

# --- Función Principal del Scraper (con LÓGICA DE REINTENTOS Y PAGINACIÓN) ---
def extraer_links_propiedades_zillow(driver, ciudad_estado_param, num_paginas=1, tipo_listado="rentals", sort_by_newest=True, min_price=None, days_on_zillow=None):
    print(f"Iniciando extracción para: {ciudad_estado_param} | Páginas: {num_paginas} | Tipo: {tipo_listado}")
    ubicacion_formateada = formatear_ubicacion_zillow(ciudad_estado_param)
    if not ubicacion_formateada: return []
    
    target_zillow_url = f"https://www.zillow.com/{ubicacion_formateada}/{tipo_listado.lower()}/"
    
    # --- BUCLE DE REINTENTO PARA CARGA DE PÁGINA INICIAL ---
    MAX_LOAD_ATTEMPTS = 3
    page_loaded_successfully = False
    for attempt in range(MAX_LOAD_ATTEMPTS):
        print(f"\nIntento de carga de página inicial {attempt + 1}/{MAX_LOAD_ATTEMPTS}...")
        url_scrapeops = get_scrapeops_url(target_zillow_url)
        print(f"Navegando a: {target_zillow_url} (vía ScrapeOps)")
        driver.get(url_scrapeops)
        try:
            print("Esperando a que la página de resultados cargue (buscando __NEXT_DATA__)...")
            WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.ID, "__NEXT_DATA__")))
            print("Página de resultados inicial cargada exitosamente.")
            page_loaded_successfully = True
            break
        except Exception as e_load:
            print(f"Intento {attempt + 1} falló al cargar la página o encontrar __NEXT_DATA__: {e_load}")
            if attempt < MAX_LOAD_ATTEMPTS - 1:
                print("Reintentando en unos segundos...")
                time.sleep(random.uniform(5, 10))
            else:
                print("Máximo de reintentos alcanzado. No se pudo cargar la página inicial.")
                driver.save_screenshot("zillow_initial_load_failed.png")
                print("Captura de pantalla del fallo de carga guardada.")

    if not page_loaded_successfully:
        return []

    # --- APLICACIÓN DE FILTROS ---
    try:
        print("\nPágina cargada. Aplicando filtros de UI...")
        filtros_aplicados_con_exito = False
        print("\n--- Intento 1: Aplicar filtros con selectores de VISTA MÓVIL ---")
        if aplicar_filtros_vista_mobile(driver, sort_by_newest, min_price, days_on_zillow, tipo_listado):
            filtros_aplicados_con_exito = True
        else:
            print("\n--- Intento 2: Fallback a selectores de VISTA WEB ---")
            if aplicar_filtros_vista_web(driver, sort_by_newest, min_price, days_on_zillow, tipo_listado):
                filtros_aplicados_con_exito = True
        
        if not filtros_aplicados_con_exito:
            print("\nFallaron los intentos de filtrado. La extracción se detiene.")
            return []
    except Exception as e_filtros:
        print(f"Ocurrió un error mayor durante la aplicación de filtros: {e_filtros}")
        return []

    # --- BUCLE DE PAGINACIÓN Y EXTRACCIÓN ---
    links_propiedades_encontrados_set = set() 
    pagina_actual = 1
    
    while pagina_actual <= num_paginas:
        print(f"\n--- Procesando Página {pagina_actual} (después de aplicar filtros) ---")
        try:
            print("Extrayendo __NEXT_DATA__ de la página actual...")
            selector_next_data = 'script[id="__NEXT_DATA__"]'
            time.sleep(2) 
            next_data_script_element = WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR, selector_next_data)))
            json_content_str = next_data_script_element.get_attribute('innerHTML')
            
            nuevos_links_en_esta_pagina = 0
            if json_content_str:
                data_next = json.loads(json_content_str)
                list_results_array = data_next.get("props", {}).get("pageProps", {}).get("searchPageState", {}).get("cat1", {}).get("searchResults", {}).get("listResults", [])
                print(f"__NEXT_DATA__ parseado. Encontrados {len(list_results_array)} resultados en 'listResults'.")
                for prop_item in list_results_array:
                    if isinstance(prop_item, dict) and "detailUrl" in prop_item:
                        link_absoluto = urljoin("https://www.zillow.com", prop_item.get("detailUrl"))
                        if link_absoluto not in links_propiedades_encontrados_set:
                            links_propiedades_encontrados_set.add(link_absoluto)
                            nuevos_links_en_esta_pagina += 1
            print(f"Se añadieron {nuevos_links_en_esta_pagina} links nuevos desde la página {pagina_actual}.")

            if pagina_actual >= num_paginas:
                print(f"Límite de {num_paginas} página(s) a scrapear alcanzado.")
                break

            print(f"Buscando botón 'Siguiente' para ir a la página {pagina_actual + 1}...")
            next_button_selector = 'a[rel="next"]'
            next_button = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.CSS_SELECTOR, next_button_selector)))
            
            current_next_button_ref = next_button
            print("Botón 'Siguiente' encontrado. Haciendo clic...")
            next_button.click()
            
            print("Esperando a que la página se actualice después del clic...")
            WebDriverWait(driver, 30).until(EC.staleness_of(current_next_button_ref))
            print(f"Navegado a la página {pagina_actual + 1} exitosamente.")
            
            pagina_actual += 1
            time.sleep(random.uniform(3, 5)) 

        except Exception as e_paginacion:
            print(f"No se pudo continuar con la paginación en la página {pagina_actual} o no hay más páginas. Causa: {e_paginacion}")
            print("Finalizando extracción de links.")
            break

    return list(links_propiedades_encontrados_set)

# --- Bloque de Ejecución ---
if __name__ == "__main__":
    print("--- Configuración de la Búsqueda para Zillow Crawler ---")
    
    ciudad_estado_a_buscar = input("Ingrese la Ciudad y Estado (ej. Stamford, CT): ")
    if not ciudad_estado_a_buscar:
        ciudad_estado_a_buscar = "Stamford, CT"
        print(f"Usando valor por defecto: {ciudad_estado_a_buscar}")

    tipo_de_listado_param = "rentals" 

    try:
        paginas_a_scrapear = int(input(f"Ingrese el número de páginas a scrapear (ej. 3, por defecto 1): ") or "1")
    except ValueError:
        print("Entrada de páginas inválida. Usando 1 por defecto.")
        paginas_a_scrapear = 1

    precio_minimo_alquiler = None
    try:
        precio_input = input("Ingrese el precio mínimo de alquiler (ej. 3000, presione Enter para no aplicar): ")
        if precio_input.strip():
            precio_minimo_alquiler = int(precio_input)
    except ValueError:
        print("Entrada de precio inválida. No se aplicará filtro de precio.")

    dias_en_zillow = None
    try:
        dias_input = input("Filtrar por 'Days on Zillow' (ej. 1, 7, 30, presione Enter para no aplicar): ")
        if dias_input.strip() and dias_input.strip() in ["1", "7", "14", "30", "90"]: # Validar entrada
            dias_en_zillow = dias_input.strip()
        elif dias_input.strip():
            print("Valor para 'Days on Zillow' no válido. No se aplicará el filtro.")
    except ValueError:
        print("Entrada de días inválida. No se aplicará filtro de días.")
    
    aplicar_orden_nuevos = False # No es necesario si se filtra por 'Days on Zillow'

    mi_driver = configurar_driver()
    if mi_driver:
        try:
            links = extraer_links_propiedades_zillow(
                mi_driver, ciudad_estado_a_buscar, 
                num_paginas=paginas_a_scrapear, tipo_listado=tipo_de_listado_param, 
                sort_by_newest=aplicar_orden_nuevos, min_price=precio_minimo_alquiler,
                days_on_zillow=dias_en_zillow
            )
            if links:
                print("\n" + "---" * 10 + "\n--- Links de Propiedades Extraídos ---")
                for link_idx, link_url in enumerate(links): print(f"{link_idx+1}. {link_url}")
                print(f"\nTotal de links únicos extraídos de hasta {paginas_a_scrapear} página(s): {len(links)}")
                # ... Lógica de guardado de archivo ...
                sort_suffix = "_newest" if aplicar_orden_nuevos else ""
                price_suffix = f"_minprice{precio_minimo_alquiler}" if precio_minimo_alquiler else ""
                days_suffix = f"_last{dias_en_zillow}days" if dias_en_zillow else ""
                output_filename = f"zillow_links_{formatear_ubicacion_zillow(ciudad_estado_a_buscar)}_{tipo_de_listado_param}{sort_suffix}{price_suffix}{days_suffix}.json"
                with open(output_filename, "w", encoding="utf-8") as f_json: json.dump(links, f_json, indent=4)
                print(f"Links guardados en {output_filename}")
            else:
                print("\nNo se extrajeron links de propiedades.")
        
        finally:
            print("\n" + "="*50)
            input("El script ha finalizado. La ventana del navegador permanecerá abierta para tu inspección. \nPRESIONA ENTER EN ESTA CONSOLA PARA CERRAR EL NAVEGADOR.")
            print("="*50)
            mi_driver.quit()
            print("Driver de Selenium cerrado.")
    else:
        print("No se pudo inicializar el driver de Selenium.")