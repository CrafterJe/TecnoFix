import logging
from decimal import Decimal

from django.db import transaction
from django.db.models import Max
from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from core.middleware import get_current_ip, get_current_user
from core.permissions import IsAdmin, IsAdminOrReadOnly

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
from .pdf import generar_pdf_cliente, generar_pdf_empresa
from .serializers import (
    AgregarItemSerializer,
    ApiProductoCatalogoSerializer,
    CambiarEstadoCotizacionSerializer,
    CategoriaDispositivoSerializer,
    CotizacionCreateSerializer,
    CotizacionItemSerializer,
    CotizacionListSerializer,
    CotizacionSerializer,
    FormulaReparacionSerializer,
    FuenteApiSerializer,
    ReorderConCategoriaSerializer,
    ReorderSerializer,
    SubcategoriaDispositivoSerializer,
    TipoReparacionSerializer,
)


def _log_reorder(entity_name: str, scope: dict, ids_ordenados: list[int]) -> None:
    """Registra un solo AuditLog para una operación de reorder (en vez de N entradas)."""
    try:
        from apps.auditoria.models import AuditLog

        AuditLog.objects.create(
            user=get_current_user(),
            action='UPDATE',
            entity=entity_name,
            entity_id=None,
            old_value={'op': 'reorder', **scope},
            new_value={'ids_ordenados': ids_ordenados},
            ip_address=get_current_ip() or '',
        )
    except Exception as exc:
        logger.error(f'Error al crear AuditLog reorder ({entity_name}): {exc}')

logger = logging.getLogger('apps.cotizaciones')


# ─────────────────────────────────────────────
#  Configuración (admin)
# ─────────────────────────────────────────────

class CategoriaDispositivoViewSet(ModelViewSet):
    queryset = (
        CategoriaDispositivo.objects
        .prefetch_related('subcategorias')
        .order_by('orden', 'nombre')
    )
    serializer_class = CategoriaDispositivoSerializer
    permission_classes = [IsAdminOrReadOnly]
    search_fields = ['nombre', 'slug']
    ordering_fields = ['orden', 'nombre', 'created_at']

    def perform_create(self, serializer):
        # Auto-asignar orden = max + 1 si no se envió un valor explícito
        if not serializer.validated_data.get('orden'):
            max_orden = CategoriaDispositivo.objects.aggregate(m=Max('orden'))['m'] or 0
            serializer.save(orden=max_orden + 1)
        else:
            serializer.save()

    @action(
        detail=False, methods=['post'], url_path='reorder',
        permission_classes=[IsAdmin],
        serializer_class=ReorderSerializer,
    )
    def reorder(self, request):
        """
        Reordena categorías masivamente. Body: `{"ids": [3, 1, 2]}` → el front
        envía los IDs en el orden deseado y el back asigna `orden = index + 1`.
        Atómico: si algún ID no existe, no se aplica ningún cambio.
        """
        serializer = ReorderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ids = serializer.validated_data['ids']

        with transaction.atomic():
            categorias = {c.id: c for c in CategoriaDispositivo.objects.filter(pk__in=ids)}
            faltantes = [i for i in ids if i not in categorias]
            if faltantes:
                return Response(
                    {'detail': f'IDs inexistentes: {faltantes}.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            to_update = []
            for index, cat_id in enumerate(ids, start=1):
                cat = categorias[cat_id]
                cat.orden = index
                to_update.append(cat)
            CategoriaDispositivo.objects.bulk_update(to_update, ['orden'])

            _log_reorder('CategoriaDispositivo', {}, ids)

        logger.info(
            f'Reorder de categorías por {request.user.email}: {ids}'
        )

        qs = self.get_queryset().filter(pk__in=ids)
        return Response(
            CategoriaDispositivoSerializer(qs, many=True, context={'request': request}).data,
        )


class SubcategoriaDispositivoViewSet(ModelViewSet):
    queryset = (
        SubcategoriaDispositivo.objects
        .select_related('categoria')
        .order_by('categoria', 'orden', 'nombre')
    )
    serializer_class = SubcategoriaDispositivoSerializer
    permission_classes = [IsAdminOrReadOnly]
    search_fields = ['nombre', 'slug', 'categoria__nombre']
    ordering_fields = ['orden', 'nombre']
    filterset_fields = ['categoria', 'activo']

    def get_queryset(self):
        qs = super().get_queryset()
        categoria_id = self.request.query_params.get('categoria')
        if categoria_id:
            qs = qs.filter(categoria_id=categoria_id)
        return qs

    def perform_create(self, serializer):
        # Auto-asignar orden = max + 1 dentro de la misma categoría
        if not serializer.validated_data.get('orden'):
            categoria = serializer.validated_data.get('categoria')
            max_orden = SubcategoriaDispositivo.objects.filter(
                categoria=categoria,
            ).aggregate(m=Max('orden'))['m'] or 0
            serializer.save(orden=max_orden + 1)
        else:
            serializer.save()

    @action(
        detail=False, methods=['post'], url_path='reorder',
        permission_classes=[IsAdmin],
        serializer_class=ReorderConCategoriaSerializer,
    )
    def reorder(self, request):
        """
        Reordena subcategorías dentro de una categoría.
        Body: `{"categoria_id": 5, "ids": [10, 8, 12]}`.
        Valida que todos los IDs pertenezcan a esa categoría.
        """
        serializer = ReorderConCategoriaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ids = serializer.validated_data['ids']
        categoria_id = serializer.validated_data['categoria_id']

        if not CategoriaDispositivo.objects.filter(pk=categoria_id).exists():
            return Response(
                {'detail': 'La categoría indicada no existe.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            subs = {
                s.id: s
                for s in SubcategoriaDispositivo.objects.filter(
                    pk__in=ids, categoria_id=categoria_id,
                )
            }
            faltantes = [i for i in ids if i not in subs]
            if faltantes:
                return Response(
                    {
                        'detail': (
                            f'IDs inexistentes o que no pertenecen a la categoría '
                            f'{categoria_id}: {faltantes}.'
                        ),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            to_update = []
            for index, sub_id in enumerate(ids, start=1):
                sub = subs[sub_id]
                sub.orden = index
                to_update.append(sub)
            SubcategoriaDispositivo.objects.bulk_update(to_update, ['orden'])

            _log_reorder(
                'SubcategoriaDispositivo',
                {'categoria_id': categoria_id},
                ids,
            )

        logger.info(
            f'Reorder de subcategorías (categoría={categoria_id}) '
            f'por {request.user.email}: {ids}'
        )

        qs = (
            SubcategoriaDispositivo.objects
            .filter(pk__in=ids, categoria_id=categoria_id)
            .select_related('categoria')
            .order_by('orden', 'nombre')
        )
        return Response(
            SubcategoriaDispositivoSerializer(qs, many=True, context={'request': request}).data,
        )


class TipoReparacionViewSet(ModelViewSet):
    queryset = (
        TipoReparacion.objects
        .select_related('categoria')
        .prefetch_related('formulas__subcategoria')
        .order_by('categoria', 'orden', 'nombre')
    )
    serializer_class = TipoReparacionSerializer
    permission_classes = [IsAdminOrReadOnly]
    search_fields = ['nombre', 'descripcion', 'categoria__nombre']
    ordering_fields = ['orden', 'nombre', 'created_at']
    filterset_fields = ['categoria', 'activo']

    def get_queryset(self):
        qs = super().get_queryset()
        categoria_id = self.request.query_params.get('categoria')
        if categoria_id:
            qs = qs.filter(categoria_id=categoria_id)
        return qs

    def perform_create(self, serializer):
        # Auto-asignar orden = max + 1 dentro de la misma categoría
        if not serializer.validated_data.get('orden'):
            categoria = serializer.validated_data.get('categoria')
            max_orden = TipoReparacion.objects.filter(
                categoria=categoria,
            ).aggregate(m=Max('orden'))['m'] or 0
            serializer.save(orden=max_orden + 1)
        else:
            serializer.save()

    @action(
        detail=False, methods=['post'], url_path='reorder',
        permission_classes=[IsAdmin],
        serializer_class=ReorderConCategoriaSerializer,
    )
    def reorder(self, request):
        """
        Reordena tipos de reparación dentro de una categoría.
        Body: `{"categoria_id": 5, "ids": [10, 8, 12]}`.
        """
        serializer = ReorderConCategoriaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ids = serializer.validated_data['ids']
        categoria_id = serializer.validated_data['categoria_id']

        if not CategoriaDispositivo.objects.filter(pk=categoria_id).exists():
            return Response(
                {'detail': 'La categoría indicada no existe.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            tipos = {
                t.id: t
                for t in TipoReparacion.objects.filter(
                    pk__in=ids, categoria_id=categoria_id,
                )
            }
            faltantes = [i for i in ids if i not in tipos]
            if faltantes:
                return Response(
                    {
                        'detail': (
                            f'IDs inexistentes o que no pertenecen a la categoría '
                            f'{categoria_id}: {faltantes}.'
                        ),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            to_update = []
            for index, tipo_id in enumerate(ids, start=1):
                tipo = tipos[tipo_id]
                tipo.orden = index
                to_update.append(tipo)
            TipoReparacion.objects.bulk_update(to_update, ['orden'])

            _log_reorder(
                'TipoReparacion',
                {'categoria_id': categoria_id},
                ids,
            )

        logger.info(
            f'Reorder de tipos de reparación (categoría={categoria_id}) '
            f'por {request.user.email}: {ids}'
        )

        qs = (
            TipoReparacion.objects
            .filter(pk__in=ids, categoria_id=categoria_id)
            .select_related('categoria')
            .prefetch_related('formulas__subcategoria')
            .order_by('orden', 'nombre')
        )
        return Response(
            TipoReparacionSerializer(qs, many=True, context={'request': request}).data,
        )


class FormulaReparacionViewSet(ModelViewSet):
    queryset = (
        FormulaReparacion.objects
        .select_related('tipo_reparacion__categoria', 'subcategoria')
        .order_by('tipo_reparacion', 'subcategoria')
    )
    serializer_class = FormulaReparacionSerializer
    permission_classes = [IsAdminOrReadOnly]
    search_fields = ['tipo_reparacion__nombre', 'subcategoria__nombre']
    filterset_fields = ['tipo_reparacion', 'subcategoria', 'es_personalizado', 'activo']

    @action(detail=False, methods=['get'], url_path='disponibles')
    def disponibles(self, request):
        """
        Devuelve fórmulas únicas por expresión (mismas (multiplicador, incremento, es_personalizado)
        se devuelven una sola vez). Útil para que el frontend muestre un dropdown sin duplicados.

        Cada item incluye un `formula_id` representativo que puede usarse en POST /items/.
        """
        qs = FormulaReparacion.objects.filter(activo=True).order_by(
            'es_personalizado', 'multiplicador', 'incremento', 'id',
        )

        vistas = {}
        for f in qs:
            clave = (f.es_personalizado, f.multiplicador, f.incremento)
            if clave in vistas:
                continue
            vistas[clave] = {
                'formula_id': f.id,
                'expresion': f.expresion,
                'es_personalizado': f.es_personalizado,
                'multiplicador': str(f.multiplicador) if f.multiplicador is not None else None,
                'incremento': str(f.incremento) if f.incremento is not None else None,
            }
        return Response(list(vistas.values()))


class FuenteApiViewSet(ModelViewSet):
    """
    Fuentes externas de productos (APIs proveedoras).
    Solo admin puede crear/editar/eliminar. Cualquier autenticado puede leer.
    """
    queryset = FuenteApi.objects.all().order_by('orden', 'nombre')
    serializer_class = FuenteApiSerializer
    permission_classes = [IsAdminOrReadOnly]
    search_fields = ['nombre', 'slug', 'base_url']
    ordering_fields = ['orden', 'nombre', 'created_at']
    filterset_fields = ['activo', 'tipo_parser']


# ─────────────────────────────────────────────
#  Catálogo de productos (caché de APIs)
# ─────────────────────────────────────────────

class ApiProductoCatalogoViewSet(ReadOnlyModelViewSet):
    """Catálogo de productos sincronizados desde las APIs externas."""
    queryset = ApiProductoCatalogo.objects.select_related('fuente').order_by('titulo')
    serializer_class = ApiProductoCatalogoSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ['titulo', 'handle', 'vendor', 'product_type']
    ordering_fields = ['titulo', 'precio', 'synced_at']
    filterset_fields = ['fuente', 'disponible']

    def get_queryset(self):
        qs = super().get_queryset()
        # Filtro por slug o ID de fuente. Acepta ?fuente=fixoem o ?fuente=1
        fuente = self.request.query_params.get('fuente')
        if fuente:
            if fuente.isdigit():
                qs = qs.filter(fuente_id=int(fuente))
            else:
                qs = qs.filter(fuente__slug=fuente)
        disponible = self.request.query_params.get('disponible')
        if disponible is not None:
            qs = qs.filter(disponible=disponible.lower() in ('true', '1', 'yes'))
        q = self.request.query_params.get('q')
        if q:
            tokens = [t for t in q.split() if t.strip()]
            for token in tokens:
                qs = qs.filter(titulo__icontains=token)
        return qs


class FuenteApiViewSet(ModelViewSet):
    """CRUD de fuentes externas de productos. Solo admin para escritura."""
    queryset = FuenteApi.objects.all().order_by('orden', 'nombre')
    serializer_class = FuenteApiSerializer
    permission_classes = [IsAdminOrReadOnly]
    search_fields = ['nombre', 'slug']
    ordering_fields = ['orden', 'nombre', 'created_at']
    filterset_fields = ['activo', 'tipo_parser']

    def perform_create(self, serializer):
        if not serializer.validated_data.get('orden'):
            max_orden = FuenteApi.objects.aggregate(m=Max('orden'))['m'] or 0
            serializer.save(orden=max_orden + 1)
        else:
            serializer.save()


# ─────────────────────────────────────────────
#  Cotizaciones
# ─────────────────────────────────────────────

class CotizacionViewSet(ModelViewSet):
    queryset = (
        Cotizacion.objects
        .select_related('cliente', 'created_by')
        .prefetch_related(
            'items__tipo_reparacion',
            'items__subcategoria',
            'items__added_by',
        )
        .order_by('-created_at')
    )
    search_fields = ['numero_cotizacion', 'nombre_cliente', 'cliente__nombre']
    ordering_fields = ['created_at', 'numero_cotizacion', 'estado']
    filterset_fields = ['estado', 'created_by']

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        anio = params.get('anio')
        mes = params.get('mes')
        if anio:
            try:
                qs = qs.filter(created_at__year=int(anio))
            except ValueError:
                pass
        if mes:
            try:
                qs = qs.filter(created_at__month=int(mes))
            except ValueError:
                pass
        return qs

    def get_serializer_class(self):
        if self.action == 'list':
            return CotizacionListSerializer
        if self.action == 'create':
            return CotizacionCreateSerializer
        if self.action == 'agregar_item':
            return AgregarItemSerializer
        if self.action == 'cambiar_estado':
            return CambiarEstadoCotizacionSerializer
        return CotizacionSerializer

    def get_permissions(self):
        if self.action == 'destroy':
            return [IsAdmin()]
        return [IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        serializer = CotizacionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save(created_by=request.user)
        logger.info(
            f'Cotización creada por {request.user.email} '
            f'para "{instance.nombre_cliente}"'
        )
        response_data = CotizacionSerializer(instance, context={'request': request}).data
        return Response(response_data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='items')
    def agregar_item(self, request, pk=None):
        cotizacion = self.get_object()

        if cotizacion.estado != 'borrador':
            return Response(
                {'detail': 'Solo se pueden agregar items a cotizaciones en borrador.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = AgregarItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        formula = data.get('_formula')
        usar_formula = data.get('_usar_formula', False)
        tipo = serializer.context.get('tipo_reparacion')
        sub = serializer.context.get('subcategoria')

        precio_base = data['precio_base']
        precio_final_manual = data.get('precio_final_manual')

        if not usar_formula or formula is None:
            # Sin fórmula → precio_final = precio_base (a menos que se envíe override manual)
            if precio_final_manual is not None:
                precio_final = Decimal(precio_final_manual)
            else:
                precio_final = Decimal(precio_base)
            formula_snapshot = 'Sin fórmula'
            es_personalizado = False
        elif formula.es_personalizado:
            precio_final = Decimal(precio_final_manual)
            formula_snapshot = formula.expresion
            es_personalizado = True
        else:
            precio_final = formula.calcular(precio_base)
            formula_snapshot = formula.expresion
            es_personalizado = False

        es_manual = data.get('es_manual', False)
        fuente_api = serializer.context.get('fuente_api') if not es_manual else None

        item = CotizacionItem.objects.create(
            cotizacion=cotizacion,
            tipo_reparacion=tipo,
            subcategoria=sub,
            es_manual=es_manual,
            fuente_api=fuente_api,
            producto_titulo=data['producto_titulo'],
            precio_base=precio_base,
            precio_final=precio_final,
            formula_snapshot=formula_snapshot,
            es_personalizado=es_personalizado,
            link_referencia=data.get('link_referencia', ''),
            disponible=data.get('disponible', True),
            cantidad=data.get('cantidad', 1),
            added_by=request.user,
        )

        logger.info(
            f'Item agregado a {cotizacion.numero_cotizacion}: '
            f'{tipo.nombre} | base=${precio_base} → final=${precio_final}'
        )

        return Response(
            CotizacionItemSerializer(item).data,
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True, methods=['delete'],
        url_path=r'items/(?P<item_id>\d+)',
    )
    def eliminar_item(self, request, pk=None, item_id=None):
        cotizacion = self.get_object()

        if cotizacion.estado != 'borrador':
            return Response(
                {'detail': 'Solo se pueden quitar items de cotizaciones en borrador.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            item = cotizacion.items.get(pk=item_id)
        except CotizacionItem.DoesNotExist:
            return Response(
                {'detail': 'Item no encontrado en esta cotización.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        producto = item.producto_titulo
        item.delete()

        logger.info(
            f'Item removido de {cotizacion.numero_cotizacion}: {producto} '
            f'por {request.user.email}'
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], url_path='cambiar-estado')
    def cambiar_estado(self, request, pk=None):
        cotizacion = self.get_object()
        serializer = CambiarEstadoCotizacionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        nuevo = serializer.validated_data['estado']
        anterior = cotizacion.estado
        cotizacion.estado = nuevo
        cotizacion.save()

        logger.info(
            f'Cotización {cotizacion.numero_cotizacion}: '
            f'{anterior} → {nuevo} por {request.user.email}'
        )
        return Response({
            'detail': f'Estado actualizado a "{cotizacion.get_estado_display()}".',
            'estado_anterior': anterior,
            'estado_nuevo': nuevo,
        })

    @action(detail=True, methods=['get'], url_path='pdf-cliente')
    def pdf_cliente(self, request, pk=None):
        cotizacion = self.get_object()
        buffer = generar_pdf_cliente(cotizacion)
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = (
            f'inline; filename="cotizacion_{cotizacion.numero_cotizacion}_cliente.pdf"'
        )
        return response

    @action(detail=True, methods=['get'], url_path='pdf-empresa')
    def pdf_empresa(self, request, pk=None):
        cotizacion = self.get_object()
        buffer = generar_pdf_empresa(cotizacion)
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = (
            f'inline; filename="cotizacion_{cotizacion.numero_cotizacion}_empresa.pdf"'
        )
        return response


# ─────────────────────────────────────────────
#  Resolver de fórmula (helper público)
# ─────────────────────────────────────────────

class ResolverFormulaView(ReadOnlyModelViewSet):
    """
    Endpoint utilitario que recibe tipo_reparacion + subcategoria + precio_base
    y devuelve el precio final calculado SIN crear nada. Útil para preview en UI.
    """
    queryset = FormulaReparacion.objects.none()
    serializer_class = FormulaReparacionSerializer
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        tipo_id = request.query_params.get('tipo_reparacion')
        sub_id = request.query_params.get('subcategoria')
        precio_base = request.query_params.get('precio_base')

        if not tipo_id or precio_base is None:
            return Response(
                {'detail': 'Parámetros requeridos: tipo_reparacion, precio_base.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            precio_base = Decimal(precio_base)
        except (ValueError, ArithmeticError):
            return Response(
                {'detail': 'precio_base debe ser un número válido.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            tipo = TipoReparacion.objects.get(pk=tipo_id, activo=True)
        except TipoReparacion.DoesNotExist:
            return Response(
                {'detail': 'Tipo de reparación no encontrado.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        sub = None
        if sub_id:
            try:
                sub = SubcategoriaDispositivo.objects.get(pk=sub_id, activo=True)
            except SubcategoriaDispositivo.DoesNotExist:
                return Response(
                    {'detail': 'Subcategoría no encontrada.'},
                    status=status.HTTP_404_NOT_FOUND,
                )

        formula = AgregarItemSerializer._resolver_formula(tipo, sub)

        if formula is None:
            return Response({
                'tiene_formula': False,
                'es_personalizado': True,
                'expresion': 'Sin fórmula',
                'precio_base': str(precio_base),
                'precio_final': None,
                'mensaje': 'No hay fórmula aplicable. Debe ingresarse el precio manualmente.',
            })

        if formula.es_personalizado:
            return Response({
                'tiene_formula': True,
                'es_personalizado': True,
                'expresion': formula.expresion,
                'precio_base': str(precio_base),
                'precio_final': None,
                'mensaje': 'Fórmula personalizada. Debe ingresarse el precio manualmente.',
            })

        precio_final = formula.calcular(precio_base)
        return Response({
            'tiene_formula': True,
            'es_personalizado': False,
            'expresion': formula.expresion,
            'precio_base': str(precio_base),
            'precio_final': str(precio_final),
            'mensaje': 'Fórmula aplicada correctamente.',
        })
