**Crear y Activar un Entorno Virtual**
    ```bash
    # Crear el entorno virtual (puedes llamarlo 'venv', 'env', etc.)
    python -m venv venv
    ```
    Para activarlo:
    * **En Windows (PowerShell/CMD):**
        ```powershell
        .\venv\Scripts\activate
        ```
    * **En macOS / Linux (bash/zsh):**
        ```bash
        source venv/bin/activate
        ```
    Después de activarlo, verás `(venv)` al principio del prompt de tu terminal.

3.  **Instalar Dependencias**
    Con el entorno virtual activado, instala todas las bibliotecas necesarias ejecutando:
    ```bash
    pip install -r requirements.txt
    ```


### Configuración de la API Key

Este proyecto utiliza el servicio de proxy [ScrapeOps](https://scrapeops.io/) para evitar bloqueos al hacer scraping. Necesitarás una API Key.

1.  **Crear una Cuenta en ScrapeOps:**
    * Ve a [https://scrapeops.io/](https://scrapeops.io/).
    * Regístrate para obtener una cuenta. Ofrecen un plan gratuito que es suficiente para empezar y probar el proyecto.
    * Una vez registrado, ve a tu "Dashboard" y copia tu **API Key**.

2.  **Crear el Archivo `config.json`:**
    * En la raíz de tu proyecto, crea un nuevo archivo y nómbralo `config.json`.
    * Abre el archivo y pega el siguiente contenido:
        ```json
        {
          "api_key": "AQUI_VA_TU_API_KEY_DE_SCRAPEOPS"
        }
        ```
    * **Importante:** Reemplaza `"AQUI_VA_TU_API_KEY_DE_SCRAPEOPS"` con la clave API real que copiaste de tu dashboard de ScrapeOps. 



    ## Modo de Uso

El flujo de trabajo se ejecuta en dos pasos. Los parámetros de búsqueda se configuran directamente en los archivos de Python antes de ejecutarlos.

### Paso 1: Ejecutar el Crawler (`Zillow_Crawler.py`)

Este script encuentra los links de las propiedades según los filtros que definas.

1.  **Configura tu Búsqueda:** Abre el archivo `Zillow_Crawler.py` con un editor de texto. Ve hasta el final del archivo, al bloque `if __name__ == "__main__":`, y modifica las variables según tus necesidades:
    ```python
    # --- Bloque de Ejecución ---
    if __name__ == "__main__":
        ciudad_estado_a_buscar = "Stamford, CT" # <-- Cambia la ciudad aquí
        tipo_de_listado_param = "rentals"      # <-- "rentals" o "for_sale"
        
        # --- Configura los filtros ---
        aplicar_orden_nuevos = True            # <-- True para ordenar por "Newest"
        precio_minimo_alquiler = 3000          # <-- Cambia el precio mínimo o pon None para no filtrar
        dias_en_zillow = "1"                   # <-- Cambia los días o pon None para no filtrar
        
        # ... el resto del código llama a las funciones con estos valores
    ```
2.  **Ejecuta el Crawler:**
    Una vez guardados los cambios, ejecuta el script desde tu terminal (con el entorno virtual activado):
    ```bash
    python Zillow_Crawler.py
    ```
3.  **Salida:** El script generará un archivo JSON (ej. `zillow_links_stamford-ct_rentals_newest_minprice3000_last1days.json`) con la lista de URLs de las propiedades encontradas que cumplen con tus filtros.

### Paso 2: Ejecutar el Scraper de Detalles (`Zillow_Scraper.py`)

Este script procesa los links del paso anterior para extraer los detalles.

1.  **Configura el Archivo de Entrada:** Abre el archivo `Zillow_Scraper.py` y asegúrate de que la variable `archivo_json_entrada` dentro del bloque `if __name__ == "__main__":` apunte al archivo JSON que se generó en el Paso 1.
    ```python
    # dentro de Zillow_Scraper.py
    if __name__ == "__main__":
        # Asegúrate de que este nombre de archivo coincida con la salida del crawler
        archivo_json_entrada = "zillow_links_stamford-ct_rentals_newest_minprice3000_last1days.json" 
        archivo_csv_salida = "Zillow_Owner_Listings_Report.csv"
        # ...
    ```
2.  **Ejecuta el Scraper:**
    ```bash
    python Zillow_Scraper.py
    ```
3.  **Salida:** El script generará el archivo `Zillow_Owner_Listings_Report.csv` con los datos finales de las propiedades publicadas por dueños.

 





### Arriba están las versiones estables del Scraper. A continuación esta la descripción de "Testing_crawler.py" que es donde corro pruebas y depuro. Estas son sus caracteristicas: 

## Características Principales

-   **Filtrado Interactivo en UI:** El script no solo navega a una página, sino que hace clic en botones, menús desplegables y rellena campos de texto para aplicar filtros de orden ("Newest"), precio mínimo y días de publicación.
-   **Lógica de Fallback (Móvil/Web):** Para maximizar la robustez, el script primero intenta aplicar los filtros usando selectores diseñados para la **vista móvil** de Zillow. Si falla, automáticamente intenta un segundo set de selectores diseñados para la **vista de escritorio/web**.
-   **Extracción desde `__NEXT_DATA__`:** Prioriza la extracción de datos desde el objeto JSON `<script id="__NEXT_DATA__">` de Zillow. Esta es una fuente de datos estructurada que el propio frontend del sitio utiliza, lo que la hace más fiable y completa que parsear el HTML visual.
-   **Configuración Dinámica:** Al ejecutarse, el script pide al usuario que introduzca los parámetros de búsqueda (ciudad, precio, días), haciendo cada ejecución flexible y sin necesidad de modificar el código.
-   **Manejo de Errores y Reintentos:** Implementa un bucle de reintentos para la carga inicial de la página, haciéndolo resiliente a fallos intermitentes de red o del proxy.
-   **Prevención de Bloqueos:** Utiliza **ScrapeOps** para la gestión de proxies residenciales y una configuración de **Selenium** con múltiples opciones para reducir la probabilidad de ser detectado como un bot.
-   **Modo de Depuración:** Al finalizar, deja la ventana del navegador abierta para permitir la inspección visual del resultado final, cerrándose solo cuando el usuario presiona "Enter" en la consola.


### Cuenta con muchas mas funcionalidades que "Zillow_Crawler.py" pero aún no obtuve resultados solidos como para hacerlo el script principal. 