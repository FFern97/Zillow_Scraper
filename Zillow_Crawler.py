import time
import json
import random
import re 
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
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
        print(f"  [Mobile] Intentando aplicar filtro de orden: '{sort_by}'...")
        sort_button = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label="Sort Properties"]')))
        sort_button.click()
        print("  [Mobile] Clic en el botón 'Sort' realizado.")
        time.sleep(random.uniform(1.5, 2.5))
        newest_option = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-key="days"]')))
        newest_option.click()
        print("  [Mobile] Clic en la opción 'Newest' realizado.")
        time.sleep(random.uniform(4, 6))
        return True
    except Exception as e: print(f"    ERROR [Mobile]: No se pudo aplicar el filtro de orden 'Newest'."); return False

def aplicar_filtro_precio_mobile(driver, min_price):
    try:
        print(f"  [Mobile] Intentando aplicar filtro de precio mínimo: ${min_price}")
        price_button = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.XPATH, "//button[.//span[text()='Price']]")))
        price_button.click()
        print("  [Mobile] Clic en el botón 'Price' realizado.")
        time.sleep(random.uniform(1.5, 2.5))
        min_price_input = WebDriverWait(driver, 15).until(EC.visibility_of_element_located((By.CSS_SELECTOR, 'input[placeholder="No Min"]')))
        min_price_input.clear(); min_price_input.send_keys(str(min_price))
        print(f"  [Mobile] Precio mínimo '{min_price}' introducido.")
        time.sleep(random.uniform(0.5, 1))
        apply_button = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'See') and contains(text(), 'rentals')]")))
        apply_button.click()
        print("  [Mobile] Clic en el botón 'Apply' de precio realizado.")
        time.sleep(random.uniform(4, 6))
        return True
    except Exception as e: print(f"    ERROR [Mobile]: No se pudo aplicar el filtro de precio."); return False

def aplicar_filtros_vista_mobile(driver, sort_by_newest, min_price, tipo_listado):
    if sort_by_newest:
        if not aplicar_filtro_sort_mobile(driver): return False
    if min_price is not None and tipo_listado.lower() == "rentals":
        if not aplicar_filtro_precio_mobile(driver, min_price): return False
    print("¡ÉXITO! Todos los filtros de la vista móvil se aplicaron correctamente.")
    return True

# --- Funciones para Aplicar Filtros (VISTA WEB) ---
def aplicar_filtro_sort_web(driver, sort_by="Newest"):
    """Aplica el filtro 'Newest' en la vista web usando los selectores encontrados."""
    try:
        print(f"  [Web] Intentando aplicar filtro de orden: '{sort_by}'...")
        
        # Selector para el BOTÓN PRINCIPAL de 'Sort' 
        selector_boton_sort_web = 'button#sort-popover'
        
        print(f"  [Web] Buscando el botón 'Sort' principal con selector: {selector_boton_sort_web}")
        sort_button = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector_boton_sort_web)))
        sort_button.click()
        print("  [Web] Clic en el botón 'Sort' principal realizado.")
        time.sleep(random.uniform(1.5, 2.5))

        # Selector para la OPCIÓN 'Newest' en el menú desplegable
        selector_opcion_newest_web = 'button[data-value="days"]'
        
        print(f"  [Web] Buscando la opción '{sort_by}' con el selector: {selector_opcion_newest_web}")
        newest_option = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector_opcion_newest_web)))
        newest_option.click()
        print("  [Web] Clic en la opción 'Newest' realizado.")
        
        time.sleep(random.uniform(4, 6)) # Esperar a que los resultados se reordenen
        return True
    except Exception as e:
        print(f"    ERROR [Web]: No se pudo aplicar el filtro de orden 'Newest'. Causa: {e}")
        return False

def aplicar_filtro_precio_web(driver, min_price):
    """PLACEHOLDER: Aplica el filtro de precio en la vista web."""
    print("  [Web] Intentando aplicar filtro de precio (función placeholder)...")
    print("    ERROR [Web]: Esta función es un placeholder. Debes añadir los selectores de la vista web para el precio.")
    return False

def aplicar_filtros_vista_web(driver, sort_by_newest, min_price, tipo_listado):
    """Agrupa y ejecuta la secuencia de filtros para la vista web."""
    if sort_by_newest:
        if not aplicar_filtro_sort_web(driver): return False
    if min_price is not None and tipo_listado.lower() == "rentals":
        if not aplicar_filtro_precio_web(driver, min_price): return False
    print("¡ÉXITO! Todos los filtros de la vista web se aplicaron correctamente.")
    return True

# --- Función Principal del Scraper (con lógica de fallback) ---
def extraer_links_propiedades_zillow(driver, ciudad_estado_param, tipo_listado="rentals", sort_by_newest=True, min_price=None):
    print(f"Iniciando extracción para: {ciudad_estado_param} (Tipo: {tipo_listado})")
    ubicacion_formateada = formatear_ubicacion_zillow(ciudad_estado_param)
    if not ubicacion_formateada: return []
    
    target_zillow_url = f"https://www.zillow.com/{ubicacion_formateada}/{tipo_listado.lower()}/"
    print(f"Navegando a la URL base (vía ScrapeOps): {target_zillow_url}")
    url_scrapeops = get_scrapeops_url(target_zillow_url)
    driver.get(url_scrapeops)

    try:
        print("Esperando a que la página de resultados cargue...")
        WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.ID, "__NEXT_DATA__")))
        print("Página de resultados inicial cargada.")
        
        filtros_aplicados_con_exito = False
        
        print("\n--- Intento 1: Aplicar filtros con selectores de VISTA MÓVIL ---")
        if aplicar_filtros_vista_mobile(driver, sort_by_newest, min_price, tipo_listado):
            filtros_aplicados_con_exito = True
        else:
            print("\n--- Intento 2: Fallback a selectores de VISTA WEB ---")
            if aplicar_filtros_vista_web(driver, sort_by_newest, min_price, tipo_listado):
                filtros_aplicados_con_exito = True

        if not filtros_aplicados_con_exito:
            print("\nFallaron todos los intentos de filtrado (Móvil y Web). La extracción se detiene pero el driver quedará abierto para inspección.")
            return []

        print("\n¡Filtros aplicados con éxito! Extrayendo __NEXT_DATA__ de la página final...")
        selector_next_data = 'script[id="__NEXT_DATA__"]'
        next_data_script_element = WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR, selector_next_data)))
        json_content_str = next_data_script_element.get_attribute('innerHTML')
        
        links_propiedades_encontrados_set = set()
        if json_content_str:
            data_next = json.loads(json_content_str)
            list_results_array = data_next.get("props", {}).get("pageProps", {}).get("searchPageState", {}).get("cat1", {}).get("searchResults", {}).get("listResults", [])
            print(f"__NEXT_DATA__ parseado. Encontrados {len(list_results_array)} resultados en 'listResults'.")
            for prop_item in list_results_array:
                if isinstance(prop_item, dict) and "detailUrl" in prop_item:
                    links_propiedades_encontrados_set.add(urljoin("https://www.zillow.com", prop_item.get("detailUrl")))
        return list(links_propiedades_encontrados_set)

    except Exception as e:
        print(f"Ocurrió un error mayor en la extracción: {e}")
        driver.save_screenshot("error_screenshot_final.png"); print("Captura de pantalla de error guardada.")
        return []

# --- Bloque de Ejecución ---
if __name__ == "__main__":
    ciudad_estado_a_buscar = "Norwalk, CT"
    tipo_de_listado_param = "rentals"
    aplicar_orden_nuevos = True
    precio_minimo_alquiler = 3000
    
    mi_driver = configurar_driver()
    if mi_driver:
        try:
            links = extraer_links_propiedades_zillow(
                mi_driver, ciudad_estado_a_buscar, tipo_listado=tipo_de_listado_param, 
                sort_by_newest=aplicar_orden_nuevos, min_price=precio_minimo_alquiler
            )
            if links:
                print("\n" + "---" * 10 + "\n--- Links de Propiedades Extraídos ---")
                for link_idx, link_url in enumerate(links): print(f"{link_idx+1}. {link_url}")
                print(f"\nTotal de links únicos extraídos: {len(links)}")
                sort_suffix = "_newest" if aplicar_orden_nuevos else ""
                price_suffix = f"_minprice{precio_minimo_alquiler}" if precio_minimo_alquiler else ""
                output_filename = f"zillow_links_{formatear_ubicacion_zillow(ciudad_estado_a_buscar)}_{tipo_de_listado_param}{sort_suffix}{price_suffix}.json"
                with open(output_filename, "w", encoding="utf-8") as f_json: json.dump(links, f_json, indent=4)
                print(f"Links guardados en {output_filename}")
            else: print("\nNo se extrajeron links de propiedades (posiblemente por fallo en los filtros o no habían resultados).")
        finally:
            print("\n" + "="*50)
            input("El script ha finalizado. La ventana del navegador permanecerá abierta para tu inspección. \nPRESIONA ENTER EN ESTA CONSOLA PARA CERRAR EL NAVEGADOR.")
            print("="*50)
            mi_driver.quit()
            print("Driver de Selenium cerrado.")
    else: print("No se pudo inicializar el driver de Selenium.")