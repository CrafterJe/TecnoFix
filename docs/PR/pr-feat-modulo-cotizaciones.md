# Pull Request: Módulo de Cotizaciones

## Descripción

Nueva app `apps.cotizaciones` que implementa el flujo completo de generación de cotizaciones para reparaciones de dispositivos electrónicos. Cubre la configuración por administrador (categorías, subcategorías, tipos de reparación, fórmulas), la búsqueda de precios desde APIs externas (FixOEM, SupraTecMX) o entrada manual, la acumulación de items en una cotización, el cálculo automático de precio final por fórmula parametrizable, y la generación de PDFs en dos versiones (cliente y empresa).

---

## Resumen del flujo

```
[Buscar / elegir tipo dispositivo]
        ↓
[Categoría: Celulares/Tablets | Computadoras | Otro]
        ↓
[Subcategoría: Android | iPhone] (opcional)
        ↓
[Fuente: API 1 (FixOEM) | API 2 (SupraTec) | Manual]
        ↓
[Tipo de reparación: Display, Batería, etc.]
        ↓
[Aplica fórmula → precio final]   ó   [Personalizado → precio manual]
        ↓
[Item se agrega a la cotización]
        ↓
[Generar PDF Cliente / PDF Empresa]
```

---

## Cambios incluidos

### Nueva app `apps/cotizaciones/`

| Archivo | Propósito |
|---|---|
| `models.py` | 8 modelos: `CategoriaDispositivo`, `SubcategoriaDispositivo`, `TipoReparacion`, `FormulaReparacion`, `FuenteApi`, `Cotizacion`, `CotizacionItem`, `ApiProductoCatalogo` |
| `admin.py` | Admin Django con inlines y autocompletes para gestionar todo desde `/admin/` |
| `serializers.py` | Serializers + validación de fórmula al agregar items + serializers de reorder |
| `views.py` | ViewSets con CRUDs, búsqueda full-text en el catálogo, acciones para PDF y endpoints bulk de reorder |
| `urls.py` | Router DRF — todos los endpoints bajo `/api/v1/cotizaciones/` |
| `pdf.py` | Generación de PDFs con ReportLab (versiones cliente y empresa) |
| `management/commands/sync_productos_api.py` | Menú interactivo para sincronizar productos desde las `FuenteApi` registradas |

### Modificaciones

| Archivo | Cambio |
|---|---|
| `config/settings/base.py` | Agregar `apps.cotizaciones` a `INSTALLED_APPS` |
| `config/urls.py` | Registrar `path('cotizaciones/', include('apps.cotizaciones.urls'))` |
| `core/utils.py` | Nueva función `generate_quote_number()` con formato `COT-YYYYMMDD-NNN` |
| `requirements/base.txt` | Agregar `reportlab==4.2.2` y `requests==2.32.3` |

---

## Modelos y BD

### Tablas nuevas (8)

| Tabla | Para qué sirve |
|---|---|
| `cotizacion_categorias` | Celulares/Tablets, Computadoras, Otro |
| `cotizacion_subcategorias` | Android, iPhone (hijas de categoría) |
| `cotizacion_tipos_reparacion` | Display, Batería, Centro de Carga, etc. |
| `cotizacion_formulas` | `multiplicador` + `incremento` o `es_personalizado=True` |
| `cotizacion_fuentes_api` | Catálogo de APIs proveedoras (FixOEM, SupraTec, futuras) con `tipo_parser` para extensibilidad |
| `cotizaciones` | Documento de cotización (`COT-YYYYMMDD-NNN`, nombre cliente, estado) |
| `cotizacion_items` | Líneas de cada cotización con precio base, precio final, fórmula snapshot, link, `fuente_api` o `es_manual` |
| `api_productos_catalogo` | Caché de productos sincronizados desde las `FuenteApi` registradas |

### Notas de diseño

- **Fórmula parametrizada**: estructura siempre `precio_base * multiplicador + incremento`. Cuando `es_personalizado=True`, no hay cálculo: el precio se ingresa a mano.
- **Resolución de fórmula**: al agregar un item, se busca primero la fórmula específica `(tipo_reparacion, subcategoria)`. Si no existe, se usa la genérica `(tipo_reparacion, subcategoria=null)`.
- **Snapshot de fórmula**: cada `CotizacionItem` guarda la expresión textual (`precio*2+400`) al momento de la creación. Si el admin modifica la fórmula después, las cotizaciones históricas mantienen su cálculo original.
- **Cliente opcional**: `Cotizacion.cliente` (FK a `clientes.Cliente`) es opcional. Si no se liga, basta con `nombre_cliente` en texto.
- **Fuentes extensibles**: `FuenteApi` reemplaza el viejo enum hardcodeado (`api1/api2/manual`). Para agregar una nueva tienda no hay que tocar código: se registra desde admin con su `tipo_parser` (hoy `shopify_v1`).
- **Catálogo de APIs no auditable**: `ApiProductoCatalogo` NO hereda `AuditableMixin` (es caché, no datos de negocio).
- **Toda la configuración audita**: categorías, subcategorías, tipos, fórmulas y fuentes API heredan `AuditableMixin`, por lo que cualquier modificación desde admin genera `AuditLog`. Las operaciones bulk de reorder generan **una sola** entrada de `AuditLog` por operación (no N).

---

## Endpoints

Base: `/api/v1/cotizaciones/`

### Configuración (solo admin para escritura)
- `GET/POST/PUT/DELETE /categorias/`
- `GET/POST/PUT/DELETE /subcategorias/?categoria={id}`
- `GET/POST/PUT/DELETE /tipos-reparacion/?categoria={id}`
- `GET/POST/PUT/DELETE /formulas/?tipo_reparacion={id}`
- `GET /formulas/disponibles/` — fórmulas únicas (deduplicadas por `multiplicador`+`incremento`+`es_personalizado`). Útil para que el front muestre un dropdown sin duplicados; cada item incluye un `formula_id` representativo.
- `GET/POST/PUT/DELETE /fuentes-api/` — CRUD del catálogo de APIs proveedoras (campos: `slug`, `nombre`, `base_url`, `tipo_parser`, `activo`, `orden`, `notas`). Permite agregar nuevas tiendas desde admin sin tocar código.

### Reorder (drag & drop, solo admin)
- `POST /categorias/reorder/` — body `{ "ids": [3, 1, 2] }`. Asigna `orden = index + 1` en una transacción.
- `POST /subcategorias/reorder/` — body `{ "categoria_id": 5, "ids": [10, 8, 12] }`. Valida que todos los IDs pertenezcan a esa categoría.
- `POST /tipos-reparacion/reorder/` — body `{ "categoria_id": 5, "ids": [...] }`. Mismo patrón.

Devuelven `200 OK` con la lista actualizada (en el nuevo orden). Si algún ID no existe o no pertenece al scope, no se aplica ningún cambio (`400`). Operación atómica, registra una única entrada en `AuditLog` describiendo el reorder completo.

### Catálogo de productos (cualquier usuario autenticado)
- `GET /productos-api/?fuente=fixoem&disponible=true&q=display+iphone`

### Resolver fórmula (preview sin guardar)
- `GET /resolver-formula/?tipo_reparacion={id}&subcategoria={id}&precio_base={n}`
  - Devuelve `{ tiene_formula, es_personalizado, expresion, precio_base, precio_final, mensaje }`

### Cotizaciones
- `GET /` — lista paginada
- `POST /` — crear cotización (en estado `borrador`)
- `GET /{id}/` — detalle con items
- `DELETE /{id}/` — eliminar (solo admin)
- `POST /{id}/items/` — agregar un item (calcula precio final)
- `DELETE /{id}/items/{item_id}/` — quitar un item
- `POST /{id}/cambiar-estado/` — `borrador` → `finalizada` / `cancelada`
- `GET /{id}/pdf-cliente/` — PDF para el cliente
- `GET /{id}/pdf-empresa/` — PDF interno (incluye fuente, fórmula, link)

---

## Permisos

| Acción | Rol mínimo |
|---|---|
| Ver/crear/editar cotizaciones | Cualquier autenticado |
| Eliminar cotización | Admin |
| Configuración (categorías, fórmulas, etc.) | Admin |
| Sincronizar APIs (`manage.py`) | Acceso al servidor |

---

## Sincronización de productos (caché)

Las APIs no se consultan en tiempo real durante la cotización. Se sincronizan a un catálogo local mediante el management command:

```bash
python manage.py sync_productos_api
```

Menú interactivo:
1. Sincronizar TODAS las tiendas
2. Sincronizar solo FixOEM
3. Sincronizar solo SupraTecMX
4. Probar conexión (sin guardar)
5. Ver estadísticas del catálogo local
6. Eliminar TODOS los productos del catálogo
0. Salir

En producción se puede agendar con **Windows Task Scheduler** (o cron) para ejecutarlo 1 vez al día.

---

## PDFs

Generados con **ReportLab**:

- **Cliente** (`/pdf-cliente/`): título, número de cotización, nombre del cliente, conceptos cotizados con cantidad/precio unitario/subtotal y total.
- **Empresa** (`/pdf-empresa/`): igual que la versión cliente más fuente del precio (API/Manual), precio base sin fórmula, fórmula aplicada, link de referencia y disponibilidad.

> Para tickets térmicos (impresora ESC/POS) se agregará `python-escpos` en un PR posterior; va por canal separado al PDF.

---

## Cómo probar

### 1. Instalar dependencias nuevas
```bash
source venv/Scripts/activate
pip install -r requirements/base.txt
```

### 2. Crear y aplicar migración
```bash
python manage.py makemigrations cotizaciones
python manage.py migrate
```

### 3. (Opcional) Sembrar configuración base
Crear desde `/admin/` o por shell:
- Categoría "Celulares/Tablets" con subcategorías "Android" e "iPhone".
- Tipos de reparación: Display, Batería, Tapa, etc.
- Fórmulas según la tabla del Excel:
  - Display/Android: `multiplicador=2, incremento=400`
  - Display/iPhone: `multiplicador=2, incremento=400`
  - Batería/Android: `multiplicador=2, incremento=200`
  - Batería/iPhone: `multiplicador=2, incremento=400`
  - Centro de Carga (ambos): `es_personalizado=True`
  - … etc.

### 4. Sincronizar productos de las APIs
```bash
python manage.py sync_productos_api
# Elegir opción 1 (todas las tiendas)
```

### 5. Crear una cotización vía API

```bash
# Crear cotización
POST /api/v1/cotizaciones/
{ "nombre_cliente": "Juan Pérez", "notas": "Reparación de pantalla y batería" }

# Buscar producto en catálogo
GET /api/v1/cotizaciones/productos-api/?q=display+iphone+15&fuente=fixoem

# (Preview) Resolver fórmula
GET /api/v1/cotizaciones/resolver-formula/?tipo_reparacion=1&subcategoria=2&precio_base=1500

# Agregar item desde API (la fórmula se auto-resuelve por tipo+subcategoría)
POST /api/v1/cotizaciones/{id}/items/
{
  "tipo_reparacion_id": 1,
  "subcategoria_id": 2,
  "es_manual": false,
  "fuente_api_id": 1,
  "producto_titulo": "Display iPhone 15 Pro",
  "precio_base": "1500.00",
  "disponible": true,
  "cantidad": 1
}

# Agregar item desde API con fórmula EXPLÍCITA (el front la eligió del dropdown)
POST /api/v1/cotizaciones/{id}/items/
{
  "tipo_reparacion_id": 1,
  "subcategoria_id": 2,
  "es_manual": false,
  "fuente_api_id": 1,
  "formula_id": 7,
  "producto_titulo": "Display iPhone 15 Pro",
  "precio_base": "1500.00",
  "cantidad": 1
}

# Agregar item manual con precio personalizado (sin fórmula)
POST /api/v1/cotizaciones/{id}/items/
{
  "tipo_reparacion_id": 3,
  "subcategoria_id": 1,
  "es_manual": true,
  "formula_id": null,
  "producto_titulo": "Liberación equipo Motorola",
  "precio_base": "0",
  "precio_final_manual": "350.00",
  "link_referencia": "https://ejemplo.com/proveedor",
  "cantidad": 1
}

# Reorder (drag & drop, solo admin)
POST /api/v1/cotizaciones/categorias/reorder/
{ "ids": [3, 1, 2] }

POST /api/v1/cotizaciones/subcategorias/reorder/
{ "categoria_id": 5, "ids": [10, 8, 12] }

# Quitar un item
DELETE /api/v1/cotizaciones/{id}/items/{item_id}/

# Finalizar
POST /api/v1/cotizaciones/{id}/cambiar-estado/
{ "estado": "finalizada" }

# Descargar PDFs
GET /api/v1/cotizaciones/{id}/pdf-cliente/
GET /api/v1/cotizaciones/{id}/pdf-empresa/
```

---

## Notas pendientes / futuro

- **Computadoras** y **Otro**: aún sin tipos/fórmulas precargadas (el admin las definirá manualmente cuando lleguen).
- **Tickets térmicos**: cuando se integre la impresora térmica, agregar `python-escpos` y endpoint `/ticket/`.
- **Integración con clientes**: por ahora `nombre_cliente` es texto libre. Cuando el módulo de clientes esté listo, se podrá ligar `Cotizacion.cliente` y autocompletar el nombre.
- **Sembrado de datos**: agregar opción al management command `seed_data` para poblar categorías/subcategorías/tipos/fórmulas iniciales de celulares.
