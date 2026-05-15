# Pull Request: Fix refresh token expirado y storage en producción

## Descripción

Dos fixes de configuración detectados via logs de producción: el refresh token expiraba después de 1 día dejando a usuarios sin sesión si no abrían la app a diario, y la subida de evidencias fallaba en producción por un `STORAGES` incompleto en Django.

---

## Problema 1 — Refresh token de 1 día

`REFRESH_TOKEN_LIFETIME` estaba en `timedelta(days=1)`. Con `ROTATE_REFRESH_TOKENS=True`, el contador se reinicia cada vez que el usuario abre la app, pero si no la abre por más de 1 día el refresh token expira y no hay forma de renovarlo sin hacer login manual.

Los logs mostraron el patrón exacto:
- Última actividad exitosa: 22 abril
- Primer `401 Unauthorized: /api/v1/users/auth/refresh/`: 26 abril (4 días después)
- Segundo intento fallido: 7 mayo (15 días después)

## Problema 2 — `InvalidStorageError` al subir evidencias

En `production.py`, al definir `STORAGES` solo se incluía `staticfiles` (para whitenoise) pero se omitía `default`. Django 4.2+ requiere ambas claves cuando se sobreescribe `STORAGES`. Sin `default`, cualquier `FileField` o `ImageField` lanzaba `InvalidStorageError: Could not find config for 'default' in settings.STORAGES` al intentar guardar una evidencia.

---

## Solución

**Fix 1** — `config/settings/base.py`: `REFRESH_TOKEN_LIFETIME` de 1 día a 30 días. Usuarios que no abran la app por hasta un mes seguirán con sesión activa. Cada vez que la abran, el token rota y el contador se reinicia.

**Fix 2** — `config/settings/production.py`: Se agrega el backend `default` a `STORAGES` usando `FileSystemStorage` (comportamiento estándar de Django), dejando `staticfiles` con whitenoise sin cambios.

---

## Archivos modificados

- `config/settings/base.py` — `REFRESH_TOKEN_LIFETIME`: `days=1` → `days=30`
- `config/settings/production.py` — `STORAGES` con clave `"default"` agregada

---

## Cómo probar

```bash
# Fix 1: Verificar que el refresh token dura 30 días
# 1. Hacer login
POST /api/v1/users/auth/login/
{ "email": "<email_usuario>", "password": "<password>" }

# 2. Verificar que el token tiene exp a 30 días desde ahora
# Decodificar el refresh token en jwt.io → campo "exp"

# Fix 2: Subir una evidencia en producción
POST /api/v1/ordenes/evidencias/
Authorization: Bearer <access_token>
Content-Type: multipart/form-data
{ "orden": 1, "imagen": <archivo>, "descripcion": "Test" }
# Debe devolver 201, no 500
```

---

## Notas

- Requiere redeploy en Railway para que los cambios de producción entren en efecto.
- Usuarios con refresh token ya expirado deberán hacer login una vez más.
