# Core — Fix: Refresh token y storage en producción

## 1. Refresh token con vida útil de 30 días

### Configuración (`config/settings/base.py`)

```python
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=8),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
    'ROTATE_REFRESH_TOKENS': True,
    ...
}
```

### Comportamiento anterior

`REFRESH_TOKEN_LIFETIME` era de 1 día. Con `ROTATE_REFRESH_TOKENS=True` el contador se reinicia cada vez que el usuario abre la app, pero si la app no se abría por más de 24 horas el refresh token expiraba y no había forma de renovarlo sin login manual.

Los logs mostraron este patrón:

```
[INFO]    2026-04-22  → última actividad exitosa
[WARNING] 2026-04-26  → 401 Unauthorized: /api/v1/users/auth/refresh/  (4 días después)
[WARNING] 2026-05-07  → 401 Unauthorized: /api/v1/users/auth/refresh/  (15 días después)
```

### Comportamiento actual

El refresh token dura 30 días. Si el usuario abre la app al menos una vez al mes, la sesión se mantiene indefinidamente porque cada refresh rota el token y reinicia el contador.

### Flujo de tokens

```
Login
  └─ access token  (8 horas)
  └─ refresh token (30 días)

Cuando access expira:
  └─ frontend llama a /auth/refresh/ con el refresh token
  └─ backend devuelve nuevo access + nuevo refresh (contador reiniciado)

Si el refresh token expira sin haberse usado:
  └─ 401 en /auth/refresh/ → el frontend debe redirigir a login
```

---

## 2. Storage default en producción

### Configuración (`config/settings/production.py`)

```python
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
```

### Problema

Django 4.2+ requiere que `STORAGES` defina explícitamente ambas claves (`default` y `staticfiles`) cuando se sobreescribe la configuración. En producción solo se había definido `staticfiles` para whitenoise, omitiendo `default`. Cualquier operación de subida de archivos (`FileField`, `ImageField`) fallaba con:

```
InvalidStorageError: Could not find config for 'default' in settings.STORAGES
```

El error se manifestaba al subir evidencias (`POST /api/v1/ordenes/evidencias/`).

### Solución

Se agrega `"default"` con `FileSystemStorage`, que es el backend estándar de Django para guardar archivos en disco. No cambia el comportamiento de los archivos de media — solo hace explícita una configuración que antes se asumía por defecto.
