# Pull Request: AtHome scraping en vivo para Railway

## Descripción

Agrega un segundo parser para AtHome (`athome_web`) que scrapea el catálogo HTML en vivo, permitiendo que la sincronización automática en Railway incluya también AtHome — no solo FixOEM/SupraTec.

Hasta ahora AtHome solo funcionaba con el parser file-based `athome_v1`, que requiere tener los archivos `catalogo_athome_parte*.json` localmente (gitignored, no se suben al repo). Eso hacía imposible que el cron diario en Railway sincronizara AtHome, porque el contenedor de producción no tenía esos archivos.

Ahora cada entorno puede elegir su parser:

| Entorno | `tipo_parser` recomendado | Tiempo de sync |
|---|---|---|
| Local (dev) | `athome_v1` (archivos JSON) | Segundos |
| Railway (prod) | `athome_web` (scraping) | 3-5 min |

Ambos parsers producen el mismo formato de dict `{nombre, sku, precio, stock, disponible, url}`, así que el resto del pipeline (`parse()`, upsert, mark-and-sweep) es el mismo.

---

## Cambios incluidos

### Código

| Archivo | Cambio |
|---|---|
| `apps/cotizaciones/models.py` | `FuenteApi.PARSER_CHOICES` agrega `('athome_web', 'AtHome web (scraping JSON-LD en vivo)')`. Help text de `base_url` actualizado. |
| `apps/cotizaciones/migrations/0009_alter_fuenteapi_base_url_alter_fuenteapi_tipo_parser.py` | Migración automática por el cambio en choices + help_text. |
| `apps/cotizaciones/management/commands/sync_productos_api.py` | Imports nuevos (`bs4`, `re`, `math`, `ThreadPoolExecutor`). Nueva clase `AtHomeWebFetcher` que hereda de `AtHomeV1Fetcher` (reutiliza `parse()`) y override `fetch_first_page()` + `fetch_all()` con scraping HTTP + BeautifulSoup. Registrado en `PARSERS`. |
| `requirements/base.txt` | Agrega `beautifulsoup4==4.14.3` (ahora también lo necesita producción). |

### Documentación

| Archivo | Cambio |
|---|---|
| `docs/cotizaciones/doc-athome-integration.md` | Reescrito: tabla comparativa de los 2 parsers, instrucciones específicas para configurar `athome_web` en Railway, parámetros del scraper, safety net. |
| `docs/PR/pr-athome-railway-scraping.md` | Nuevo — este doc. |

---

## Implementación del scraper

`AtHomeWebFetcher` adapta la lógica de `docs/api-samples/athome/script.py` al patrón de fetchers del comando Django:

```python
class AtHomeWebFetcher(AtHomeV1Fetcher):
    tipo_parser = 'athome_web'

    PRODUCTS_PER_PAGE = 12
    WORKERS = 3          # más conservador que el script (5) para no estresar AtHome
    DELAY_BATCH = 0.5    # 500ms entre lotes
    FALLBACK_MAX_PAGES = 200  # si no se detecta productsCount

    def fetch_first_page(self): ...
    def fetch_all(self): ...
```

Flujo de `fetch_all()`:

1. GET `base_url` → buscar `productsCount: N` en el HTML para saber cuántas páginas hay
2. Si no se encuentra → usar `FALLBACK_MAX_PAGES`
3. Procesar páginas en lotes de `WORKERS` con `ThreadPoolExecutor` paralelo
4. Por cada página: buscar `<script type="application/ld+json">` y filtrar `@type == Product`
5. Si una página devuelve 0 productos → asumir fin del catálogo, break
6. Acumular resultados preservando orden por número de página

### Por qué hereda de `AtHomeV1Fetcher`

`AtHomeV1Fetcher.parse()` convierte un dict `{nombre, sku, precio, ...}` en una instancia `ApiProductoCatalogo`. El scraper produce **el mismo formato de dict** (intencionalmente, para que sea compatible). Heredando, evitamos duplicar `parse()`.

---

## Migración en BD

Aplicar `0009_alter_fuenteapi_base_url_alter_fuenteapi_tipo_parser`:

```bash
python manage.py migrate cotizaciones
```

No tiene side effects en datos — solo actualiza el field validator (`choices`) y el `help_text`.

---

## Setup en cada entorno post-merge

### Local (dev) — opcional, mantiene workflow actual

Si quieres que tu BD local también use scraping en lugar de los archivos JSON:

```bash
python manage.py shell -c "from apps.cotizaciones.models import FuenteApi; FuenteApi.objects.filter(slug='athome').update(tipo_parser='athome_web', base_url='https://www.athomemx.mx/productos')"
```

Si no, **dejarlo igual** (`tipo_parser='athome_v1'`, `base_url='data/athome'`) y seguir corriendo el scraper standalone manualmente cuando quieras refrescar los JSONs.

### Railway (producción) — requerido para que el cron funcione

```bash
# Desde el shell de Railway en el servicio TecnoFix:
python manage.py shell -c "from apps.cotizaciones.models import FuenteApi; FuenteApi.objects.filter(slug='athome').update(tipo_parser='athome_web', base_url='https://www.athomemx.mx/productos', activo=True)"
```

Después de eso, el cron `sync_productos_api --all-active --no-interactive` que corre cada noche a las 4 AM CDMX scrapeará AtHome automáticamente.

---

## Compatibilidad

- `athome_v1` sigue funcionando exactamente igual. Si tienes una FuenteApi en `athome_v1`, el cambio de migración no afecta su comportamiento.
- El registro `FuenteApi` con `slug='athome'` se queda en `athome_v1` por default (no cambia automáticamente). El switch es manual y por entorno.
- No hay cambios al menú interactivo, ni a `--fuente`, `--all-active`, `--no-interactive`.
- Mark-and-sweep aplica igual a ambos parsers.

---

## Pruebas

### Local — fetch_first_page (sin tocar BD)

```python
python manage.py shell -c "
from apps.cotizaciones.models import FuenteApi
from apps.cotizaciones.management.commands.sync_productos_api import AtHomeWebFetcher

class S:
    def ERROR(self, x): return x
    def WARNING(self, x): return x
    def SUCCESS(self, x): return x
class O:
    def write(self, x): print(x)

f = FuenteApi(slug='athome-test', base_url='https://www.athomemx.mx/productos', tipo_parser='athome_web')
fetcher = AtHomeWebFetcher(f, O(), S())
products = fetcher.fetch_first_page()
print(f'Productos: {len(products)}')
print(products[0] if products else 'vacío')
"
```

Resultado esperado: 12 productos con `{nombre, sku, precio, stock, disponible, url}` poblados.

### Railway — primer Trigger Now del cron

Después de mergear y aplicar la migración en Railway:

1. Aplicar migración: `python manage.py migrate cotizaciones` (o el cron lo hace al primer deploy si Dockerfile corre `migrate --noinput`).
2. Ejecutar el switch de `FuenteApi` con el comando shell del bloque anterior.
3. En el dashboard de Railway → servicio cron → **Trigger Now**.
4. Ver logs: deberían aparecer las 3 fuentes (FixOEM, SupraTec, AtHome) con sus totales y mark-and-sweep correspondiente.

---

## Riesgos y consideraciones

| Riesgo | Mitigación |
|---|---|
| AtHome bloquea por exceso de requests | `WORKERS=3` (vs 5 del script standalone) + 0.5s entre lotes. User-Agent realista. |
| AtHome cambia estructura HTML | `fetch_all()` retorna 0 productos → safety net salta mark-and-sweep. Catálogo se queda con datos del día anterior. Hay que revisar logs. |
| Scraping tarda más de lo esperado | Cron job de Railway tiene timeout flexible. ~5 min está OK. |
| `productsCount` no encontrado en HTML | Fallback de 200 páginas — algo conservador para no scrapear infinito. El bucle también frena cuando una página devuelve 0 productos. |
