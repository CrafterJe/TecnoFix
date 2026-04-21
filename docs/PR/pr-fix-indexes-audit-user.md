# Pull Request: Índices de BD, fix auditoría con JWT y campo rol opcional

## Descripción
Se corrigen dos bugs funcionales (usuario nulo en auditoría y campo `rol` requerido en creación) y se añaden índices de base de datos en todos los modelos de negocio para mejorar el rendimiento en filtros y búsquedas frecuentes.

---

## Cambios incluidos

### 1. Fix: usuario siempre `null` en AuditLog (`core/middleware.py`)
El `AuditMiddleware` capturaba `request.user` al inicio del request, antes de que DRF ejecutara su autenticación JWT. En ese momento el usuario era `AnonymousUser`, por lo que todos los registros de auditoría quedaban con `user = null`.

**Solución:** el middleware ahora guarda el objeto `request` completo en el thread-local. La función `get_current_user()` lo lee de forma lazy cuando los signals de auditoría la invocan durante el `save()` — momento en que DRF ya procesó el JWT y el usuario está autenticado.

### 2. Fix: campo `rol` requerido en creación de usuario (`apps/users/serializers.py`)
`UsuarioCreateSerializer` no declaraba `rol` explícitamente, por lo que DRF lo tomaba como campo requerido aunque el modelo tiene `default='recepcion'`. Si el cliente no lo enviaba, la petición fallaba con `400`.

**Solución:** se declara `rol` como `ChoiceField` con `required=False` y `default='recepcion'` en el serializer.

### 3. Índices de base de datos en todos los modelos
Se añaden índices en los campos más consultados de cada app. Los campos FK y `unique=True` ya son indexados automáticamente por Django; los nuevos índices cubren:

| Modelo | Campos indexados |
|---|---|
| `Usuario` | `rol`, `activo`, `rol + activo` |
| `Cliente` | `nombre`, `telefono`, `email` |
| `Dispositivo` | `tipo`, `marca` |
| `Orden` | `estado`, `created_at`, `estado + created_at` |
| `Evidencia` | `tipo` |
| `Refaccion` | `nombre`, `categoria`, `stock` |
| `RefaccionCompatible` | `marca` |
| `AuditLog` | `entity + entity_id`, `action`, `created_at` |

Se generaron las migraciones correspondientes en todas las apps afectadas.

---

## Archivos modificados
- `core/middleware.py` — resolución lazy del usuario en thread-local
- `apps/users/serializers.py` — `rol` opcional con default en `UsuarioCreateSerializer`
- `apps/users/models.py` + migración
- `apps/clientes/models.py` + migración
- `apps/ordenes/models.py` + migración
- `apps/inventario/models.py` + migración
- `apps/auditoria/models.py` + migración

## Cómo probar

```bash
# Aplicar migraciones
python manage.py migrate

# Verificar auditoría: crear o actualizar cualquier registro autenticado con JWT
# y confirmar que AuditLog.user ya no es null

# Verificar creación de usuario sin campo rol
POST /api/v1/users/
{
  "nombre": "Test",
  "email": "test@tecnofix.com",
  "password": "Password123!",
  "password_confirm": "Password123!"
}
# Debe retornar 201 con rol = "recepcion"
```
