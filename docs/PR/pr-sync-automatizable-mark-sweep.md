# Pull Request: Sync de productos API automatizable + mark-and-sweep

## Descripción

Habilita la **sincronización diaria automática** del catálogo de productos externos (FixOEM, SupraTec) en Railway sin requerir intervención manual, e introduce **mark-and-sweep** para que los productos descontinuados por las fuentes queden marcados como `disponible=False` en lugar de seguir saliendo en cotizaciones.

Tres cambios en un solo PR:

1. **Flags no interactivos** en `sync_productos_api` (`--fuente`, `--all-active`, `--no-interactive`) — el menú interactivo sigue siendo el default, los flags solo lo saltan cuando se invoca desde cron.
2. **Mark-and-sweep** post-upsert por fuente, con safety net si la API falla.
3. **`.gitignore`** agrega `data/` para que la carpeta de JSONs de AtHome no se suba al repo.
4. **Documentación** del setup del cron en Railway y actualización del flujo de AtHome para usar `data/athome` (ruta relativa, portable entre equipos).

---

## Cambios incluidos

### Código

| Archivo | Cambio |
|---|---|
| `apps/cotizaciones/management/commands/sync_productos_api.py` | Agrega `add_arguments()` con `--fuente`, `--all-active`, `--no-interactive`. `handle()` delega a `_handle_no_interactive()` si se pasaron flags, sino mantiene el menú. `_sincronizar()` ahora captura `sync_started_at`, envuelve `fetch_all()` en try/except (skip mark-and-sweep si falla), y al final llama a `_marcar_no_vistos()` que hace un `update(disponible=False)` sobre los productos cuyo `synced_at < sync_started_at` y siguen `disponible=True`. |
| `.gitignore` | Agrega `data/` (carpeta para datos locales como los JSONs de AtHome). |

### Documentación

| Archivo | Tipo | Contenido |
|---|---|---|
| `docs/admin/doc-railway-cron-sync.md` | Nuevo | Pasos para crear un servicio "Cron Job" en Railway (no se versiona en `railway.toml` — Railway lo gestiona desde el dashboard). Cron schedule, comando, troubleshooting. |
| `docs/cotizaciones/doc-athome-integration.md` | Update | Nuevo flujo con `data/athome/` (gitignored), instrucciones para regenerar los JSONs con `script.py`, ejemplos con flags no interactivos, sección sobre mark-and-sweep y plan para AtHome en producción. |

---

## Flags nuevos

```bash
# Modo interactivo (default, sin flags) — sigue funcionando idéntico que antes
python manage.py sync_productos_api

# Modo cron — todas las fuentes activas
python manage.py sync_productos_api --all-active --no-interactive

# Modo cron — una fuente específica
python manage.py sync_productos_api --fuente fixoem --no-interactive
```

`--fuente` y `--all-active` son mutuamente excluyentes. `--no-interactive` solo, sin ninguno de los otros dos, devuelve error.

---

## Mark-and-sweep — comportamiento

Para cada fuente sincronizada:

1. Captura `sync_started_at = timezone.now()` ANTES del `fetch_all()`.
2. Ejecuta `fetch_all()`. Si lanza excepción o retorna vacío → **se salta mark-and-sweep** para esa fuente y continúa con la siguiente (no se contamina BD por fallos temporales).
3. Hace `bulk_create(update_conflicts=True)`. Los productos vistos quedan con `synced_at = ahora` (donde `ahora >= sync_started_at`).
4. Ejecuta:
   ```python
   ApiProductoCatalogo.objects.filter(
       fuente=fuente,
       synced_at__lt=sync_started_at,
       disponible=True,
   ).update(disponible=False)
   ```
5. Imprime cuántos productos quedaron marcados como descontinuados.

| Estado anterior | Aparece en API hoy? | Estado después |
|---|---|---|
| `disponible=True` | ✅ Sí | `disponible=True` (actualizado por upsert si cambió) |
| `disponible=True` | ❌ No | **`disponible=False`** (mark-and-sweep) |
| `disponible=False` | ✅ Sí | `disponible=True` (actualizado por upsert) |
| `disponible=False` | ❌ No | `disponible=False` (no se toca) |

**No se borran registros**. Productos descontinuados quedan en BD con `disponible=False` para histórico. El front filtra por `disponible=True` al mostrar resultados en cotización.

---

## AtHome — cambio de flujo local

El registro `FuenteApi` de AtHome **debe migrarse** de la ruta absoluta del dispositivo donde se desarrolló:

```
ANTES:  base_url = C:\Users\CrafterJe\Desktop\Importante\Projects\TecnoFix\AtHome  (absoluta, no portable)
DESPUÉS: base_url = data/athome  (relativa al BASE_DIR, portable entre equipos)
```

Pasos manuales (no van al commit, son operativos):

```bash
# Instalar dependencia del scraper (solo local, no entra a requirements/)
pip install beautifulsoup4

# Generar JSONs en data/athome/
mkdir -p data/athome
cd data/athome
python ../../docs/api-samples/athome/script.py
cd ../..

# Actualizar FuenteApi.base_url desde /admin/cotizaciones/fuenteapi/
# (o vía shell):
python manage.py shell -c "from apps.cotizaciones.models import FuenteApi; FuenteApi.objects.filter(slug='athome').update(base_url='data/athome')"

# Probar sync
python manage.py sync_productos_api --fuente athome --no-interactive
```

---

## Railway cron — setup post-merge

El cron job no se versiona en el repo (Railway lo gestiona desde el dashboard). Después de mergear este PR:

1. En Railway dashboard: crear un nuevo servicio tipo **Cron Job** desde el mismo repo/branch (`main`).
2. **Schedule**: `0 10 * * *` (10:00 UTC = 04:00 AM CDMX).
3. **Start Command**: `python manage.py sync_productos_api --all-active --no-interactive`
4. Copiar las mismas variables de entorno que el servicio backend principal.

Pasos detallados en `docs/admin/doc-railway-cron-sync.md`.

---

## AtHome en Railway

Por ahora **AtHome no se sincroniza automáticamente en Railway** porque la imagen de producción no tiene los JSONs locales (`data/` está gitignored).

Estrategia futura: agregar `beautifulsoup4` a `requirements/production.txt` y modificar `AtHomeV1Fetcher` para hacer scraping HTML en vivo (similar a `docs/api-samples/athome/script.py`). Cuando eso esté listo, AtHome entrará automáticamente al cron `--all-active` sin más cambios.

---

## Compatibilidad

- **El menú interactivo no cambia**: si corres `python manage.py sync_productos_api` sin flags, ves el mismo menú numerado de siempre. La convención de "comandos interactivos" se respeta.
- **Sin migraciones de BD**: solo cambia el comando, no hay cambios de schema.
- **Sin dependencias nuevas en `requirements/`**: `bs4` queda fuera del backend (solo lo usa el scraper standalone, manual).

---

## Pruebas manuales sugeridas

```bash
# 1. Menú interactivo sigue funcionando
python manage.py sync_productos_api
# Verificar que sale el menú numerado normal

# 2. Flag --fuente con slug inválido devuelve error claro
python manage.py sync_productos_api --fuente noexiste --no-interactive
# Esperado: "No existe una FuenteApi activa con slug='noexiste'."

# 3. --fuente y --all-active juntos son rechazados
python manage.py sync_productos_api --fuente fixoem --all-active --no-interactive
# Esperado: "--fuente y --all-active son mutuamente excluyentes."

# 4. --no-interactive solo (sin --fuente/--all-active) rechaza
python manage.py sync_productos_api --no-interactive
# Esperado: "Modo no interactivo requiere --fuente <slug> o --all-active."

# 5. Sync real (puede tomar varios minutos)
python manage.py sync_productos_api --fuente fixoem --no-interactive
# Verificar al final: "FixOEM: NN guardados, N errores, NN marcados como no disponibles..."
```
