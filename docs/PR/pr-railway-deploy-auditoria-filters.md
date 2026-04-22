# Pull Request: Deploy en Railway y filtros de auditoría

## Descripción
Se configura el deploy del backend en Railway usando Docker, se resuelven los problemas de compatibilidad con MySQL 8 y Nixpacks, y se implementan los filtros de entidad y acción en el endpoint de auditoría.

---

## Cambios incluidos

### 1. Configuración de deploy en Railway (`Dockerfile`, `railway.toml`)
El proyecto no tenía ninguna configuración de deploy. Se intentó primero con Nixpacks pero presentó problemas con el binario de Python y la compilación de `mysqlclient`. Se optó por un `Dockerfile` directo con `python:3.11-slim`.

- `Dockerfile`: instala dependencias del sistema (Cairo/SVG), instala requirements de producción, ejecuta `collectstatic` en build y corre `migrate + gunicorn` al arrancar.
- `railway.toml`: especifica builder `dockerfile` y políticas de restart.
- `nixpacks.toml`: conservado con los nixpkgs de Cairo/SVG para referencia futura.

### 2. Reemplazo de `mysqlclient` por `PyMySQL` (`requirements/base.txt`)
`mysqlclient` requiere compilar código C y headers de MySQL, lo que falló en el entorno de build de Railway. `PyMySQL` es puro Python y funciona sin dependencias nativas.

Se agrega el shim de compatibilidad en `config/__init__.py`:
```python
import pymysql
pymysql.install_as_MySQLdb()
```

Se agrega `cryptography==42.0.8` porque Railway usa MySQL 8 con `caching_sha2_password` y PyMySQL lo requiere para cifrar la autenticación.

### 3. Whitenoise para archivos estáticos (`requirements/production.txt`, `config/settings/production.py`)
Sin Whitenoise, gunicorn no sirve archivos estáticos. Se agrega al middleware justo después de `SecurityMiddleware` (posición requerida) y se configura `CompressedManifestStaticFilesStorage` para compresión y cache-busting automático.

### 4. Filtros de acción y entidad en auditoría (`apps/auditoria/views.py`)
`filterset_fields` requiere `django-filter` que no está instalado. Se reemplaza por `get_queryset()` con filtrado manual vía query params.

**Uso:**
```
GET /api/v1/auditoria/?action=CREATE
GET /api/v1/auditoria/?entity=Orden
GET /api/v1/auditoria/?action=UPDATE&entity=Cliente
```

---

## Archivos modificados
- `Dockerfile` — imagen de producción
- `railway.toml` — configuración de deploy
- `nixpacks.toml` — nixpkgs para Cairo/SVG
- `requirements.txt` — punto de entrada para Railway (apunta a production.txt)
- `requirements/base.txt` — PyMySQL + cryptography + cairosvg
- `requirements/production.txt` — whitenoise
- `config/__init__.py` — shim PyMySQL
- `config/settings/production.py` — whitenoise en middleware y storage
- `.python-version` — versión 3.11 para tooling
- `.gitignore` — ignorar `.env.railway`
- `apps/auditoria/views.py` — filtros manuales por action y entity

## Variables de entorno requeridas en Railway
| Variable | Valor |
|---|---|
| `DJANGO_SETTINGS_MODULE` | `config.settings.production` |
| `SECRET_KEY` | (generado) |
| `ALLOWED_HOSTS` | `tecnofix-production.up.railway.app` |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:1420,tauri://localhost,https://tauri.localhost` |
| `DB_NAME` | `${{MySQL.MYSQL_DATABASE}}` |
| `DB_USER` | `${{MySQL.MYSQLUSER}}` |
| `DB_PASSWORD` | `${{MySQL.MYSQLPASSWORD}}` |
| `DB_HOST` | `${{MySQL.MYSQLHOST}}` |
| `DB_PORT` | `${{MySQL.MYSQLPORT}}` |

## Cómo probar

```bash
# Verificar que el servidor responde
curl https://tecnofix-production.up.railway.app/api/v1/docs/

# Filtros de auditoría (requiere token admin)
GET /api/v1/auditoria/?action=LOGIN
GET /api/v1/auditoria/?entity=Orden
```
