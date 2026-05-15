# Pull Request: AtHome API + Índices de rendimiento + Dev performance

## Descripción

PR que agrupa tres mejoras independientes pero relacionadas con el rendimiento y extensibilidad del módulo de cotizaciones:

1. **Integración de AtHome** como tercera fuente de productos (archivos JSON locales, ~10,000 productos)
2. **Índices compuestos** en 4 apps para acelerar los endpoints con filtros combinados más frecuentes
3. **Fixes de rendimiento en dev local** que recortaron el tiempo de respuesta de ~150ms a ~30ms

---

## 1. Integración AtHome (`apps/cotizaciones`)

### Cambios de schema

| Archivo | Cambio |
|---|---|
| `apps/cotizaciones/models.py` | `FuenteApi.PARSER_CHOICES` agrega `athome_v1` |
| `apps/cotizaciones/models.py` | `FuenteApi.base_url`: `URLField` → `CharField(500)` |
| `apps/cotizaciones/models.py` | `ApiProductoCatalogo.producto_id_externo`: `BigIntegerField` → `CharField(100)` |
| `apps/cotizaciones/models.py` | `ApiProductoCatalogo.url_producto`: nuevo `URLField(blank=True)` |
| `apps/cotizaciones/migrations/0006_athome_schema.py` | Migración de schema (manual) |
| `apps/cotizaciones/migrations/0007_athome_fuente_data.py` | Data migration — inserta `FuenteApi` de AtHome |

### Nuevo parser

| Archivo | Cambio |
|---|---|
| `apps/cotizaciones/management/commands/sync_productos_api.py` | Nueva clase `AtHomeV1Fetcher` |
| `apps/cotizaciones/management/commands/sync_productos_api.py` | `ShopifyV1Fetcher.parse()` agrega `url_producto=''` |
| `apps/cotizaciones/management/commands/sync_productos_api.py` | `_guardar_productos`: `url_producto` en `update_fields` |
| `apps/cotizaciones/management/commands/sync_productos_api.py` | `PARSERS` registra `athome_v1` |

### Serializer

| Archivo | Cambio |
|---|---|
| `apps/cotizaciones/serializers.py` | `ApiProductoCatalogoSerializer` expone `url_producto` |

### Notas para el front

- `producto_id_externo` **cambió de número a string** en el JSON. Revisar comparaciones con `===` o `parseInt`.
- `url_producto` es campo nuevo: viene con URL completa en productos AtHome, vacío en Shopify. Renderizar link solo si está presente.

---

## 2. Índices de rendimiento

### Índices agregados

| App | Modelo | Índice | Migración |
|---|---|---|---|
| `auditoria` | AuditLog | `(action, entity)` | `0004_add_performance_indexes.py` |
| `ordenes` | Orden | `(estado, assigned_to)` | `0004_add_performance_indexes.py` |
| `cotizaciones` | ApiProductoCatalogo | `(fuente, disponible)` | `0008_add_performance_indexes.py` |
| `inventario` | Refaccion | `(stock, stock_minimo)` | `0003_add_performance_indexes.py` |

### Por qué estos y no otros

- Los FK simples ya tienen `db_index=True` automático en Django — no se duplicaron.
- Campos con `unique=True` ya tienen índice implícito.
- Tablas con < 20 registros (FuenteApi, CategoriaDispositivo) no necesitan índice: full scan es más rápido.
- `titulo__icontains` usa `LIKE '%term%'` — ningún B-tree lo acelera. El índice en `titulo` solo sirve para `ORDER BY`.

---

## 3. Dev performance

| Archivo | Cambio | Impacto |
|---|---|---|
| `config/settings/development.py` | `debug_toolbar` detrás de `ENABLE_DEBUG_TOOLBAR=1` env var | −50 a −150ms por request |
| `config/settings/development.py` | `CONN_MAX_AGE=60` solo en dev | −15 a −30ms por request |
| `config/settings/base.py` | `CORS_PREFLIGHT_MAX_AGE=86400` | Elimina OPTIONS repetidos del browser |

---

## Migraciones incluidas (resumen)

```
cotizaciones:
  0006_athome_schema         — schema: base_url CharField, producto_id_externo CharField, url_producto nuevo campo
  0007_athome_fuente_data    — data: inserta FuenteApi de AtHome
  0008_add_performance_indexes — índice compuesto (fuente, disponible) en ApiProductoCatalogo

auditoria:
  0004_add_performance_indexes — índice compuesto (action, entity) en AuditLog

ordenes:
  0004_add_performance_indexes — índice compuesto (estado, assigned_to) en Orden

inventario:
  0003_add_performance_indexes — índice compuesto (stock, stock_minimo) en Refaccion
```

---

## Cómo probar

### AtHome

```bash
# 1. Aplicar migraciones
python manage.py migrate

# 2. Sincronizar catálogo AtHome
python manage.py sync_productos_api
# Elegir: "Sincronizar solo AtHome"

# 3. Verificar productos en catálogo
python manage.py shell -c "
from apps.cotizaciones.models import ApiProductoCatalogo, FuenteApi
f = FuenteApi.objects.get(slug='athome')
print(ApiProductoCatalogo.objects.filter(fuente=f).count(), 'productos')
"

# 4. Probar endpoint
GET /api/v1/cotizaciones/productos-catalogo/?fuente=athome&disponible=true&q=mica&page_size=30
```

### Índices

```bash
python manage.py dbshell
```
```sql
SHOW INDEX FROM api_productos_catalogo;
SHOW INDEX FROM ordenes;
SHOW INDEX FROM audit_log;
SHOW INDEX FROM refacciones;
```

### Dev performance

```bash
# Sin toolbar (default — rápido)
python manage.py runserver

# Con toolbar (cuando lo necesites)
$env:ENABLE_DEBUG_TOOLBAR="1"; python manage.py runserver   # PowerShell
ENABLE_DEBUG_TOOLBAR=1 python manage.py runserver            # Bash
```

---

## Docs relacionados

- [`docs/cotizaciones/doc-athome-integration.md`](../cotizaciones/doc-athome-integration.md) — Detalle técnico del parser AtHome
- [`docs/core/doc-performance-indexes.md`](../core/doc-performance-indexes.md) — Auditoría de índices completa
- [`docs/admin/doc-dev-performance.md`](../admin/doc-dev-performance.md) — Fixes de rendimiento en dev local
