import time
import json
import random
import re 
import csv
import argparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from urllib.parse import urlencode

# --- (Configuración Global y Funciones Auxiliares se mantienen igual) ---
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

def get_scrapeops_url(target_url, residential=True, render_js=True, country="us"):
    if not API_KEY: return target_url
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

# --- Lógica Principal del Scraper de Detalles ---
def scrapear_detalles_de_propiedades(archivo_json_entrada, archivo_csv_salida):
    """
    Lee una lista de URLs de Zillow, visita cada una, y si es publicada por el dueño,
    extrae los detalles y los guarda en un CSV.
    """
    print(f"Iniciando scrapeo de detalles desde: {archivo_json_entrada}")
    try:
        with open(archivo_json_entrada, 'r', encoding='utf-8') as f:
            links_propiedades = json.load(f)
        if not isinstance(links_propiedades, list):
            print("Error: El archivo JSON de entrada no contiene una lista de links.")
            return
        print(f"Se cargaron {len(links_propiedades)} links de propiedades para procesar.")
    except Exception as e:
        print(f"Error al leer el archivo JSON de entrada '{archivo_json_entrada}': {e}")
        return

    columnas_csv = ["Adress", "", "", "url link", "phone number", "", "property owner name", "", "date", "", "", "price"]
    
    with open(archivo_csv_salida, 'w', newline='', encoding='utf-8') as f_csv:
        writer = csv.writer(f_csv)
        writer.writerow(columnas_csv)

        mi_driver = configurar_driver()
        if not mi_driver:
            print("No se pudo iniciar el driver, abortando scrapeo de detalles.")
            return

        try:
            for i, link in enumerate(links_propiedades):
                print(f"\n[{i+1}/{len(links_propiedades)}] Procesando URL: {link}")
                
                url_scrapeops = get_scrapeops_url(link)
                mi_driver.get(url_scrapeops)

                try:
                    selector_owner = "//div[@class='ds-listing-agent-header' and text()='Listed by property owner']"
                    print("  Verificando si es 'Listed by property owner'...")
                    WebDriverWait(mi_driver, 15).until(EC.presence_of_element_located((By.XPATH, selector_owner)))
                    print("  ¡Confirmado! La propiedad es publicada por el dueño.")

                    address = ""; owner_name = ""; phone_number = ""; publication_date = ""; price = ""

                    try:
                        address_selector = 'div[class^="styles__AddressWrapper-"] h1'
                        address = mi_driver.find_element(By.CSS_SELECTOR, address_selector).text
                    except: print("    - Dirección no encontrada.")
                    
                    try:
                        owner_name = mi_driver.find_element(By.CSS_SELECTOR, "span.ds-listing-agent-display-name").text
                    except: print("    - Nombre del dueño no encontrado.")
                    
                    try:
                        phone_number = mi_driver.find_element(By.CSS_SELECTOR, "li.ds-listing-agent-info-text").text
                    except: print("    - Teléfono no encontrado.")

                    try:
                        date_selector = 'tbody tr:first-child span[data-testid="date-info"]'
                        publication_date = mi_driver.find_element(By.CSS_SELECTOR, date_selector).text
                    except: print("    - Fecha de publicación no encontrada.")
                    
                    # --- LÓGICA DE EXTRACCIÓN DE PRECIO ACTUALIZADA ---
                    try:
                        price_selector = 'span[data-testid="price"]'
                        price_element = mi_driver.find_element(By.CSS_SELECTOR, price_selector)
                        # El texto puede ser "$3,399/mo", usamos .find_element para obtener el span interno sin "/mo"
                        # o procesamos el texto. El texto del elemento principal puede ser más fácil de obtener.
                        full_price_text = price_element.text
                        if "/mo" in full_price_text:
                            price = full_price_text.split("/mo")[0].strip()
                        else:
                            price = full_price_text.strip()
                    except: 
                        print("    - Precio no encontrado con selector principal. Intentando con la tabla de historial como fallback...")
                        # Fallback al método anterior si el principal no funciona
                        try:
                            price_selector_fallback = 'tbody tr:first-child td[data-testid="price-money-cell"] span[class*="StyledPriceText"]'
                            price = mi_driver.find_element(By.CSS_SELECTOR, price_selector_fallback).text
                        except:
                            print("    - Precio no encontrado tampoco en la tabla de historial.")
                    # --- FIN DE LA LÓGICA DE PRECIO ---

                    fila_csv = [
                        address, "", "", link, phone_number, "", 
                        owner_name, "", publication_date, "", "", price
                    ]
                    
                    writer.writerow(fila_csv)
                    print(f"  -> Datos guardados para '{owner_name or 'Dueño Desconocido'}' en el CSV.")

                except Exception as e_owner_check:
                    print(f"  No es una publicación de dueño o falló la espera. Saltando.")
                
                time.sleep(random.uniform(2, 5))

        finally:
            if mi_driver:
                mi_driver.quit()
                print("\nDriver de Selenium cerrado.")


if __name__ == "__main__":
    # Estos nombres serán pasados por main_pipeline.py en el futuro
    # Por ahora, para pruebas directas, asegúrate de que el archivo de entrada exista
    archivo_json_entrada = "zillow_links_stamford-ct_rentals_newest_minprice3000.json"
    archivo_csv_salida = "Zillow_Owner_Listings_Report_v3.csv"
    
    scrapear_detalles_de_propiedades(archivo_json_entrada, archivo_csv_salida)