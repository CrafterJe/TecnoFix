# Deploy en Railway

## Arquitectura

El backend corre en Railway usando Docker (`python:3.11-slim`). La base de datos es un plugin MySQL 8 dentro del mismo proyecto de Railway.

## Archivos de configuración

### `Dockerfile`
- Instala dependencias del sistema: Cairo, Pango, GDK-Pixbuf (para cairosvg)
- Instala `requirements/production.txt`
- Ejecuta `collectstatic` en tiempo de build
- Al arrancar: corre `migrate` y luego `gunicorn`

### `railway.toml`
- Builder: `dockerfile`
- Restart policy: `on_failure`, máximo 10 reintentos

### `nixpacks.toml`
- Conservado con los nixpkgs de Cairo/SVG para cuando se active la feature de generación SVG

## Variables de entorno en Railway

| Variable | Valor |
|---|---|
| `DJANGO_SETTINGS_MODULE` | `config.settings.production` |
| `SECRET_KEY` | (generado con `get_random_secret_key()`) |
| `ALLOWED_HOSTS` | `tecnofix-production.up.railway.app` |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:1420,tauri://localhost,https://tauri.localhost` |
| `DB_NAME` | `${{MySQL.MYSQL_DATABASE}}` |
| `DB_USER` | `${{MySQL.MYSQLUSER}}` |
| `DB_PASSWORD` | `${{MySQL.MYSQLPASSWORD}}` |
| `DB_HOST` | `${{MySQL.MYSQLHOST}}` |
| `DB_PORT` | `${{MySQL.MYSQLPORT}}` |

Las variables `DB_*` usan referencias al plugin MySQL — Railway las resuelve automáticamente cuando los servicios están linkeados.

## Driver de MySQL

Se usa `PyMySQL` en lugar de `mysqlclient` porque Railway no tiene las headers de MySQL para compilar código C. El shim en `config/__init__.py` lo hace compatible con Django:

```python
import pymysql
pymysql.install_as_MySQLdb()
```

Se requiere `cryptography` porque Railway usa MySQL 8 con autenticación `caching_sha2_password`.

## Archivos estáticos

`whitenoise` sirve los estáticos directamente desde gunicorn. Configurado en `config/settings/production.py` con `CompressedManifestStaticFilesStorage` para compresión y cache-busting automático.

## Migraciones

Corren automáticamente cada vez que el contenedor arranca (antes de gunicorn). Son idempotentes — no hay problema en que corran múltiples veces.

## Conectarse a la BD desde local

Para ejecutar management commands contra la BD de Railway usar `.env.railway`:

```bash
cp .env.railway .env
python manage.py create_test_users
# restaurar después
cp .env.example .env
```

Datos de conexión para MySQL Workbench:
- **Host**: `shortline.proxy.rlwy.net`
- **Port**: `22166`
- **User**: `root`
- **Schema**: `railway`

## Hacer redeploy

Railway hace deploy automático en cada push al branch linkeado. Para forzar un redeploy manual: Railway dashboard → Deployments → Redeploy.
