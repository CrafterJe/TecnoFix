# Cotizaciones — Integración AtHome (parser local JSON)

## Qué es

AtHome (`athomemx.mx`) es una tercera fuente de productos incorporada al catálogo de APIs del módulo de cotizaciones. A diferencia de FixOEM y SupraTecMX (que usan la API pública de Shopify), AtHome provee su catálogo como archivos JSON estáticos locales, por lo que requirió un parser propio.

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

Actualmente AtHome **no se sincroniza automáticamente en Railway** porque el contenedor de producción no tiene los JSON locales (están en `.gitignore`). Las opciones futuras:

1. **Mantener manual**: solo se sincroniza cuando se corre el scraper localmente y se ejecuta el sync apuntando a la BD de producción. Útil mientras el catálogo de AtHome cambie poco.
2. **Scraping directo en Railway** (estrategia elegida para el futuro): agregar `beautifulsoup4` a `requirements/production.txt` y modificar `AtHomeV1Fetcher` para hacer scraping en vivo (similar a `script.py` pero llamado desde el comando). Entonces AtHome entra automáticamente al cron `--all-active`.

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
