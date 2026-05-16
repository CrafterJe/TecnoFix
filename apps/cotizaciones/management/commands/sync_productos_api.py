"""
Comando para sincronizar productos desde las APIs externas
hacia la tabla local api_productos_catalogo.

Las fuentes ya no están hardcodeadas: se leen desde la tabla FuenteApi (activas).
Cada fuente tiene un `tipo_parser` que decide qué estrategia usar para parsear sus productos.

Para agregar una API nueva:
  1. Crear el registro FuenteApi desde admin (slug, nombre, base_url, tipo_parser).
  2. Si la API usa un formato distinto al ya soportado, implementar un nuevo fetcher
     debajo en PARSERS.

Uso interactivo (default — menú numerado):
    python manage.py sync_productos_api

Uso no interactivo (para cron / automatización):
    python manage.py sync_productos_api --all-active --no-interactive
    python manage.py sync_productos_api --fuente fixoem --no-interactive
"""
import json
import math
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal, InvalidOperation
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.cotizaciones.models import ApiProductoCatalogo, FuenteApi

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

LIMITE_POR_PAGINA = 250
PAUSA_ENTRE_PAGINAS = 1


# ─────────────────────────────────────────────
#  Fetchers (strategy pattern por tipo_parser)
# ─────────────────────────────────────────────

class BaseFetcher:
    """Contrato común para todos los fetchers."""
    tipo_parser = None  # override en subclases

    def __init__(self, fuente: FuenteApi, stdout, style):
        self.fuente = fuente
        self.stdout = stdout
        self.style = style

    def fetch_all(self) -> list:
        """Descarga TODOS los productos crudos. Devuelve lista de dicts."""
        raise NotImplementedError

    def fetch_first_page(self) -> list:
        """Descarga solo la primera página (para probar conexión)."""
        raise NotImplementedError

    def parse(self, raw: dict, ahora) -> ApiProductoCatalogo:
        """Convierte un producto crudo en una instancia de ApiProductoCatalogo (no guardada)."""
        raise NotImplementedError


class ShopifyV1Fetcher(BaseFetcher):
    """Fetcher para tiendas Shopify (FixOEM, SupraTec, etc.)."""
    tipo_parser = 'shopify_v1'

    def _request_page(self, page):
        url = f'{self.fuente.base_url.rstrip("/")}/products.json?limit={LIMITE_POR_PAGINA}&page={page}'
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        return response.json().get('products', [])

    def fetch_first_page(self):
        return self._request_page(1)

    def fetch_all(self):
        todos = []
        page = 1
        while True:
            try:
                data = self._request_page(page)
            except requests.RequestException as exc:
                self.stdout.write(self.style.ERROR(
                    f'  Error en página {page}: {exc}'
                ))
                break

            if not data:
                self.stdout.write('  Sin más productos.')
                break

            todos.extend(data)
            self.stdout.write(
                f'  Página {page}: +{len(data)} productos (acumulado: {len(todos)})'
            )
            page += 1
            time.sleep(PAUSA_ENTRE_PAGINAS)
        return todos

    def parse(self, raw, ahora):
        producto_id = raw.get('id')
        title = (raw.get('title') or '').strip()
        if not producto_id or not title:
            return None

        variants = raw.get('variants') or []
        if not variants:
            return None
        v = variants[0]

        try:
            precio = Decimal(str(v.get('price') or '0'))
        except InvalidOperation:
            precio = Decimal('0')

        return ApiProductoCatalogo(
            fuente=self.fuente,
            producto_id_externo=str(producto_id),
            titulo=title[:500],
            precio=precio,
            disponible=bool(v.get('available')),
            handle=(raw.get('handle') or '')[:300],
            vendor=(raw.get('vendor') or '')[:200],
            product_type=(raw.get('product_type') or '')[:200],
            url_producto='',
            synced_at=ahora,
        )


class AtHomeV1Fetcher(BaseFetcher):
    """Fetcher para AtHome: lee archivos JSON locales (catalogo_athome_parteXXX.json)."""
    tipo_parser = 'athome_v1'

    def _get_directorio(self) -> Path:
        ruta = self.fuente.base_url
        p = Path(ruta)
        if p.is_absolute():
            return p
        return Path(settings.BASE_DIR) / ruta

    def _leer_archivo(self, archivo: Path) -> list:
        with open(archivo, encoding='utf-8') as f:
            return json.load(f)

    def _listar_archivos(self) -> list[Path]:
        directorio = self._get_directorio()
        if not directorio.is_dir():
            raise FileNotFoundError(
                f'No se encontró el directorio de AtHome: {directorio}\n'
                'Actualiza base_url en /admin/cotizaciones/fuenteapi/'
            )
        archivos = sorted(directorio.glob('catalogo_athome_parte*.json'))
        if not archivos:
            raise FileNotFoundError(
                f'No hay archivos catalogo_athome_parteXXX.json en {directorio}'
            )
        return archivos

    def fetch_first_page(self) -> list:
        archivos = self._listar_archivos()
        return self._leer_archivo(archivos[0])

    def fetch_all(self) -> list:
        archivos = self._listar_archivos()
        todos = []
        for archivo in archivos:
            try:
                datos = self._leer_archivo(archivo)
                todos.extend(datos)
                self.stdout.write(
                    f'  {archivo.name}: +{len(datos)} productos (acumulado: {len(todos)})'
                )
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f'  Error leyendo {archivo.name}: {exc}'))
        return todos

    def parse(self, raw: dict, ahora) -> ApiProductoCatalogo:
        sku = str(raw.get('sku') or '').strip()
        nombre = (raw.get('nombre') or '').strip()
        if not sku or not nombre:
            return None

        try:
            precio = Decimal(str(raw.get('precio') or '0'))
        except InvalidOperation:
            precio = Decimal('0')

        return ApiProductoCatalogo(
            fuente=self.fuente,
            producto_id_externo=sku[:100],
            titulo=nombre[:500],
            precio=precio,
            disponible=bool(raw.get('disponible')),
            handle='',
            vendor='',
            product_type='',
            url_producto=(raw.get('url') or '')[:500],
            synced_at=ahora,
        )


class AtHomeWebFetcher(AtHomeV1Fetcher):
    """
    Fetcher para AtHome: hace scraping en vivo del HTML extrayendo JSON-LD.

    A diferencia de AtHomeV1Fetcher (que lee archivos JSON pre-generados),
    este parser hace HTTP requests al catálogo HTML y parsea los datos en cada sync.
    Pensado para entornos como Railway donde no hay archivos locales.

    Reutiliza parse() de AtHomeV1Fetcher porque produce el mismo formato de dict
    {nombre, sku, precio, stock, disponible, url}.
    """
    tipo_parser = 'athome_web'

    PRODUCTS_PER_PAGE = 12
    WORKERS = 3
    DELAY_BATCH = 0.5
    SCRAPE_USER_AGENT = (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
    )
    FALLBACK_MAX_PAGES = 200

    def _get_session(self):
        session = requests.Session()
        session.headers.update({'User-Agent': self.SCRAPE_USER_AGENT})
        return session

    def _extract_products_from_page(self, session, page):
        url = f'{self.fuente.base_url.rstrip("/")}?page={page}'
        try:
            resp = session.get(url, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as exc:
            self.stdout.write(self.style.ERROR(f'  [ERR] Página {page}: {exc}'))
            return []

        soup = BeautifulSoup(resp.text, 'html.parser')
        products = []
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string or '')
            except (json.JSONDecodeError, AttributeError):
                continue
            if data.get('@type') != 'Product':
                continue

            offers = data.get('offers') or {}
            disponible = (offers.get('availability') or '').endswith('InStock')
            inventory = offers.get('inventoryLevel') or {}
            stock_raw = inventory.get('value', '0') if isinstance(inventory, dict) else '0'

            products.append({
                'nombre': data.get('name'),
                'sku': data.get('sku'),
                'precio': float(offers.get('price') or 0),
                'stock': int(stock_raw) if str(stock_raw).isdigit() else 0,
                'disponible': disponible,
                'url': offers.get('url') or (data.get('mainEntityOfPage') or {}).get('@id'),
            })
        return products

    def _get_total_pages(self, session):
        try:
            resp = session.get(self.fuente.base_url, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as exc:
            self.stdout.write(self.style.ERROR(f'  Error obteniendo página inicial: {exc}'))
            return self.FALLBACK_MAX_PAGES

        soup = BeautifulSoup(resp.text, 'html.parser')
        for script in soup.find_all('script'):
            text = script.string or ''
            match = re.search(r'productsCount\s*[:=]\s*(\d+)', text)
            if match:
                count = int(match.group(1))
                pages = math.ceil(count / self.PRODUCTS_PER_PAGE)
                self.stdout.write(f'  Total productos detectados: {count} -> {pages} páginas')
                return pages
        self.stdout.write(self.style.WARNING(
            f'  No se pudo detectar productsCount, usando fallback {self.FALLBACK_MAX_PAGES} páginas'
        ))
        return self.FALLBACK_MAX_PAGES

    def fetch_first_page(self):
        session = self._get_session()
        return self._extract_products_from_page(session, page=1)

    def fetch_all(self):
        session = self._get_session()
        total_pages = self._get_total_pages(session)

        all_products = []
        found_end = False
        with ThreadPoolExecutor(max_workers=self.WORKERS) as executor:
            for batch_start in range(1, total_pages + 1, self.WORKERS):
                if found_end:
                    break
                batch = range(batch_start, min(batch_start + self.WORKERS, total_pages + 1))
                futures = {executor.submit(self._extract_products_from_page, session, p): p for p in batch}

                page_results = {}
                for future in as_completed(futures):
                    page = futures[future]
                    products = future.result()
                    if not products:
                        found_end = True
                        self.stdout.write(f'  Página {page}: sin productos -> fin del catálogo')
                    else:
                        page_results[page] = products
                        self.stdout.write(
                            f'  Página {page}: +{len(products)} productos (parcial)'
                        )

                for page in sorted(page_results.keys()):
                    all_products.extend(page_results[page])

                if not found_end:
                    time.sleep(self.DELAY_BATCH)

        self.stdout.write(f'  Total scrapeado: {len(all_products)} productos')
        return all_products


# Registry de parsers disponibles.
PARSERS = {
    ShopifyV1Fetcher.tipo_parser: ShopifyV1Fetcher,
    AtHomeV1Fetcher.tipo_parser: AtHomeV1Fetcher,
    AtHomeWebFetcher.tipo_parser: AtHomeWebFetcher,
}


def get_fetcher(fuente: FuenteApi, stdout, style) -> BaseFetcher:
    cls = PARSERS.get(fuente.tipo_parser)
    if cls is None:
        raise ValueError(
            f'No hay parser registrado para tipo_parser="{fuente.tipo_parser}" '
            f'(fuente: {fuente.nombre}). Implementa una subclase de BaseFetcher.'
        )
    return cls(fuente, stdout, style)


# ─────────────────────────────────────────────
#  Comando
# ─────────────────────────────────────────────

class Command(BaseCommand):
    help = 'Sincroniza productos desde APIs externas al catálogo local.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fuente',
            type=str,
            default=None,
            help='Slug de una FuenteApi específica a sincronizar (ej: fixoem). Mutuamente excluyente con --all-active.',
        )
        parser.add_argument(
            '--all-active',
            action='store_true',
            default=False,
            help='Sincroniza todas las fuentes activas. Pensado para cron jobs.',
        )
        parser.add_argument(
            '--no-interactive',
            action='store_true',
            default=False,
            help='No muestra el menú interactivo. Requiere --fuente o --all-active.',
        )

    def handle(self, *args, **options):
        fuente_slug = options.get('fuente')
        all_active = options.get('all_active')
        no_interactive = options.get('no_interactive')

        if no_interactive or fuente_slug or all_active:
            self._handle_no_interactive(fuente_slug, all_active)
            return

        self._mostrar_menu()

    def _handle_no_interactive(self, fuente_slug, all_active):
        if fuente_slug and all_active:
            self.stdout.write(self.style.ERROR(
                '  --fuente y --all-active son mutuamente excluyentes.'
            ))
            return

        if all_active:
            fuentes = list(FuenteApi.objects.filter(activo=True).order_by('orden', 'nombre'))
            if not fuentes:
                self.stdout.write(self.style.WARNING(
                    '  No hay fuentes API activas. Nada que sincronizar.'
                ))
                return
        elif fuente_slug:
            try:
                fuente = FuenteApi.objects.get(slug=fuente_slug, activo=True)
            except FuenteApi.DoesNotExist:
                self.stdout.write(self.style.ERROR(
                    f'  No existe una FuenteApi activa con slug="{fuente_slug}".'
                ))
                return
            fuentes = [fuente]
        else:
            self.stdout.write(self.style.ERROR(
                '  Modo no interactivo requiere --fuente <slug> o --all-active.'
            ))
            return

        self._sincronizar(fuentes)

    # ──────────────────────────────────────────
    #  Menú dinámico
    # ──────────────────────────────────────────
    def _mostrar_menu(self):
        while True:
            fuentes = list(FuenteApi.objects.filter(activo=True).order_by('orden', 'nombre'))

            self.stdout.write('\n' + '=' * 60)
            self.stdout.write(self.style.SUCCESS('  TecnoFix — Sincronización de productos API'))
            self.stdout.write('=' * 60)

            if not fuentes:
                self.stdout.write(self.style.WARNING(
                    '  No hay fuentes API activas. Regístralas en /admin/cotizaciones/fuenteapi/'
                ))
                self.stdout.write('  0. Salir')
                self.stdout.write('-' * 60)
                if input('  Opción: ').strip() == '0':
                    return
                continue

            self.stdout.write('  1. Sincronizar TODAS las fuentes activas')
            for idx, fuente in enumerate(fuentes, start=2):
                self.stdout.write(f'  {idx}. Sincronizar solo {fuente.nombre}')
            self.stdout.write(f'  {len(fuentes) + 2}. Probar conexión (sin guardar)')
            self.stdout.write(f'  {len(fuentes) + 3}. Ver estadísticas del catálogo local')
            self.stdout.write(f'  {len(fuentes) + 4}. Eliminar TODOS los productos del catálogo')
            self.stdout.write('  0. Salir')
            self.stdout.write('-' * 60)

            opcion = input('  Opción: ').strip()

            if opcion == '0':
                self.stdout.write(self.style.SUCCESS('\n  ¡Hasta luego!\n'))
                return
            if opcion == '1':
                self._sincronizar(fuentes)
                continue
            if opcion == str(len(fuentes) + 2):
                self._probar_conexion(fuentes)
                continue
            if opcion == str(len(fuentes) + 3):
                self._mostrar_estadisticas()
                continue
            if opcion == str(len(fuentes) + 4):
                self._eliminar_catalogo()
                continue

            try:
                idx_fuente = int(opcion) - 2
                if 0 <= idx_fuente < len(fuentes):
                    self._sincronizar([fuentes[idx_fuente]])
                    continue
            except ValueError:
                pass
            self.stdout.write(self.style.WARNING('  Opción no válida.'))

    # ──────────────────────────────────────────
    #  Operaciones
    # ──────────────────────────────────────────
    def _sincronizar(self, fuentes):
        total_global = 0
        total_marcados = 0
        for fuente in fuentes:
            self.stdout.write('\n' + '=' * 60)
            self.stdout.write(self.style.SUCCESS(f'  Sincronizando: {fuente.nombre} ({fuente.tipo_parser})'))
            self.stdout.write('=' * 60)

            try:
                fetcher = get_fetcher(fuente, self.stdout, self.style)
            except ValueError as exc:
                self.stdout.write(self.style.ERROR(f'  {exc}'))
                continue

            sync_started_at = timezone.now()

            try:
                productos = fetcher.fetch_all()
            except Exception as exc:
                self.stdout.write(self.style.ERROR(
                    f'  Error obteniendo productos: {exc}\n'
                    '  Saltando mark-and-sweep para evitar marcar catálogo como agotado por fallo temporal.'
                ))
                continue

            if not productos:
                self.stdout.write(self.style.WARNING(
                    '  Sin productos descargados. Saltando mark-and-sweep '
                    '(no se marca disponible=False sin datos frescos).'
                ))
                continue

            guardados, errores = self._guardar_productos(productos, fetcher)
            total_global += guardados

            marcados = self._marcar_no_vistos(fuente, sync_started_at)
            total_marcados += marcados

            self.stdout.write(self.style.SUCCESS(
                f'\n  {fuente.nombre}: {guardados} guardados, {errores} errores, '
                f'{marcados} marcados como no disponibles (descontinuados).'
            ))

        self.stdout.write(self.style.SUCCESS(
            f'\n  Total escrito en BD: {total_global} productos.\n'
            f'  Total marcados como descontinuados: {total_marcados}.'
        ))

    def _marcar_no_vistos(self, fuente, sync_started_at):
        """
        Mark-and-sweep: marca disponible=False los productos de esta fuente
        que NO fueron tocados en este sync (synced_at < sync_started_at).

        Productos que ya estaban disponible=False no se tocan (no hay nada que actualizar).
        Solo se ejecuta si el sync trajo datos frescos (validado antes de llamar).
        """
        return ApiProductoCatalogo.objects.filter(
            fuente=fuente,
            synced_at__lt=sync_started_at,
            disponible=True,
        ).update(disponible=False)

    def _probar_conexion(self, fuentes):
        self.stdout.write('\n  Probando conexión a las fuentes activas...\n')
        for fuente in fuentes:
            try:
                fetcher = get_fetcher(fuente, self.stdout, self.style)
                productos = fetcher.fetch_first_page()
                self.stdout.write(self.style.SUCCESS(
                    f'  OK  {fuente.nombre}: {len(productos)} productos en página 1'
                ))
            except Exception as exc:
                self.stdout.write(self.style.ERROR(
                    f'  ERR {fuente.nombre}: {exc}'
                ))

    def _mostrar_estadisticas(self):
        total = ApiProductoCatalogo.objects.count()
        if total == 0:
            self.stdout.write(self.style.WARNING(
                '\n  No hay productos en el catálogo local.'
            ))
            return

        self.stdout.write(f'\n  Total de productos en catálogo: {total}')
        for fuente in FuenteApi.objects.all().order_by('orden', 'nombre'):
            count = ApiProductoCatalogo.objects.filter(fuente=fuente).count()
            disponibles = ApiProductoCatalogo.objects.filter(
                fuente=fuente, disponible=True,
            ).count()
            self.stdout.write(
                f'    - {fuente.nombre} ({fuente.slug}): {count} productos ({disponibles} disponibles)'
            )

        ultima = ApiProductoCatalogo.objects.order_by('-synced_at').first()
        if ultima:
            self.stdout.write(f'\n  Última sincronización: {ultima.synced_at}')

    def _eliminar_catalogo(self):
        total = ApiProductoCatalogo.objects.count()
        if total == 0:
            self.stdout.write(self.style.WARNING(
                '\n  El catálogo ya está vacío.'
            ))
            return

        confirm = input(
            self.style.WARNING(
                f'\n  ¿Eliminar {total} productos del catálogo? (s/N): '
            )
        ).strip().lower()
        if confirm != 's':
            self.stdout.write('  Cancelado.')
            return

        eliminados, _ = ApiProductoCatalogo.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(
            f'  {eliminados} producto(s) eliminado(s).'
        ))

    # ──────────────────────────────────────────
    #  Persistencia (bulk_create con upsert)
    # ──────────────────────────────────────────
    def _guardar_productos(self, productos, fetcher: BaseFetcher):
        BATCH = 500
        total = len(productos)
        ahora = timezone.now()

        self.stdout.write(f'  Parseando {total} productos...')
        objs = []
        errores = 0

        for raw in productos:
            try:
                obj = fetcher.parse(raw, ahora)
            except Exception as exc:
                errores += 1
                self.stdout.write(self.style.ERROR(
                    f'  [ERR] {raw.get("title", "?")}: {exc}'
                ))
                continue

            if obj is None:
                errores += 1
            else:
                objs.append(obj)

        if not objs:
            self.stdout.write(self.style.WARNING('  Ningún producto válido para guardar.'))
            return 0, errores

        self.stdout.write(f'  Guardando en BD en lotes de {BATCH}...')

        guardados = 0
        for i in range(0, len(objs), BATCH):
            lote = objs[i:i + BATCH]
            resultado = ApiProductoCatalogo.objects.bulk_create(
                lote,
                update_conflicts=True,
                update_fields=['titulo', 'precio', 'disponible', 'handle', 'vendor', 'product_type', 'url_producto', 'synced_at'],
            )
            guardados += len(resultado)
            self.stdout.write(f'  Lote {i // BATCH + 1}: {len(resultado)} registros guardados.')

        return guardados, errores
