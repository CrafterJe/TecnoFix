# Dev local — Optimización de rendimiento

## Problema

El backend local con `python manage.py runserver` respondía en 75–210ms por request, mientras que en Railway la misma app responde en < 50ms. La causa no era el motor de BD (ambos usan MySQL) sino overhead de herramientas de desarrollo siempre activas.

---

## Causas identificadas

| # | Causa | Overhead estimado |
|---|---|---|
| 1 | `DebugToolbarMiddleware` activo en cada request | 50–150ms |
| 2 | `CONN_MAX_AGE=0` (default) — nueva conexión TCP a MySQL por request | 15–30ms |
| 3 | `CORS_PREFLIGHT_MAX_AGE` no configurado — OPTIONS repetido en el browser | N requests adicionales |
| 4 | `DEBUG=True` — Django guarda todas las queries en `connection.queries` | overhead menor |

---

## Fixes aplicados

### 1. `debug_toolbar` detrás de env var

**Archivo**: `config/settings/development.py`

```python
if os.getenv('ENABLE_DEBUG_TOOLBAR') == '1':
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
```

**Antes**: el toolbar cargaba en cada request aunque no estuvieras usándolo.

**Después**: no carga por default. Para activarlo puntualmente:

```powershell
# PowerShell
$env:ENABLE_DEBUG_TOOLBAR="1"; python manage.py runserver
```

```bash
# Bash / Git Bash
ENABLE_DEBUG_TOOLBAR=1 python manage.py runserver
```

---

### 2. `CONN_MAX_AGE=60` en development

**Archivo**: `config/settings/development.py`

```python
DATABASES['default']['CONN_MAX_AGE'] = 60
```

Django reutiliza la conexión MySQL durante 60 segundos en lugar de abrir y cerrar una conexión TCP por cada request. No se aplica en `production.py` para no interferir con el manejo de conexiones de Railway.

---

### 3. `CORS_PREFLIGHT_MAX_AGE=86400` en base

**Archivo**: `config/settings/base.py`

```python
CORS_PREFLIGHT_MAX_AGE = 86400
```

El browser cachea la respuesta OPTIONS (preflight CORS) durante 24 horas. Sin esto, cada request no-simple del front dispara un OPTIONS adicional antes del request real. Aplica a dev y producción por igual (es seguro en ambos).

---

## Resultado esperado

| Entorno | Antes | Después |
|---|---|---|
| Local (runserver) | 75–210ms | ~20–50ms |
| Railway | < 50ms | < 50ms (sin cambios) |

---

## Runserver vs Gunicorn en local

`runserver` es single-threaded y sin soporte WSGI productivo, pero para desarrollo es suficiente una vez quitado el overhead de `debug_toolbar` y `CONN_MAX_AGE`.

Si se necesita probar comportamiento multi-worker en local:

```bash
# Requiere gunicorn instalado (está en requirements/production.txt)
pip install gunicorn
gunicorn config.wsgi --workers 2 --reload --bind 0.0.0.0:8000
```

> Nota: en Windows, `gunicorn` no está soportado nativamente. Usar WSL2 o Docker para esta prueba.
