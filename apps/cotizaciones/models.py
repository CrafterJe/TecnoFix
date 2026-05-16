from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils.text import slugify

from core.mixins import AuditableMixin
from core.models import BaseModel


class CategoriaDispositivo(AuditableMixin, BaseModel):
    """Categoría principal de dispositivo: Celulares/Tablets, Computadoras, Otro."""
    nombre = models.CharField('Nombre', max_length=80, unique=True)
    slug = models.SlugField('Slug', max_length=80, unique=True, blank=True)
    activo = models.BooleanField('Activo', default=True)
    orden = models.PositiveIntegerField('Orden de visualización', default=0)

    class Meta:
        db_table = 'cotizacion_categorias'
        verbose_name = 'Categoría de dispositivo'
        verbose_name_plural = 'Categorías de dispositivo'
        ordering = ['orden', 'nombre']

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = _unique_slug(CategoriaDispositivo, self.nombre, instance=self)
        super().save(*args, **kwargs)


class SubcategoriaDispositivo(AuditableMixin, BaseModel):
    """Subcategoría que segmenta una categoría: Android, iPhone (hijos de Celulares)."""
    categoria = models.ForeignKey(
        CategoriaDispositivo,
        on_delete=models.CASCADE,
        related_name='subcategorias',
        verbose_name='Categoría',
    )
    nombre = models.CharField('Nombre', max_length=80)
    slug = models.SlugField('Slug', max_length=80, blank=True)
    activo = models.BooleanField('Activo', default=True)
    orden = models.PositiveIntegerField('Orden de visualización', default=0)

    class Meta:
        db_table = 'cotizacion_subcategorias'
        verbose_name = 'Subcategoría de dispositivo'
        verbose_name_plural = 'Subcategorías de dispositivo'
        ordering = ['categoria', 'orden', 'nombre']
        constraints = [
            models.UniqueConstraint(
                fields=['categoria', 'slug'],
                name='uq_subcategoria_categoria_slug',
            ),
        ]

    def __str__(self):
        return f'{self.categoria.nombre} / {self.nombre}'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = _unique_slug(
                SubcategoriaDispositivo, self.nombre,
                instance=self, scope={'categoria': self.categoria_id},
            )
        super().save(*args, **kwargs)


def _unique_slug(model_cls, source: str, instance=None, scope: dict | None = None) -> str:
    """Genera un slug único a partir de `source`, agregando sufijo numérico si ya existe."""
    base = slugify(source) or 'item'
    slug = base
    counter = 2
    qs = model_cls.objects.all()
    if scope:
        qs = qs.filter(**scope)
    if instance and instance.pk:
        qs = qs.exclude(pk=instance.pk)
    while qs.filter(slug=slug).exists():
        slug = f'{base}-{counter}'
        counter += 1
    return slug


class TipoReparacion(AuditableMixin, BaseModel):
    """Tipo de reparación: Display, Batería, Centro de Carga, etc."""
    categoria = models.ForeignKey(
        CategoriaDispositivo,
        on_delete=models.CASCADE,
        related_name='tipos_reparacion',
        verbose_name='Categoría',
    )
    nombre = models.CharField('Nombre', max_length=120)
    descripcion = models.TextField('Descripción', blank=True)
    activo = models.BooleanField('Activo', default=True)
    orden = models.PositiveIntegerField('Orden de visualización', default=0)

    class Meta:
        db_table = 'cotizacion_tipos_reparacion'
        verbose_name = 'Tipo de reparación'
        verbose_name_plural = 'Tipos de reparación'
        ordering = ['categoria', 'orden', 'nombre']
        constraints = [
            models.UniqueConstraint(
                fields=['categoria', 'nombre'],
                name='uq_tiporeparacion_categoria_nombre',
            ),
        ]
        indexes = [
            models.Index(fields=['activo'], name='idx_tiporep_activo'),
        ]

    def __str__(self):
        return f'{self.nombre} ({self.categoria.nombre})'


class FormulaReparacion(AuditableMixin, BaseModel):
    """
    Fórmula de cálculo del precio final por tipo de reparación + subcategoría.
    Estructura: precio_final = precio_base * multiplicador + incremento.
    Si es_personalizado=True, no hay fórmula y el precio se ingresa manualmente.
    """
    tipo_reparacion = models.ForeignKey(
        TipoReparacion,
        on_delete=models.CASCADE,
        related_name='formulas',
        verbose_name='Tipo de reparación',
    )
    subcategoria = models.ForeignKey(
        SubcategoriaDispositivo,
        on_delete=models.CASCADE,
        related_name='formulas',
        verbose_name='Subcategoría',
        null=True,
        blank=True,
        help_text='Dejar vacío para aplicar a cualquier subcategoría.',
    )
    es_personalizado = models.BooleanField(
        'Es personalizado',
        default=False,
        help_text='Si está activo, no se aplica fórmula y el precio se ingresa manualmente.',
    )
    multiplicador = models.DecimalField(
        'Multiplicador',
        max_digits=6, decimal_places=2,
        null=True, blank=True,
        help_text='Ejemplo: 2.00 para multiplicar por 2.',
    )
    incremento = models.DecimalField(
        'Incremento',
        max_digits=10, decimal_places=2,
        null=True, blank=True,
        help_text='Cantidad a sumar al resultado. Ejemplo: 400.00',
    )
    activo = models.BooleanField('Activo', default=True)

    class Meta:
        db_table = 'cotizacion_formulas'
        verbose_name = 'Fórmula de reparación'
        verbose_name_plural = 'Fórmulas de reparación'
        ordering = ['tipo_reparacion', 'subcategoria']
        constraints = [
            models.UniqueConstraint(
                fields=['tipo_reparacion', 'subcategoria'],
                name='uq_formula_tipo_subcategoria',
            ),
        ]

    def __str__(self):
        sub = self.subcategoria.nombre if self.subcategoria else 'Todas'
        if self.es_personalizado:
            return f'{self.tipo_reparacion.nombre} → {sub}: Personalizado'
        return f'{self.tipo_reparacion.nombre} → {sub}: {self.expresion}'

    @staticmethod
    def _fmt_decimal(d: Decimal) -> str:
        """Formatea un Decimal sin notación científica y sin ceros sobrantes.
        2.00 → '2', 1.50 → '1.5', 400.00 → '400'.
        """
        s = format(d, 'f')
        if '.' in s:
            s = s.rstrip('0').rstrip('.')
        return s or '0'

    @property
    def expresion(self) -> str:
        """Representación legible de la fórmula. Ej: 'precio*2+400' o 'Personalizado'."""
        if self.es_personalizado:
            return 'Personalizado'
        mult = self.multiplicador or Decimal('1')
        inc = self.incremento or Decimal('0')
        return f'precio*{self._fmt_decimal(mult)}+{self._fmt_decimal(inc)}'

    def calcular(self, precio_base: Decimal) -> Decimal:
        """Aplica la fórmula sobre un precio base. Si es personalizada retorna el mismo precio."""
        if self.es_personalizado:
            return Decimal(precio_base)
        mult = self.multiplicador or Decimal('1')
        inc = self.incremento or Decimal('0')
        return (Decimal(precio_base) * mult) + inc


class Cotizacion(AuditableMixin, BaseModel):
    """Cotización para un cliente. Acumula uno o más items hasta imprimir."""
    ESTADO_CHOICES = [
        ('borrador', 'Borrador'),
        ('finalizada', 'Finalizada'),
        ('cancelada', 'Cancelada'),
    ]

    numero_cotizacion = models.CharField(
        'Número de cotización', max_length=25, unique=True, blank=True,
    )
    cliente = models.ForeignKey(
        'clientes.Cliente',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='cotizaciones',
        verbose_name='Cliente registrado',
        help_text='Cliente existente del sistema. Opcional si es cliente nuevo.',
    )
    nombre_cliente = models.CharField(
        'Nombre del cliente',
        max_length=150,
        help_text='Nombre tal como aparecerá en la cotización (cliente nuevo o existente).',
    )
    estado = models.CharField(
        'Estado', max_length=20, choices=ESTADO_CHOICES, default='borrador',
    )
    notas = models.TextField('Notas', blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='cotizaciones_creadas',
        verbose_name='Generada por',
    )

    class Meta:
        db_table = 'cotizaciones'
        verbose_name = 'Cotización'
        verbose_name_plural = 'Cotizaciones'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['estado'], name='idx_cotizaciones_estado'),
            models.Index(fields=['created_at'], name='idx_cotizaciones_created'),
            models.Index(fields=['numero_cotizacion'], name='idx_cotizaciones_numero'),
        ]

    def __str__(self):
        return f'{self.numero_cotizacion} — {self.nombre_cliente}'

    def save(self, *args, **kwargs):
        if not self.numero_cotizacion:
            from core.utils import generate_quote_number
            self.numero_cotizacion = generate_quote_number()
        super().save(*args, **kwargs)

    @property
    def total(self) -> Decimal:
        """Suma de todos los precios finales de los items."""
        return sum((item.precio_final for item in self.items.all()), Decimal('0'))


class FuenteApi(AuditableMixin, BaseModel):
    """
    Catálogo de fuentes externas de productos (APIs proveedoras).
    Permite agregar nuevas APIs desde admin sin tocar código:
    solo se debe registrar la fuente con su tipo_parser correspondiente.
    """
    PARSER_CHOICES = [
        ('shopify_v1', 'Shopify v1 (products.json paginado)'),
        ('athome_v1', 'AtHome v1 (archivos JSON locales)'),
        ('athome_web', 'AtHome web (scraping JSON-LD en vivo)'),
    ]

    slug = models.SlugField('Slug', max_length=50, unique=True, blank=True, help_text='Identificador interno único (ej: fixoem). Se auto-genera del nombre si va vacío.')
    nombre = models.CharField('Nombre', max_length=100, help_text='Nombre visible (ej: FixOEM).')
    base_url = models.CharField('URL / ruta base', max_length=500, help_text='URL raíz (Shopify), ruta al directorio de archivos JSON (athome_v1) o URL del catálogo HTML (athome_web). Ej: https://fixoem.com, data/athome, https://www.athomemx.mx/productos')
    tipo_parser = models.CharField(
        'Tipo de parser', max_length=20, choices=PARSER_CHOICES, default='shopify_v1',
        help_text='Estrategia para descargar/parsear productos.',
    )
    activo = models.BooleanField('Activa', default=True)
    orden = models.PositiveIntegerField('Orden', default=0)
    notas = models.TextField('Notas', blank=True)

    class Meta:
        db_table = 'cotizacion_fuentes_api'
        verbose_name = 'Fuente de API'
        verbose_name_plural = 'Fuentes de API'
        ordering = ['orden', 'nombre']

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = _unique_slug(FuenteApi, self.nombre, instance=self)
        super().save(*args, **kwargs)


class CotizacionItem(AuditableMixin, BaseModel):
    """Línea de cotización. Cada concepto cotizado (display, batería, etc)."""

    cotizacion = models.ForeignKey(
        Cotizacion,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Cotización',
    )
    tipo_reparacion = models.ForeignKey(
        TipoReparacion,
        on_delete=models.PROTECT,
        related_name='items_cotizacion',
        verbose_name='Tipo de reparación',
    )
    subcategoria = models.ForeignKey(
        SubcategoriaDispositivo,
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='items_cotizacion',
        verbose_name='Subcategoría',
    )
    es_manual = models.BooleanField(
        'Es manual', default=False,
        help_text='True si el precio se obtuvo manualmente (no de una API).',
    )
    fuente_api = models.ForeignKey(
        FuenteApi,
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='items_cotizacion',
        verbose_name='Fuente API',
        help_text='Fuente externa de la que vino el precio. Null si es_manual=True.',
    )
    producto_titulo = models.CharField(
        'Producto',
        max_length=300,
        help_text='Título del producto en la API o descripción manual.',
    )
    precio_base = models.DecimalField(
        'Precio base',
        max_digits=10, decimal_places=2,
        help_text='Precio sin fórmula aplicada (de la API o ingresado manualmente).',
    )
    precio_final = models.DecimalField(
        'Precio final',
        max_digits=10, decimal_places=2,
        help_text='Precio con la fórmula aplicada (o ingresado manualmente si es personalizado).',
    )
    formula_snapshot = models.CharField(
        'Fórmula aplicada (snapshot)',
        max_length=80,
        blank=True,
        help_text='Texto de la fórmula al momento de generar el item. Ej: precio*2+400',
    )
    es_personalizado = models.BooleanField(
        'Fue personalizado', default=False,
        help_text='True si el precio se ingresó manualmente (sin fórmula).',
    )
    link_referencia = models.URLField(
        'Link de referencia', max_length=500, blank=True,
        help_text='URL opcional (de dónde se obtiene la pieza). Solo visible en PDF empresa.',
    )
    disponible = models.BooleanField(
        'Disponible', default=True,
        help_text='Disponibilidad del producto (de la API "available") al momento de cotizar.',
    )
    cantidad = models.PositiveIntegerField('Cantidad', default=1)
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='cotizacion_items_agregados',
        verbose_name='Agregado por',
    )

    class Meta:
        db_table = 'cotizacion_items'
        verbose_name = 'Item de cotización'
        verbose_name_plural = 'Items de cotización'
        ordering = ['created_at']

    def __str__(self):
        return f'{self.producto_titulo} — ${self.precio_final}'


class ApiProductoCatalogo(BaseModel):
    """
    Caché local de productos extraídos de las APIs externas (FixOEM, SupraTec, etc).
    Se actualiza por el management command sync_productos_api (idealmente 1 vez al día).
    Esta tabla NO es auditable (es caché, no datos de negocio).
    """
    fuente = models.ForeignKey(
        FuenteApi,
        on_delete=models.CASCADE,
        related_name='productos',
        verbose_name='Fuente',
    )
    producto_id_externo = models.CharField('ID / SKU externo', max_length=100)
    titulo = models.CharField('Título', max_length=500)
    precio = models.DecimalField('Precio', max_digits=10, decimal_places=2)
    disponible = models.BooleanField('Disponible', default=False)
    handle = models.CharField('Handle', max_length=300, blank=True)
    vendor = models.CharField('Vendor', max_length=200, blank=True)
    product_type = models.CharField('Tipo de producto', max_length=200, blank=True)
    url_producto = models.URLField('URL del producto', max_length=500, blank=True)
    synced_at = models.DateTimeField('Sincronizado en', auto_now=True)

    class Meta:
        db_table = 'api_productos_catalogo'
        verbose_name = 'Producto API (catálogo)'
        verbose_name_plural = 'Productos API (catálogo)'
        ordering = ['titulo']
        constraints = [
            models.UniqueConstraint(
                fields=['fuente', 'producto_id_externo'],
                name='uq_apiproducto_fuente_externo',
            ),
        ]
        indexes = [
            models.Index(fields=['fuente'], name='idx_apiproducto_fuente'),
            models.Index(fields=['disponible'], name='idx_apiproducto_disponible'),
            models.Index(fields=['titulo'], name='idx_apiproducto_titulo'),
            models.Index(fields=['fuente', 'disponible'], name='idx_apiproducto_fuente_disp'),
        ]

    def __str__(self):
        return f'[{self.fuente.nombre}] {self.titulo}'
