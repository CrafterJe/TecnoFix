# Auditoría — Filtros de acción y entidad

## Endpoint

```
GET /api/v1/auditoria/
```

Requiere autenticación JWT con rol `admin`.

## Filtros disponibles

### Por acción (`?action=`)

| Valor | Descripción |
|---|---|
| `CREATE` | Registros creados |
| `UPDATE` | Registros actualizados |
| `DELETE` | Registros eliminados |
| `ASSIGN` | Asignaciones |
| `STATUS_CHANGE` | Cambios de estado |
| `LOGIN` | Inicios de sesión |

### Por entidad (`?entity=`)

Acepta el nombre del modelo. No distingue mayúsculas/minúsculas.

| Valor | Descripción |
|---|---|
| `Orden` | Órdenes de servicio |
| `Cliente` | Clientes |
| `Dispositivo` | Dispositivos |
| `Refaccion` | Refacciones |
| `User` | Usuarios |

## Ejemplos

```
# Todos los logins
GET /api/v1/auditoria/?action=LOGIN

# Todas las órdenes creadas
GET /api/v1/auditoria/?action=CREATE&entity=Orden

# Todos los cambios sobre clientes
GET /api/v1/auditoria/?entity=Cliente

# Actualizaciones de refacciones
GET /api/v1/auditoria/?action=UPDATE&entity=Refaccion
```

## Otros parámetros

| Parámetro | Descripción |
|---|---|
| `search=` | Busca en `entity`, `action`, `user__nombre`, `user__email` |
| `ordering=` | Ordena por `created_at`, `action`, `entity` (prefijo `-` para descendente) |
| `page=` | Paginación estándar (20 por página) |

## Respuesta

```json
{
  "count": 100,
  "total_pages": 5,
  "current_page": 1,
  "next": "...",
  "previous": null,
  "results": [
    {
      "id": 1,
      "user": { "id": 1, "nombre": "Admin", "email": "admin@tecnofix.com" },
      "action": "CREATE",
      "entity": "Orden",
      "entity_id": 42,
      "old_value": {},
      "new_value": { "estado": "recibida" },
      "ip_address": "192.168.1.1",
      "created_at": "2026-04-22T18:44:31Z"
    }
  ]
}
```
