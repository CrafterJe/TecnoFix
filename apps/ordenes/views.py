import logging

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from core.permissions import IsAdmin, IsAdminOrTecnico

from .models import Evidencia, Orden, OrdenRefaccion
from .serializers import (
    AgregarRefaccionSerializer,
    AsignarTecnicoSerializer,
    CambiarEstadoSerializer,
    EvidenciaCreateSerializer,
    EvidenciaSerializer,
    OrdenCreateSerializer,
    OrdenListSerializer,
    OrdenSerializer,
)

logger = logging.getLogger('apps.ordenes')


class OrdenViewSet(ModelViewSet):
    queryset = (
        Orden.objects
        .select_related('dispositivo__cliente', 'assigned_to', 'created_by')
        .prefetch_related('evidencias', 'refacciones_usadas__refaccion')
        .order_by('-created_at')
    )
    search_fields = ['numero_orden', 'dispositivo__cliente__nombre', 'dispositivo__marca']
    ordering_fields = ['created_at', 'estado', 'numero_orden']
    filterset_fields = ['estado', 'assigned_to']

    def get_serializer_class(self):
        if self.action == 'list':
            return OrdenListSerializer
        if self.action == 'create':
            return OrdenCreateSerializer
        if self.action == 'asignar_tecnico':
            return AsignarTecnicoSerializer
        if self.action == 'cambiar_estado':
            return CambiarEstadoSerializer
        if self.action == 'agregar_refaccion':
            return AgregarRefaccionSerializer
        return OrdenSerializer

    def get_permissions(self):
        if self.action in ('destroy',):
            return [IsAdmin()]
        if self.action in ('asignar_tecnico', 'agregar_refaccion'):
            return [IsAdmin()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(
            created_by=self.request.user,
            received_by=self.request.user,
        )
        logger.info(f'Orden creada por {self.request.user.email}')

    @action(detail=True, methods=['post'], url_path='asignar-tecnico')
    def asignar_tecnico(self, request, pk=None):
        orden = self.get_object()
        serializer = AsignarTecnicoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from apps.users.models import Usuario
        tecnico = Usuario.objects.get(pk=serializer.validated_data['tecnico_id'])
        orden.assigned_to = tecnico
        orden.save()

        logger.info(f'Orden {orden.numero_orden} asignada a {tecnico.nombre}')
        return Response({'detail': f'Orden asignada a {tecnico.nombre}.'})

    @action(detail=True, methods=['post'], url_path='cambiar-estado')
    def cambiar_estado(self, request, pk=None):
        orden = self.get_object()
        serializer = CambiarEstadoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        estado_anterior = orden.estado
        orden.estado = serializer.validated_data['estado']
        orden.status_updated_by = request.user

        if serializer.validated_data.get('diagnostico'):
            orden.diagnostico = serializer.validated_data['diagnostico']

        if orden.estado == 'entregado':
            orden.delivered_by = request.user

        orden.save()

        logger.info(
            f'Orden {orden.numero_orden}: {estado_anterior} → {orden.estado} '
            f'por {request.user.email}'
        )
        return Response({
            'detail': f'Estado actualizado a "{orden.get_estado_display()}".',
            'estado_anterior': estado_anterior,
            'estado_nuevo': orden.estado,
        })

    @action(detail=True, methods=['post'], url_path='agregar-refaccion')
    def agregar_refaccion(self, request, pk=None):
        orden = self.get_object()
        serializer = AgregarRefaccionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from apps.inventario.models import Refaccion
        refaccion = Refaccion.objects.get(pk=serializer.validated_data['refaccion_id'])
        cantidad = serializer.validated_data['cantidad']

        if refaccion.stock < cantidad:
            return Response(
                {'detail': f'Stock insuficiente. Disponible: {refaccion.stock}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        refaccion.stock -= cantidad
        refaccion.save()

        orden_refaccion = OrdenRefaccion.objects.create(
            orden=orden,
            refaccion=refaccion,
            cantidad=cantidad,
            added_by=request.user,
        )

        return Response({'detail': f'{refaccion.nombre} x{cantidad} agregado a la orden.'})


class EvidenciaViewSet(ModelViewSet):
    queryset = Evidencia.objects.select_related('orden', 'uploaded_by').order_by('-created_at')
    search_fields = ['orden__numero_orden', 'tipo']

    def get_serializer_class(self):
        if self.action == 'create':
            return EvidenciaCreateSerializer
        return EvidenciaSerializer

    def get_permissions(self):
        if self.action == 'destroy':
            return [IsAdmin()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)
