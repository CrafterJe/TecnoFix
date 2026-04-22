# Users — Renovación de tokens al cambiar contraseña

## Endpoint

```
POST /api/v1/users/{id}/change-password/
```

Requiere autenticación JWT. Solo el propio usuario o un `admin` pueden cambiar la contraseña.

## Comportamiento anterior

El endpoint devolvía únicamente:

```json
{ "detail": "Contraseña actualizada correctamente." }
```

Los tokens existentes seguían válidos hasta su expiración natural, sin renovarse.

## Comportamiento actual

Tras cambiar la contraseña exitosamente, el endpoint genera un par de tokens nuevos y los incluye en la respuesta:

```json
{
  "detail": "Contraseña actualizada correctamente.",
  "access": "<nuevo_access_token>",
  "refresh": "<nuevo_refresh_token>"
}
```

## Por qué

Cuando el usuario cambia su contraseña, los tokens anteriores quedan técnicamente vivos hasta expirar. Emitir tokens nuevos en el mismo response permite al frontend reemplazarlos de inmediato, cerrando esa ventana sin interrumpir la sesión.

## Request

```json
{
  "password_actual": "contraseñaActual123",
  "password_nuevo": "nuevaContraseña456"
}
```

## Responses

| Código | Descripción |
|---|---|
| `200` | Contraseña cambiada — incluye `access` y `refresh` nuevos |
| `400` | `password_actual` incorrecta o datos inválidos |
| `401` | No autenticado |
| `403` | El usuario autenticado no tiene permiso sobre este recurso |

### 200 OK

```json
{
  "detail": "Contraseña actualizada correctamente.",
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### 400 Bad Request

```json
{ "password_actual": "Contraseña incorrecta." }
```

## Integración en el frontend

Al recibir el `200`, reemplazar los tokens en storage antes de mostrar el toast de éxito:

```js
const res = await apiClient.post(`/users/${id}/change-password/`, payload)
localStorage.setItem('access', res.data.access)
localStorage.setItem('refresh', res.data.refresh)
// mostrar toast de éxito
```

El interceptor de 401 no se dispara porque los tokens nunca expiran durante el flujo — el usuario continúa la sesión sin interrupción.
