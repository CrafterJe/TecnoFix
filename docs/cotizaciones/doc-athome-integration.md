# Cotizaciones — Integración AtHome (dos parsers)

## Qué es

AtHome (`athomemx.mx`) es una tercera fuente de productos del módulo de cotizaciones. A diferencia de FixOEM y SupraTecMX (que usan la API pública de Shopify), AtHome **no expone una API JSON**, así que se necesitan estrategias propias:

| `tipo_parser` | Cómo obtiene los datos | Cuándo usarlo |
|---|---|---|
| `athome_v1` | Lee archivos JSON pre-generados (`catalogo_athome_parte*.json`) localmente | Dev local — rápido (segundos), no requiere internet |
| `athome_web` | Scrapea el catálogo HTML en vivo extrayendo JSON-LD | Producción / Railway — funciona en cualquier ambiente con internet, ~3-5 min por sync |

La selección de parser se hace por entorno: cada `FuenteApi` (registro de BD) tiene su propio `tipo_parser`, así que local puede usar `athome_v1` (rápido) y Railway puede usar `athome_web` (autónomo). El código y el resto del flujo (mark-and-sweep, BD, serializers) es idéntico para ambos.

---

## Cambios de schema (migraciones 0006 y 0007)

### Migración 0006 — `athome_schema`

| Modelo | Campo | Cambio |
|---|---|---|
| `FuenteApi` | `PARSER_CHOICES` | Agrega `('athome_v1', 'AtHome v1 (archivos JSON locales)')` |
| `FuenteApi` | `base_url` | `URLField` → `CharField(500)` para aceptar rutas locales además de URLs HTTP |
| `ApiProductoCatalogo` | `producto_id_externo` | `BigIntegerField` → `CharField(100)` para soportar SKUs alfanuméricos o numéricos |
| `ApiProductoCatalogo` | `url_producto` | Campo nuevo `URLField(blank=True)` — URL directa del producto (solo lo provee AtHome) |

> `producto_id_externo` se cambió a `CharField` como medida preventiva: el formato de SKU de AtHome no está garantizado como siempre numérico. Para Shopify el comportamiento es idéntico (los IDs se guardan como strings numéricos).

### Migración 0007 — `athome_fuente_data`

Inserta el registro `FuenteApi` de AtHome en la BD:

```
slug       = "athome"
nombre     = "AtHome"
base_url   = <ruta calculada en tiempo de migración — puede ser absoluta o relativa>
tipo_parser = "athome_v1"
activo     = True
orden      = 3
```

> **Recomendación**: usar **ruta relativa** `data/athome` para que el setup sea portable entre dispositivos. El fetcher resuelve `base_url` relativa contra `BASE_DIR` del proyecto. Si los archivos están en otra carpeta, actualizar `base_url` desde `/admin/cotizaciones/fuenteapi/`.

---

## Nuevo parser: `AtHomeV1Fetcher`

Archivo: `apps/cotizaciones/management/commands/sync_productos_api.py`

### Estructura de los archivos fuente

```
TecnoFix-BackEnd/data/athome/           ← carpeta gitignored, no se sube al repo
├── catalogo_athome_parte001.json
├── catalogo_athome_parte002.json
├── ...
└── catalogo_athome_parte020.json
```

20 archivos, ~500 productos cada uno. Total: ~10,000 productos.

> Estos archivos **no están en el repo** (ver `.gitignore: data/`) porque pesan varios MB y son regenerables. Cada dispositivo donde quieras correr el sync de AtHome necesita generar los suyos (ver siguiente sección).

### Formato de cada producto

```json
{
  "nombre": "MICA HIDROGEL RELIFE GF-3R MATTE PRIVACY",
  "sku": "14339",
  "precio": 1289.98,
  "stock": 3,
  "disponible": true,
  "url": "https://www.athomemx.mx/productos/mica-hidrogel-relife-gf-3r-matte-privacy-vd81i/"
}
```

### Mapeo al modelo `ApiProductoCatalogo`

| Campo JSON | Campo modelo | Notas |
|---|---|---|
| `sku` | `producto_id_externo` | Como string (`sku[:100]`) |
| `nombre` | `titulo` | Truncado a 500 chars |
| `precio` | `precio` | Convertido a `Decimal` |
| `disponible` | `disponible` | Boolean directo |
| `url` | `url_producto` | Nuevo campo, URL completa |
| — | `handle` | Vacío (no aplica) |
| — | `vendor` | Vacío (no aplica) |
| — | `product_type` | Vacío (no aplica) |
| `stock` | — | No se guarda (solo `disponible` es necesario) |

### Resolución de ruta

```python
def _get_directorio(self) -> Path:
    ruta = self.fuente.base_url
    p = Path(ruta)
    if p.is_absolute():
        return p
    return Path(settings.BASE_DIR) / ruta
```

Si `base_url` es absoluta (caso normal) se usa directo. Si es relativa, se resuelve desde `BASE_DIR`.

---

## Cambio en el serializer

`ApiProductoCatalogoSerializer` expone el nuevo campo:

```python
fields = [
    'id', 'fuente',
    'producto_id_externo', 'titulo', 'precio',
    'disponible', 'handle', 'vendor', 'product_type',
    'url_producto',   # nuevo
    'synced_at',
]
```

> **Nota para el front**: `producto_id_externo` es ahora `string` (era `number`). `url_producto` viene vacío para productos Shopify y con URL completa para AtHome.

---

## Generar los JSON localmente (primera vez en un equipo)

Los archivos `catalogo_athome_parte*.json` no están en el repo; hay que generarlos con el scraper standalone:

```bash
# 1. Instalar dependencia del scraper (NO va a requirements/ del backend; es solo para generar los JSONs)
pip install beautifulsoup4

# 2. Crear carpeta destino y correr el scraper desde ahí
mkdir -p data/athome
cd data/athome
python ../../docs/api-samples/athome/script.py
# Tarda varios minutos (~200 páginas, 5 workers en paralelo)
# Genera catalogo_athome_parte001.json ... parteXXX.json + catalogo_athome_estructura.json

cd ../..

# 3. (Solo primera vez) Apuntar base_url a esa carpeta — desde /admin/cotizaciones/fuenteapi/
#    Editar la fuente "AtHome" → base_url = data/athome  (ruta relativa al proyecto)
```

## Sincronización a BD

```bash
# Modo interactivo (manual, local)
python manage.py sync_productos_api
# Opción: "Sincronizar TODAS las fuentes" → incluye AtHome
# Opción: "Sincronizar solo AtHome"

# Modo no interactivo (cron, scripting)
python manage.py sync_productos_api --fuente athome --no-interactive
```

AtHome lee los archivos JSON locales en lugar de hacer requests HTTP. El flujo de `bulk_create` con upsert es idéntico al de Shopify.

### Mark-and-sweep

Después del upsert, los productos de cada fuente que **no fueron tocados** en este sync (su `synced_at` quedó anterior al inicio del sync) se marcan como `disponible=False`. Esto refleja descontinuaciones del catálogo de origen sin borrar registros (mantiene histórico).

Safety net: si `fetch_all()` falla o regresa vacío, el mark-and-sweep **se salta** para esa fuente — un fallo temporal no marca todo el catálogo como agotado.

---

## AtHome en producción (Railway)

Railway usa **`athome_web`** (scraping directo). El cron diario `sync_productos_api --all-active --no-interactive` scrapea el HTML de AtHome cada noche y actualiza el catálogo en la BD de producción.

### Configurar AtHome en Railway por primera vez

Ejecutar (vía shell de Railway sobre el servicio backend):

```python
python manage.py shell -c "from apps.cotizaciones.models import FuenteApi; FuenteApi.objects.filter(slug='athome').update(tipo_parser='athome_web', base_url='https://www.athomemx.mx/productos', activo=True)"
```

Esto cambia:
- `tipo_parser`: `athome_v1` → `athome_web`
- `base_url`: ruta local → URL del catálogo
- `activo`: asegura que entre al `--all-active`

### Parámetros del scraper

| Constante | Valor | Por qué |
|---|---|---|
| `WORKERS` | 3 | Más conservador que el script standalone (5) para no estresar el servidor de AtHome |
| `DELAY_BATCH` | 0.5s | Pausa entre lotes de 3 páginas |
| `PRODUCTS_PER_PAGE` | 12 | Lo que devuelve AtHome por página |
| `FALLBACK_MAX_PAGES` | 200 | Si no se detecta `productsCount` en el HTML, frena después de 200 páginas |

### Cuánto tarda

Con ~10,000 productos / 12 por página = ~833 páginas, en lotes de 3 con 0.5s de pausa = **~3-5 minutos** en Railway. El cron corre a las 4 AM CDMX (10:00 UTC), tráfico bajo en AtHome.

### Safety net

Si el scraping falla (timeout, AtHome devuelve HTML inválido, cambio de estructura), `fetch_all()` retorna lista vacía. El comando lo detecta y **se salta mark-and-sweep para esa fuente**: el catálogo no se marca como agotado, queda con los datos del día anterior. Hay que revisar logs.

Ver `docs/admin/doc-railway-cron-sync.md` para la configuración del cron.

---

## Búsqueda en el catálogo

El endpoint existente ya soporta AtHome sin cambios:

```
GET /api/v1/cotizaciones/productos-catalogo/?fuente=athome&disponible=true&q=mica&page=1&page_size=30
```

Respuesta paginada estándar con `next`/`previous` para infinite scroll.

---

## Agregar una fuente futura

El sistema es extensible por diseño:

1. Crear subclase de `BaseFetcher` en `sync_productos_api.py`
2. Agregar `tipo_parser` nuevo a `FuenteApi.PARSER_CHOICES` y registrar en `PARSERS`
3. Generar migración de schema
4. Registrar la `FuenteApi` desde `/admin/` (sin tocar código)
