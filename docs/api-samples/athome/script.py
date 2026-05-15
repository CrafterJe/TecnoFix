import requests
from bs4 import BeautifulSoup
import json
import time
import math
from concurrent.futures import ThreadPoolExecutor, as_completed

# ─────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────
BASE_URL = "https://www.athomemx.mx/productos"
PRODUCTS_PER_PAGE = 12
WORKERS = 5        # páginas en paralelo
DELAY_BATCH = 0.5  # segundos entre lotes de páginas

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)


# ─────────────────────────────────────────
# EXTRACCIÓN DE UNA PÁGINA
# ─────────────────────────────────────────
def extract_products_from_page(page: int) -> list[dict]:
    """Extrae todos los productos de una página del catálogo via JSON-LD."""
    url = f"{BASE_URL}?page={page}"

    try:
        resp = SESSION.get(url, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  [ERROR] Página {page}: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    products = []

    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, AttributeError):
            continue

        if data.get("@type") != "Product":
            continue

        offers = data.get("offers", {})
        availability_url = offers.get("availability", "")
        disponible = availability_url.endswith("InStock")
        inventory = offers.get("inventoryLevel", {})
        stock_raw = inventory.get("value", "0") if isinstance(inventory, dict) else "0"

        products.append({
            "nombre":     data.get("name"),
            "sku":        data.get("sku"),
            "precio":     float(offers.get("price", 0)),
            "stock":      int(stock_raw) if str(stock_raw).isdigit() else 0,
            "disponible": disponible,
            "url":        offers.get("url") or (data.get("mainEntityOfPage") or {}).get("@id"),
        })

    return products


# ─────────────────────────────────────────
# OBTENER TOTAL REAL DE PÁGINAS
# ─────────────────────────────────────────
def get_total_pages() -> int:
    import re
    resp = SESSION.get(BASE_URL, timeout=15)
    soup = BeautifulSoup(resp.text, "html.parser")

    for script in soup.find_all("script"):
        text = script.string or ""
        match = re.search(r'productsCount\s*[:=]\s*(\d+)', text)
        if match:
            count = int(match.group(1))
            pages = math.ceil(count / PRODUCTS_PER_PAGE)
            print(f"  Total productos: {count} → {pages} páginas")
            return pages

    return 200  # fallback


# ─────────────────────────────────────────
# SCRAPER COMPLETO CON PAGINACIÓN
# ─────────────────────────────────────────
def scrape_all_products(max_pages: int = None) -> list[dict]:
    total_pages = max_pages or get_total_pages()
    all_products = [None] * (total_pages + 1)  # índice por página para mantener orden
    found_end = False

    print(f"Iniciando scraping de {BASE_URL} ({total_pages} páginas, {WORKERS} workers)")

    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        for batch_start in range(1, total_pages + 1, WORKERS):
            if found_end:
                break
            batch = range(batch_start, min(batch_start + WORKERS, total_pages + 1))
            futures = {executor.submit(extract_products_from_page, p): p for p in batch}

            for future in as_completed(futures):
                page = futures[future]
                products = future.result()
                if not products:
                    found_end = True
                    print(f"  Página {page}: sin productos → fin del catálogo.")
                else:
                    all_products[page] = products
                    print(f"  Página {page}: {len(products)} productos")

            time.sleep(DELAY_BATCH)

    flat = [p for slot in all_products if slot for p in slot]
    print(f"Total: {len(flat)} productos")
    return flat


# ─────────────────────────────────────────
# BUSCADOR EN MEMORIA
# ─────────────────────────────────────────
def buscar_producto(catalogo: list[dict], query: str) -> list[dict]:
    """
    Búsqueda fuzzy por nombre o SKU dentro del catálogo ya cargado.
    """
    query = query.strip().lower()
    resultados = [
        p for p in catalogo
        if query in (p.get("nombre") or "").lower()
        or query in str(p.get("sku") or "").lower()
    ]
    return resultados


# ─────────────────────────────────────────
# USO PRINCIPAL
# ─────────────────────────────────────────
if __name__ == "__main__":
    # 1. Cargar catálogo completo (o solo N páginas para prueba)
    catalogo = scrape_all_products(max_pages=None)

    # 2. Guardar en JSON local como caché (lotes de 500)
    CHUNK_SIZE = 500
    num_chunks = math.ceil(len(catalogo) / CHUNK_SIZE) if catalogo else 1
    for i in range(num_chunks):
        chunk = catalogo[i * CHUNK_SIZE : (i + 1) * CHUNK_SIZE]
        filename = f"catalogo_athome_parte{i + 1:03d}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(chunk, f, ensure_ascii=False, indent=2)
        print(f"  Guardado {filename} ({len(chunk)} variantes)")
    print(f"\nCatálogo guardado en {num_chunks} archivo(s) · {len(catalogo)} variantes en total.")

    # 3. Guardar estructura del JSON
    estructura = {
        "descripcion": "Estructura de cada objeto en los archivos catalogo_athome_parteXXX.json",
        "total_variantes": len(catalogo),
        "total_archivos": num_chunks,
        "productos_por_archivo": CHUNK_SIZE,
        "campos": {
            "nombre":     {"tipo": "string",  "descripcion": "Nombre del producto"},
            "sku":        {"tipo": "string",  "descripcion": "Código SKU del producto"},
            "precio":     {"tipo": "number",  "descripcion": "Precio en MXN"},
            "stock":      {"tipo": "integer", "descripcion": "Unidades disponibles en inventario"},
            "disponible": {"tipo": "boolean", "descripcion": "True si tiene stock (InStock), False si agotado"},
            "url":        {"tipo": "string",  "descripcion": "URL completa del producto en la tienda"},
        },
        "ejemplo": catalogo[0] if catalogo else {},
    }
    with open("catalogo_athome_estructura.json", "w", encoding="utf-8") as f:
        json.dump(estructura, f, ensure_ascii=False, indent=2)
    print("Estructura guardada en catalogo_athome_estructura.json")