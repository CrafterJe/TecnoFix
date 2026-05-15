from decimal import Decimal

from rest_framework import serializers

from .models import (
    ApiProductoCatalogo,
    CategoriaDispositivo,
    Cotizacion,
    CotizacionItem,
    FormulaReparacion,
    FuenteApi,
    SubcategoriaDispositivo,
    TipoReparacion,
)


# ─────────────────────────────────────────────
#  Configuración (admin)
# ─────────────────────────────────────────────

class SubcategoriaDispositivoSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)
    slug = serializers.SlugField(max_length=80, required=False, allow_blank=True)

    class Meta:
        model = SubcategoriaDispositivo
        fields = [
            'id', 'categoria', 'categoria_nombre',
            'nombre', 'slug', 'activo', 'orden',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        # El UniqueConstraint (categoria, slug) genera un UniqueTogetherValidator que
        # exige slug en el payload. La unicidad se garantiza por el constraint de BD
        # + la lógica de save() del modelo (que auto-genera slug único).
        validators = []


class CategoriaDispositivoSerializer(serializers.ModelSerializer):
    subcategorias = SubcategoriaDispositivoSerializer(many=True, read_only=True)
    total_tipos_reparacion = serializers.IntegerField(
        source='tipos_reparacion.count', read_only=True,
    )
    slug = serializers.SlugField(max_length=80, required=False, allow_blank=True)

    class Meta:
        model = CategoriaDispositivo
        fields = [
            'id', 'nombre', 'slug', 'activo', 'orden',
            'subcategorias', 'total_tipos_reparacion',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class FormulaReparacionSerializer(serializers.ModelSerializer):
    expresion = serializers.CharField(read_only=True)
    tipo_reparacion_nombre = serializers.CharField(
        source='tipo_reparacion.nombre', read_only=True,
    )
    subcategoria_nombre = serializers.CharField(
        source='subcategoria.nombre', read_only=True, default=None,
    )

    class Meta:
        model = FormulaReparacion
        fields = [
            'id',
            'tipo_reparacion', 'tipo_reparacion_nombre',
            'subcategoria', 'subcategoria_nombre',
            'es_personalizado', 'multiplicador', 'incremento',
            'expresion', 'activo',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate(self, attrs):
        es_personalizado = attrs.get(
            'es_personalizado',
            getattr(self.instance, 'es_personalizado', False),
        )
        multiplicador = attrs.get(
            'multiplicador',
            getattr(self.instance, 'multiplicador', None),
        )
        incremento = attrs.get(
            'incremento',
            getattr(self.instance, 'incremento', None),
        )

        if es_personalizado:
            if multiplicador is not None or incremento is not None:
                raise serializers.ValidationError(
                    'Si es personalizado, multiplicador e incremento deben ser nulos.'
                )
        else:
            if multiplicador is None or incremento is None:
                raise serializers.ValidationError(
                    'Si no es personalizado, debes indicar multiplicador e incremento.'
                )
            if multiplicador <= 0:
                raise serializers.ValidationError(
                    'El multiplicador debe ser mayor a 0.'
                )
        return attrs


class TipoReparacionSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)
    formulas = FormulaReparacionSerializer(many=True, read_only=True)

    class Meta:
        model = TipoReparacion
        fields = [
            'id', 'categoria', 'categoria_nombre',
            'nombre', 'descripcion', 'activo', 'orden',
            'formulas',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


# ─────────────────────────────────────────────
#  Fuentes de API (catálogo de APIs externas)
# ─────────────────────────────────────────────

class FuenteApiSerializer(serializers.ModelSerializer):
    slug = serializers.SlugField(max_length=50, required=False, allow_blank=True)

    class Meta:
        model = FuenteApi
        fields = [
            'id', 'slug', 'nombre', 'base_url', 'tipo_parser',
            'activo', 'orden', 'notas',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class FuenteApiResumenSerializer(serializers.ModelSerializer):
    """Versión compacta para anidar en otros serializers."""
    class Meta:
        model = FuenteApi
        fields = ['id', 'slug', 'nombre']


# ─────────────────────────────────────────────
#  Búsqueda de productos en caché de APIs
# ─────────────────────────────────────────────

class ApiProductoCatalogoSerializer(serializers.ModelSerializer):
    fuente = FuenteApiResumenSerializer(read_only=True)

    class Meta:
        model = ApiProductoCatalogo
        fields = [
            'id', 'fuente',
            'producto_id_externo', 'titulo', 'precio',
            'disponible', 'handle', 'vendor', 'product_type',
            'synced_at',
        ]


# ─────────────────────────────────────────────
#  Cotizaciones e items
# ─────────────────────────────────────────────

class CotizacionItemSerializer(serializers.ModelSerializer):
    fuente_api = FuenteApiResumenSerializer(read_only=True)
    tipo_reparacion_nombre = serializers.CharField(
        source='tipo_reparacion.nombre', read_only=True,
    )
    subcategoria_nombre = serializers.CharField(
        source='subcategoria.nombre', read_only=True, default=None,
    )
    added_by_nombre = serializers.CharField(
        source='added_by.nombre', read_only=True, default=None,
    )
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = CotizacionItem
        fields = [
            'id', 'cotizacion',
            'tipo_reparacion', 'tipo_reparacion_nombre',
            'subcategoria', 'subcategoria_nombre',
            'es_manual', 'fuente_api',
            'producto_titulo', 'precio_base', 'precio_final',
            'formula_snapshot', 'es_personalizado',
            'link_referencia', 'disponible', 'cantidad',
            'subtotal',
            'added_by', 'added_by_nombre',
            'created_at',
        ]
        read_only_fields = [
            'id', 'cotizacion', 'precio_final', 'formula_snapshot',
            'es_personalizado', 'added_by', 'created_at',
        ]

    def get_subtotal(self, obj) -> str:
        return str(obj.precio_final * obj.cantidad)


class AgregarItemSerializer(serializers.Serializer):
    """
    Payload para agregar un item a una cotización.
    El item puede ser manual (es_manual=True, sin fuente_api) o desde una API (es_manual=False + fuente_api_id).

    Resolución de fórmula (en este orden):
      1. Si se envía `formula_id` (int) → se aplica esa fórmula explícitamente.
      2. Si se envía `formula_id: null` → SIN fórmula, precio_final = precio_base.
      3. Si NO se envía `formula_id` → se auto-resuelve por (tipo, subcategoria) (legacy).

    Cuando la fórmula resultante es personalizada (o no hay), se requiere `precio_final_manual`.
    """
    tipo_reparacion_id = serializers.IntegerField()
    subcategoria_id = serializers.IntegerField(required=False, allow_null=True)
    es_manual = serializers.BooleanField(
        default=False,
        help_text='True = el precio fue ingresado a mano. False = vino de una API (requiere fuente_api_id).',
    )
    fuente_api_id = serializers.IntegerField(
        required=False, allow_null=True,
        help_text='Solo si es_manual=False. Debe corresponder a una FuenteApi activa.',
    )
    formula_id = serializers.IntegerField(
        required=False, allow_null=True,
        help_text='ID de FormulaReparacion a aplicar. null = sin fórmula. Omitir = auto-resolver por tipo+subcategoria (legacy).',
    )
    producto_titulo = serializers.CharField(max_length=300)
    precio_base = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0'))
    precio_final_manual = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True,
        help_text='Requerido si la fórmula resultante es personalizada.',
    )
    link_referencia = serializers.URLField(required=False, allow_blank=True, max_length=500)
    disponible = serializers.BooleanField(default=True)
    cantidad = serializers.IntegerField(min_value=1, default=1)

    def validate_tipo_reparacion_id(self, value):
        try:
            tipo = TipoReparacion.objects.get(pk=value, activo=True)
        except TipoReparacion.DoesNotExist:
            raise serializers.ValidationError('Tipo de reparación no encontrado o inactivo.')
        self.context['tipo_reparacion'] = tipo
        return value

    def validate_subcategoria_id(self, value):
        if value is None:
            return value
        try:
            sub = SubcategoriaDispositivo.objects.get(pk=value, activo=True)
        except SubcategoriaDispositivo.DoesNotExist:
            raise serializers.ValidationError('Subcategoría no encontrada o inactiva.')
        self.context['subcategoria'] = sub
        return value

    def validate_fuente_api_id(self, value):
        if value is None:
            return value
        try:
            fuente = FuenteApi.objects.get(pk=value, activo=True)
        except FuenteApi.DoesNotExist:
            raise serializers.ValidationError('Fuente API no encontrada o inactiva.')
        self.context['fuente_api'] = fuente
        return value

    def validate_formula_id(self, value):
        if value is None:
            return value
        try:
            formula = FormulaReparacion.objects.get(pk=value, activo=True)
        except FormulaReparacion.DoesNotExist:
            raise serializers.ValidationError('Fórmula no encontrada o inactiva.')
        self.context['formula_explicit'] = formula
        return value

    def validate(self, attrs):
        tipo = self.context.get('tipo_reparacion')
        sub = self.context.get('subcategoria')
        es_manual = attrs.get('es_manual', False)
        fuente_api_id = attrs.get('fuente_api_id')

        # Coherencia de origen
        if es_manual and fuente_api_id is not None:
            raise serializers.ValidationError(
                'No se puede ser manual y al mismo tiempo indicar una fuente_api_id.'
            )
        if not es_manual and fuente_api_id is None:
            raise serializers.ValidationError(
                'Debes indicar fuente_api_id o marcar es_manual=true.'
            )

        # Coherencia de categoría/subcategoría
        if tipo and sub and tipo.categoria_id != sub.categoria_id:
            raise serializers.ValidationError(
                'La subcategoría no pertenece a la categoría del tipo de reparación.'
            )

        # Resolución de fórmula
        formula_explicit = self.context.get('formula_explicit')
        formula_id_in_payload = 'formula_id' in self.initial_data

        if formula_explicit:
            # 1) Fórmula explícita (cualquier FormulaReparacion de la BD)
            formula = formula_explicit
            usar_formula = True
        elif formula_id_in_payload:
            # 2) Frontend envió formula_id=null → sin fórmula
            formula = None
            usar_formula = False
        else:
            # 3) Legacy: auto-resolver por tipo+subcategoria
            formula = self._resolver_formula(tipo, sub)
            usar_formula = formula is not None

        attrs['_formula'] = formula
        attrs['_usar_formula'] = usar_formula

        # Si hay fórmula y es personalizada → requiere precio_final_manual
        if usar_formula and formula is not None and formula.es_personalizado:
            if attrs.get('precio_final_manual') is None:
                raise serializers.ValidationError(
                    'La fórmula seleccionada es personalizada. '
                    'Debes indicar precio_final_manual.'
                )

        # Si NO hay fórmula y NO se envió precio_final_manual → precio_final = precio_base
        # (no requiere error)

        return attrs

    @staticmethod
    def _resolver_formula(tipo, subcategoria):
        """
        Busca primero la fórmula específica (tipo + subcategoría),
        si no la encuentra, busca la genérica (tipo + subcategoria=null).
        """
        if tipo is None:
            return None
        qs = FormulaReparacion.objects.filter(tipo_reparacion=tipo, activo=True)
        if subcategoria:
            f = qs.filter(subcategoria=subcategoria).first()
            if f:
                return f
        return qs.filter(subcategoria__isnull=True).first()


# ─────────────────────────────────────────────
#  Cotización
# ─────────────────────────────────────────────

class CotizacionListSerializer(serializers.ModelSerializer):
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    created_by_nombre = serializers.CharField(source='created_by.nombre', read_only=True)
    total_items = serializers.IntegerField(source='items.count', read_only=True)
    total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Cotizacion
        fields = [
            'id', 'numero_cotizacion', 'nombre_cliente',
            'estado', 'estado_display',
            'created_by', 'created_by_nombre',
            'total_items', 'total',
            'created_at',
        ]


class CotizacionSerializer(serializers.ModelSerializer):
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    created_by_nombre = serializers.CharField(source='created_by.nombre', read_only=True)
    cliente_nombre = serializers.CharField(source='cliente.nombre', read_only=True, default=None)
    items = CotizacionItemSerializer(many=True, read_only=True)
    total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Cotizacion
        fields = [
            'id', 'numero_cotizacion',
            'cliente', 'cliente_nombre', 'nombre_cliente',
            'estado', 'estado_display', 'notas',
            'created_by', 'created_by_nombre',
            'items', 'total',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'numero_cotizacion', 'created_by',
            'created_at', 'updated_at',
        ]


class CotizacionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cotizacion
        fields = ['cliente', 'nombre_cliente', 'notas']

    def validate(self, attrs):
        cliente = attrs.get('cliente')
        nombre = attrs.get('nombre_cliente', '').strip()
        if not nombre and not cliente:
            raise serializers.ValidationError(
                'Debes proveer nombre_cliente o un cliente registrado.'
            )
        if cliente and not nombre:
            attrs['nombre_cliente'] = cliente.nombre
        return attrs


class CambiarEstadoCotizacionSerializer(serializers.Serializer):
    estado = serializers.ChoiceField(choices=Cotizacion.ESTADO_CHOICES)


# ─────────────────────────────────────────────
#  Reorder (drag & drop)
# ─────────────────────────────────────────────

class ReorderSerializer(serializers.Serializer):
    """
    Payload para reordenar una lista de objetos. El front envía los IDs
    en el orden deseado (primero = arriba); el back asigna orden = index + 1.
    """
    ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
        help_text='IDs en el orden deseado. El primero recibe orden=1.',
    )

    def validate_ids(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError('La lista no puede contener IDs duplicados.')
        return value


class ReorderConCategoriaSerializer(ReorderSerializer):
    """Reorder con scope obligatorio por categoría (subcategorías y tipos de reparación)."""
    categoria_id = serializers.IntegerField(
        min_value=1,
        help_text='Categoría dueña de los items a reordenar.',
    )
