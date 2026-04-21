# TecnoFix — Backend

API REST para un sistema de gestión de taller de reparación de dispositivos electrónicos.
Administra órdenes de servicio, inventario, clientes y técnicos con control de acceso por roles, auditoría automática y registro de evidencias fotográficas.

Disponible como aplicación de escritorio Windows (.msi) y como aplicación web. Este repositorio es el backend.

---

## Stack

| Tecnología | Versión | Uso |
|---|---|---|
| Python | 3.11 | Lenguaje |
| Django | 5.0.6 | Framework web |
| Django REST Framework | 3.15.2 | API REST |
| djangorestframework-simplejwt | 5.3.1 | Autenticación JWT |
| MySQL | 8.0+ | Base de datos |
| mysqlclient | 2.2.4 | Driver MySQL |
| django-cors-headers | 4.4.0 | CORS para el frontend |
| Pillow | 10.4.0 | Imágenes de evidencias |
| drf-spectacular | 0.27.2 | Documentación Swagger |
| pytest + factory-boy | — | Tests |

---

## Requisitos previos

- Python 3.11+
- MySQL 8.0+
- Git

---

## Instalación

```bash
# 1. Clonar el repositorio
git clone <url-del-repo>
cd TecnoFix-BackEnd

# 2. Crear y activar el entorno virtual
python -m venv venv

# Windows PowerShell
.\venv\Scripts\Activate.ps1

# Windows CMD
venv\Scripts\activate.bat

# Linux / Mac
source venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements/development.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env con los datos de tu BD y SECRET_KEY

# 5. Generar SECRET_KEY
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# 6. Crear la base de datos en MySQL
mysql -u root -p -e "CREATE DATABASE tecnofix CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 7. Aplicar migraciones
python manage.py makemigrations
python manage.py migrate

# 8. Crear usuarios de prueba (menú interactivo)
python manage.py create_test_users

# 9. Sembrar datos de prueba (menú interactivo)
python manage.py seed_data

# 10. Correr el servidor
python manage.py runserver
```

---

## Variables de entorno (.env)

| Variable | Descripción | Ejemplo |
|---|---|---|
| `SECRET_KEY` | Clave secreta de Django | `bn%_i197a4gu=...` |
| `DEBUG` | Modo debug | `True` |
| `DB_NAME` | Nombre de la BD | `tecnofix` |
| `DB_USER` | Usuario MySQL | `root` |
| `DB_PASSWORD` | Contraseña MySQL | `mipassword` |
| `DB_HOST` | Host MySQL | `localhost` |
| `DB_PORT` | Puerto MySQL | `3306` |
| `ALLOWED_HOSTS` | Hosts permitidos | `localhost,127.0.0.1` |
| `CORS_ALLOWED_ORIGINS` | Orígenes del frontend | `http://localhost:5173` |

Ver `.env.example` para la plantilla completa.

---

## Estructura del proyecto

```
TecnoFix-BackEnd/
├── config/
│   ├── settings/
│   │   ├── base.py          # Configuración base
│   │   ├── development.py   # Desarrollo (CORS abierto, debug toolbar)
│   │   └── production.py    # Producción (HTTPS, CORS restringido)
│   ├── urls.py              # Rutas principales bajo /api/v1/
│   └── wsgi.py
├── core/                    # App compartida (no es de negocio)
│   ├── models.py            # BaseModel abstracto (created_at, updated_at)
│   ├── mixins.py            # AuditableMixin (marcador de auditoría)
│   ├── middleware.py        # AuditMiddleware (guarda user+IP en thread-local)
│   ├── signals.py           # Handlers pre/post save/delete para AuditLog
│   ├── permissions.py       # IsAdmin, IsTecnico, IsRecepcion...
│   ├── pagination.py        # StandardResultsPagination (page_size=20, máx 100)
│   └── utils.py             # Generador de número de orden ORD-YYYYMMDD-NNN
├── apps/
│   ├── users/               # Usuario custom (login por email), roles JWT
│   ├── clientes/            # Clientes y dispositivos
│   ├── ordenes/             # Órdenes, evidencias, refacciones usadas
│   ├── inventario/          # Refacciones y compatibilidades
│   └── auditoria/           # Registro de auditoría (solo lectura vía API)
├── docs/
│   ├── admin/               # Convenciones y guías internas
│   ├── PR/                  # Descripciones de pull requests
│   ├── users/               # Docs y testing del módulo usuarios
│   ├── clientes/            # Docs y testing del módulo clientes
│   ├── ordenes/             # Docs y testing del módulo órdenes
│   ├── inventario/          # Docs y testing del módulo inventario
│   ├── auditoria/           # Docs y testing del módulo auditoría
│   └── core/                # Docs de utilidades compartidas
├── requirements/
│   ├── base.txt
│   ├── development.txt
│   └── production.txt
├── logs/                    # app.log rotativo (generado automáticamente)
├── media/                   # Imágenes de evidencias (generado automáticamente)
│   └── evidencias/
│       └── orden_ORD-XXXX/  # Imágenes agrupadas por orden
├── conftest.py              # Fixtures globales de tests
├── manage.py
└── .env.example
```

---

## API

Base URL: `http://localhost:8000/api/v1/`

| Módulo | Endpoints |
|---|---|
| Auth | `POST /users/auth/login/` · `POST /users/auth/refresh/` |
| Usuarios | `/users/` + cambiar-password, activar, desactivar |
| Clientes | `/clientes/` |
| Dispositivos | `/clientes/dispositivos/` |
| Órdenes | `/ordenes/` + cambiar-estado, asignar-tecnico, agregar-refaccion |
| Evidencias | `/ordenes/evidencias/` |
| Inventario | `/inventario/` + ajustar-stock |
| Compatibilidades | `/inventario/compatibles/` |
| Auditoría | `/auditoria/` |

Documentación interactiva (Swagger): `http://localhost:8000/api/v1/docs/`

### Autenticación

JWT Bearer en el header de cada petición:

```
Authorization: Bearer <access_token>
```

- Access token: 8 horas
- Refresh token: 1 día, se rota en cada uso

### Paginación

Todas las respuestas de listado siguen este formato:

```json
{
  "count": 45,
  "total_pages": 3,
  "current_page": 1,
  "next": "http://localhost:8000/api/v1/ordenes/?page=2",
  "previous": null,
  "results": []
}
```

Parámetros: `?page=N` · `?page_size=N` (máximo 100, default 20)

---

## Roles y permisos

| Rol | Acceso |
|---|---|
| `admin` | Acceso total: usuarios, eliminar, auditoría, asignar técnicos |
| `tecnico` | Ver órdenes asignadas, cambiar estado, ajustar stock |
| `recepcion` | Crear clientes, dispositivos y órdenes |

---

## Comandos útiles

```bash
# Servidor de desarrollo
python manage.py runserver

# Usuarios de prueba (menú interactivo)
python manage.py create_test_users

# Datos de prueba (menú interactivo)
python manage.py seed_data

# Correr todos los tests
pytest

# Tests de una sola app
pytest apps/ordenes/

# Tests por nombre
pytest -k test_login

# Tests con cobertura
pytest --cov
```

---

## Credenciales de prueba

> Disponibles después de ejecutar `python manage.py create_test_users`

| Email | Contraseña | Rol |
|---|---|---|
| admin@tecnofix.com | Admin2024! | Administrador |
| tecnico1@tecnofix.com | Tecnico2024! | Técnico |
| tecnico2@tecnofix.com | Tecnico2024! | Técnico |
| recepcion1@tecnofix.com | Recepcion2024! | Recepción |
| recepcion2@tecnofix.com | Recepcion2024! | Recepción |

---

## Auditoría automática

Todos los modelos que heredan `AuditableMixin` quedan auditados automáticamente.
Cada `CREATE`, `UPDATE` y `DELETE` genera un registro en `AuditLog` con:

- Usuario que realizó la acción (vía thread-local del `AuditMiddleware`)
- IP de origen
- Valores anteriores y nuevos en JSON

Los registros son accesibles en `GET /api/v1/auditoria/` (solo administradores). Los logs nunca se crean manualmente — es todo automático vía Django signals.

---

## Número de orden

- Formato: `ORD-YYYYMMDD-NNN` (ej. `ORD-20240324-001`)
- Generado automáticamente en `Orden.save()`
- El contador `NNN` es diario — reinicia desde `001` cada día
- Usa `select_for_update()` para evitar duplicados bajo concurrencia

---

## Producción

```bash
# Instalar dependencias de producción
pip install -r requirements/production.txt

# Configurar settings de producción
export DJANGO_SETTINGS_MODULE=config.settings.production

# Colectar archivos estáticos
python manage.py collectstatic

# Correr con gunicorn
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

> En producción: configurar `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS` y `DEBUG=False` en el `.env`.
