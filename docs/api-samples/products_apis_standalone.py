import requests
import time
import json
import os
import shutil

TIENDAS = {
    "1": {"nombre": "FixOEM",     "url": "https://fixoem.com"},
    "2": {"nombre": "SupraTecMX", "url": "https://www.supratecmx.com"},
}

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}


def fetch_page(base_url: str, page: int) -> list:
    url = f"{base_url}/products.json?limit=250&page={page}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code != 200:
        print(f"Error {response.status_code} al obtener la página {page}.")
        return []
    return response.json().get('products', [])


def get_all_products(base_url: str) -> list:
    all_products = []
    page = 1
    print(f"--- Iniciando extracción de: {base_url} ---")
    while True:
        data = fetch_page(base_url, page)
        if not data:
            print("Ya no hay más productos.")
            break
        all_products.extend(data)
        print(f"Página {page} lista. Llevamos {len(all_products)} productos...")
        page += 1
        time.sleep(1)
    return all_products


def analizar_valor(valor):
    if isinstance(valor, dict):
        return {"tipo": "dict", "campos": {k: analizar_valor(v) for k, v in valor.items()}}
    if isinstance(valor, list):
        if not valor:
            return {"tipo": "list", "elemento": "vacío"}
        return {"tipo": "list", "elemento": analizar_valor(valor[0])}
    if valor is None:
        return {"tipo": "null", "ejemplo": None}
    if isinstance(valor, bool):
        return {"tipo": "bool", "ejemplo": valor}
    if isinstance(valor, int):
        return {"tipo": "int", "ejemplo": valor}
    if isinstance(valor, float):
        return {"tipo": "float", "ejemplo": valor}
    ejemplo = valor if not isinstance(valor, str) or len(valor) <= 120 else valor[:120] + "..."
    return {"tipo": "str", "ejemplo": ejemplo}


def actualizar_estructura(productos: list, carpeta_tienda: str):
    if not productos:
        return
    nueva = {"total_campos": len(productos[0]), "estructura": {k: analizar_valor(v) for k, v in productos[0].items()}}
    ruta = os.path.join(carpeta_tienda, "estructura.json")
    os.makedirs(carpeta_tienda, exist_ok=True)
    if os.path.exists(ruta):
        with open(ruta, encoding="utf-8") as f:
            existente = json.load(f)
        if existente == nueva:
            print("  Estructura sin cambios.")
            return
        print("  Estructura actualizada.")
    else:
        print("  Estructura generada.")
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(nueva, f, indent=4, ensure_ascii=False)


def preparar_carpeta(carpeta: str):
    if os.path.exists(carpeta):
        shutil.rmtree(carpeta)
    os.makedirs(carpeta)


def guardar_en_lotes(productos: list, carpeta: str, lote: int):
    preparar_carpeta(carpeta)
    total = len(productos)
    num_lotes = (total + lote - 1) // lote
    for i in range(num_lotes):
        chunk = productos[i * lote:(i + 1) * lote]
        filename = os.path.join(carpeta, f"lote_{i + 1:03d}.json")
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(chunk, f, indent=4, ensure_ascii=False)
    print(f"  {total} productos en {num_lotes} archivos → '{carpeta}/'")


def guardar_archivo_unico(productos: list, carpeta: str, filename: str):
    preparar_carpeta(carpeta)
    ruta = os.path.join(carpeta, filename)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(productos, f, indent=4, ensure_ascii=False)
    print(f"  {len(productos)} productos → '{ruta}'")


def elegir_tiendas() -> list:
    print("\n¿De qué tienda quieres obtener productos?")
    for key, tienda in TIENDAS.items():
        print(f"  [{key}] {tienda['nombre']} — {tienda['url']}")
    print(f"  [3] Todas las tiendas")
    while True:
        opcion = input("Elige tienda: ").strip()
        if opcion == "3":
            return list(TIENDAS.values())
        if opcion in TIENDAS:
            return [TIENDAS[opcion]]
        print("Opción inválida.")


def elegir_pagina() -> int | None:
    print("\n¿Qué página quieres obtener?")
    print("  [0] Todas las páginas")
    entrada = input("Número de página (o 0 para todas): ").strip()
    try:
        page = int(entrada)
        return None if page == 0 else page
    except ValueError:
        print("Valor inválido, obteniendo todas las páginas.")
        return None


def elegir_modo_guardado() -> tuple[str, int]:
    print("\n¿Cómo quieres guardar los productos?")
    print("  [1] Un solo archivo JSON")
    print("  [2] En lotes (recomendado para más de 1000 productos)")
    opcion = input("Elige modo: ").strip()
    if opcion == "2":
        try:
            lote = int(input("¿Cuántos productos por archivo? (ej: 500): ").strip())
        except ValueError:
            lote = 500
            print("Valor inválido, usando 500.")
        return "lotes", lote
    return "unico", 0


def procesar_tienda(tienda: dict, page: int | None, modo: str, lote: int):
    nombre = tienda["nombre"].lower().replace(" ", "_")
    base_url = tienda["url"]
    carpeta = os.path.join("productos", nombre)

    print(f"\n{'='*50}")
    print(f"  {tienda['nombre']}")
    print(f"{'='*50}")

    if page is None:
        resultados = get_all_products(base_url)
        tag = "completo"
    else:
        print(f"Obteniendo página {page}...")
        resultados = fetch_page(base_url, page)
        tag = f"pagina{page}"

    if not resultados:
        print("  Sin productos.")
        return

    actualizar_estructura(resultados, carpeta)

    if modo == "lotes":
        guardar_en_lotes(resultados, os.path.join(carpeta, tag), lote)
    else:
        guardar_archivo_unico(resultados, carpeta, f"{tag}.json")


if __name__ == "__main__":
    tiendas = elegir_tiendas()
    page = elegir_pagina()
    modo, lote = elegir_modo_guardado()

    for tienda in tiendas:
        procesar_tienda(tienda, page, modo, lote)

    print("\nProceso completado.")
