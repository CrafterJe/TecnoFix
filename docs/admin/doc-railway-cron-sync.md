# Sync automático de productos API en Railway (cron job)

## Qué hace

Una vez al día, sincroniza el catálogo de productos desde las APIs externas activas (FixOEM, SupraTec) hacia la tabla local `api_productos_catalogo`. Aplica **mark-and-sweep**: los productos que ya no aparecen en la API se marcan como `disponible=False` para que no salgan en cotizaciones, sin borrarlos (mantiene histórico).

Hora elegida: **04:00 AM Mexico City** (10:00 UTC) — bajo tráfico.

> AtHome **no se sincroniza en Railway** por ahora porque requiere los archivos JSON locales generados con `script.py`. Cuando se implemente scraping directo en producción (`bs4` en `requirements/production.txt` + fetcher modificado), AtHome entrará automáticamente al `--all-active`.

---

## Comando que ejecuta el cron

```bash
python manage.py sync_productos_api --all-active --no-interactive
```

- `--all-active`: itera todas las `FuenteApi` con `activo=True`.
- `--no-interactive`: salta el menú y corre directo (requerido para cron).

Si una fuente falla (timeout, error HTTP, etc.) el cron **NO marca su catálogo como agotado** — solo lo loggea y sigue con la siguiente fuente. Esto evita que un fallo temporal de la API tire todo el catálogo a `disponible=False`.

---

## Setup en Railway (dashboard, no se versiona en `railway.toml`)

Railway gestiona los cron jobs como **un servicio aparte** que se configura desde el dashboard, no desde el `railway.toml` del repo.

### Pasos

1. **Entrar al proyecto en Railway** → seleccionar el proyecto `TecnoFix`.
2. **+ New** → **Empty Service** (o **Deploy from GitHub repo** si quieres re-clonarlo).
3. **Settings** del nuevo servicio:
   - **Source repo**: mismo repo que el backend (`CrafterJe/TecnoFix`).
   - **Branch**: `main`.
   - **Build**: Dockerfile (el mismo).
   - **Service Type**: Cron Job.
   - **Cron Schedule**: `0 10 * * *` (10:00 UTC = 04:00 CDMX).
   - **Custom Start Command**:
     ```
     python manage.py sync_productos_api --all-active --no-interactive
     ```
4. **Variables**: copiar las mismas variables de entorno que el servicio principal (DB, `SECRET_KEY`, `DJANGO_SETTINGS_MODULE=config.settings.production`, etc.). Railway permite "Reference" para apuntar a las del servicio backend sin duplicar.
5. **Deploy**: el servicio queda en standby y arranca solo a la hora programada.

> Si Railway pide un puerto, déjalo vacío — los cron jobs no exponen HTTP.

### Verificar que corre

En el dashboard del nuevo servicio:

- **Deployments** → cada ejecución del cron aparece como un deployment con su log.
- **Metrics** → CPU/RAM al momento de la ejecución.

El log esperado se ve algo así:

```
============================================================
  Sincronizando: FixOEM (shopify_v1)
============================================================
  Página 1: +250 productos (acumulado: 250)
  Página 2: +250 productos (acumulado: 500)
  ...
  Parseando 1234 productos...
  Guardando en BD en lotes de 500...
  Lote 1: 500 registros guardados.
  ...

  FixOEM: 1234 guardados, 0 errores, 12 marcados como no disponibles (descontinuados).
============================================================
  Sincronizando: SupraTec (shopify_v1)
============================================================
  ...

  Total escrito en BD: 2500 productos.
  Total marcados como descontinuados: 18.
```

---

## Cómo desactivar temporalmente el sync

- **Pausar el servicio en Railway** desde Settings → "Pause Service". No se ejecutará en la próxima hora programada.
- O **marcar como inactiva** una `FuenteApi` desde `/admin/cotizaciones/fuenteapi/` (campo `activo=False`). El cron seguirá corriendo pero saltará esa fuente.

---

## Probar localmente antes de configurar Railway

```bash
# Equivalente a lo que correrá el cron, pero en local
python manage.py sync_productos_api --all-active --no-interactive

# Solo una fuente:
python manage.py sync_productos_api --fuente fixoem --no-interactive
```

Si esto funciona localmente apuntando a la BD de Railway (o a una BD de staging), entonces el cron también funcionará.

---

## Cron schedule reference

Railway usa la sintaxis estándar de cron en UTC. Algunos ejemplos:

| Quiero que corra | Cron UTC | Hora CDMX (horario estándar) |
|---|---|---|
| Diario 4:00 AM | `0 10 * * *` | 4:00 AM ← **elegido** |
| Diario 2:00 AM | `0 8 * * *` | 2:00 AM |
| Cada 6 horas | `0 */6 * * *` | varía |
| Lunes a viernes 6:00 AM | `0 12 * * 1-5` | 6:00 AM |

> Mexico City no observa horario de verano desde 2022, así que CDMX = UTC-6 todo el año.

---

## Troubleshooting

| Síntoma | Causa probable | Solución |
|---|---|---|
| Cron no ejecuta | Schedule en formato incorrecto o servicio pausado | Verificar en Settings que el cron expr es válido y el servicio está activo |
| `No hay fuentes API activas` | Todas las `FuenteApi` están con `activo=False` | Activar al menos una desde `/admin/` |
| `0 guardados, 0 marcados` repetido | API externa devolviendo HTTP errors o lista vacía | Revisar log del deployment, posiblemente la tienda cambió su endpoint |
| Catálogo entero como `disponible=False` después de un sync | Bug — no debería pasar porque el mark-and-sweep solo corre si `fetch_all()` retornó datos | Revisar log, abrir issue |
