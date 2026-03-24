# TecnoFix Backend

API REST para sistema de gestión de taller de reparación de dispositivos electrónicos.
Administra órdenes de servicio, inventario, clientes y técnicos con control de acceso por roles.

## Stack

- Python 3.11 + Django 5.0
- Django REST Framework 3.15
- MySQL (mysqlclient)
- JWT via djangorestframework-simplejwt
- Swagger via drf-spectacular
- pytest + factory-boy (tests)

## Requisitos previos

- Python 3.11+
- MySQL 8.0+
- Git

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

# 8. Crear usuarios de prueba (menu interactivo)
python manage.py create_test_users

# 9. Sembrar datos de prueba (menu interactivo)
python manage.py seed_data

# 10. Correr el servidor
python manage.py runserver
```

## Variables de entorno (.env)

| Variable | Descripcion | Ejemplo |
|---|---|---|
| `SECRET_KEY` | Clave secreta de Django | `bn%_i197a4gu=...` |
| `DEBUG` | Modo debug | `True` |
| `DB_NAME` | Nombre de la BD | `tecnofix` |
| `DB_USER` | Usuario MySQL | `root` |
| `DB_PASSWORD` | Contrasena MySQL | `mipassword` |
| `DB_HOST` | Host MySQL | `localhost` |
| `DB_PORT` | Puerto MySQL | `3306` |

## Estructura del proyecto

```
TecnoFix-BackEnd/
├── config/
│   ├── settings/
│   │   ├── base.py          # Configuracion base
│   │   ├── development.py   # Desarrollo (CORS abierto, SQL logs)
│   │   └── production.py    # Produccion (HTTPS, CORS restringido)
│   ├── urls.py              # Rutas principales
│   └── wsgi.py
├── core/                    # App compartida (no es de negocio)
│   ├── mixins.py            # AuditableMixin
│   ├── middleware.py        # AuditMiddleware
│   ├── signals.py           # Auditoria automatica
│   ├── permissions.py       # IsAdmin, IsTecnico, IsRecepcion...
│   ├── pagination.py        # StandardResultsPagination
│   └── utils.py             # Generador de numero de orden
├── apps/
│   ├── users/               # Usuarios y autenticacion
│   ├── clientes/            # Clientes y dispositivos
│   ├── ordenes/             # Ordenes, evidencias, refacciones usadas
│   ├── inventario/          # Refacciones y compatibilidades
│   └── auditoria/           # Registro de auditoria (solo lectura)
├── requirements/
│   ├── base.txt
│   ├── development.txt
│   └── production.txt
├── logs/                    # Logs rotativos (generados automaticamente)
├── manage.py
└── .env.example
```

## Endpoints principales

Base URL: `http://localhost:8000/api/v1/`

| Recurso | URL |
|---|---|
| Login | `POST /users/auth/login/` |
| Refresh token | `POST /users/auth/refresh/` |
| Usuarios | `/users/` |
| Clientes | `/clientes/` |
| Dispositivos | `/clientes/dispositivos/` |
| Ordenes | `/ordenes/` |
| Evidencias | `/ordenes/evidencias/` |
| Inventario | `/inventario/` |
| Auditoria | `/auditoria/` |

Documentacion interactiva (Swagger): `http://localhost:8000/api/v1/docs/`

## Roles y permisos

| Rol | Acceso |
|---|---|
| `admin` | Acceso total |
| `tecnico` | Lectura general, puede cambiar estado de ordenes y ajustar stock |
| `recepcion` | Crear clientes, dispositivos y ordenes |

## Comandos utiles

```bash
# Usuarios de prueba (menu interactivo)
python manage.py create_test_users

# Datos de prueba (menu interactivo)
python manage.py seed_data

# Correr tests
pytest

# Tests con cobertura
pytest --cov

# Tests de una sola app
pytest apps/ordenes/
```

## Credenciales de prueba

| Email | Contrasena | Rol |
|---|---|---|
| admin@tecnofix.com | Admin2024! | Administrador |
| tecnico1@tecnofix.com | Tecnico2024! | Tecnico |
| tecnico2@tecnofix.com | Tecnico2024! | Tecnico |
| recepcion1@tecnofix.com | Recepcion2024! | Recepcion |
| recepcion2@tecnofix.com | Recepcion2024! | Recepcion |

## Auditoria automatica

Todos los modelos que heredan `AuditableMixin` quedan auditados automaticamente.
Cada CREATE, UPDATE y DELETE genera un registro en `AuditLog` con:
- Usuario que realizo la accion
- IP de origen
- Valores anteriores y nuevos en JSON

Los registros son accesibles en `GET /api/v1/auditoria/` (solo administradores).

## Produccion

```bash
# Instalar dependencias de produccion
pip install -r requirements/production.txt

# Variable de entorno para settings de produccion
set DJANGO_SETTINGS_MODULE=config.settings.production

# Colectar archivos estaticos
python manage.py collectstatic

# Correr con gunicorn
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```
