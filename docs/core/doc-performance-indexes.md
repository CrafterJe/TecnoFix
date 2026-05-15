# Índices de rendimiento — Auditoría y optimización de BD

## Contexto

Se realizó una auditoría completa de índices sobre todos los modelos y endpoints GET del proyecto. Se analizaron patrones de filtrado reales en los `ViewSet` para identificar queries sin cobertura de índice. Solo se crearon índices compuestos donde existe un query concreto que los aprovecha; los índices "por si acaso" se descartaron.

Fecha: 2026-05-15

---

## Índices existentes antes de esta auditoría (resumen)

| App | Modelo | Índices previos |
|---|---|---|
| auditoria | AuditLog | `(entity, entity_id)`, `action`, `created_at` |
| clientes | Cliente | `nombre`, `telefono`, `email` |
| clientes | Dispositivo | `tipo`, `marca` |
| cotizaciones | ApiProductoCatalogo | `fuente`, `disponible`, `titulo` + UniqueConstraint `(fuente, producto_id_externo)` |
| cotizaciones | Cotizacion | `estado`, `created_at`, `numero_cotizacion` |
| cotizaciones | TipoReparacion | `activo` |
| inventario | Refaccion | `nombre`, `categoria`, `stock` |
| ordenes | Orden | `estado`, `created_at`, `(estado, created_at)` |
| ordenes | Evidencia | `tipo` |
| users | Usuario | `rol`, `activo`, `(rol, activo)` |

---

## Índices agregados

### 1. `auditoria` — AuditLog

**Migración**: `apps/auditoria/migrations/0004_add_performance_indexes.py`

```python
models.Index(fields=['action', 'entity'], name='idx_auditlog_action_entity')
```

**Por qué**: El endpoint `GET /api/v1/auditoria/?action=X&entity=Y` filtra por ambos campos en AND. Los índices individuales de `action` y `(entity, entity_id)` existentes no cubren esta combinación eficientemente.

---

### 2. `ordenes` — Orden

**Migración**: `apps/ordenes/migrations/0004_add_performance_indexes.py`

```python
models.Index(fields=['estado', 'assigned_to'], name='idx_ordenes_estado_assigned')
```

**Por qué**: El endpoint `GET /api/v1/ordenes/?estado=X&assigned_to=Y` ("tareas de un técnico en estado X") es el filtro más común en producción. El compuesto existente `(estado, created_at)` no cubre este caso. `assigned_to` es FK (índice implícito individual), pero el compuesto con `estado` permite index lookup sin escanear filas descartadas.

---

### 3. `cotizaciones` — ApiProductoCatalogo

**Migración**: `apps/cotizaciones/migrations/0008_add_performance_indexes.py`

```python
models.Index(fields=['fuente', 'disponible'], name='idx_apiproducto_fuente_disp')
```

**Por qué**: La búsqueda de productos combina siempre `fuente` + `disponible` antes de aplicar el `LIKE '%q%'` en título. Con ~17,000 productos en catálogo, el índice compuesto reduce el scan set a la fracción disponible de una sola fuente antes de la búsqueda textual.

> Nota: `titulo__icontains` genera `LIKE '%term%'` y no puede usar el índice B-tree en `titulo` (ningún motor lo hace con leading wildcard). El índice `idx_apiproducto_titulo` existente solo acelera el `ORDER BY titulo` del queryset base.

---

### 4. `inventario` — Refaccion

**Migración**: `apps/inventario/migrations/0003_add_performance_indexes.py`

```python
models.Index(fields=['stock', 'stock_minimo'], name='idx_refacciones_stock_min')
```

**Por qué**: El endpoint `GET /api/v1/inventario/bajo-stock/` filtra `stock__lte=F('stock_minimo')`. La query compara dos columnas de la misma fila; el índice compuesto permite que MySQL evalúe la condición usando el índice en lugar de scan completo.

---

## Qué se descartó y por qué

| Sugerencia descartada | Razón |
|---|---|
| Índices en FKs simples (`cliente_id`, `orden_id`, etc.) | Django crea `db_index=True` automáticamente en todos los `ForeignKey` |
| `idx_usuarios_email` | `email` tiene `unique=True` → índice implícito |
| `idx_formula_tipo_subcategoria` | Ya existe vía `UniqueConstraint(['tipo_reparacion', 'subcategoria'])` |
| Índices en campos de bajo volumen (`FuenteApi.activo`, `CategoriaDispositivo.activo`) | Tablas con < 20 registros; el full scan es más rápido que usar el índice |

---

## Cómo verificar en BD

```bash
python manage.py dbshell
```

```sql
-- MySQL: listar índices de una tabla
SHOW INDEX FROM api_productos_catalogo;
SHOW INDEX FROM ordenes;
SHOW INDEX FROM audit_log;
SHOW INDEX FROM refacciones;
```
