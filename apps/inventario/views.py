import logging

from django.db import models
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from core.permissions import IsAdmin, IsAdminOrReadOnly, IsAdminOrTecnico

from .models import Refaccion, RefaccionCompatible
from .serializers import (
    AjustarStockSerializer,
    RefaccionCompatibleSerializer,
    RefaccionListSerializer,
    RefaccionSerializer,
)

logger = logging.getLogger('apps.inventario')


class RefaccionViewSet(ModelViewSet):
    queryset = Refaccion.objects.prefetch_related('compatibilidades').order_by('nombre')
    search_fields = ['nombre', 'descripcion', 'categoria']
    ordering_fields = ['nombre', 'stock', 'precio_venta', 'created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return RefaccionListSerializer
        if self.action == 'ajustar_stock':
            return AjustarStockSerializer
        return RefaccionSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated()]
        if self.action == 'ajustar_stock':
            return [IsAdminOrTecnico()]
        return [IsAdmin()]

    @action(detail=True, methods=['post'], url_path='ajustar-stock')
    def ajustar_stock(self, request, pk=None):
        refaccion = self.get_object()
        serializer = AjustarStockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cantidad = serializer.validated_data['cantidad']
        nuevo_stock = refaccion.stock + cantidad

        if nuevo_stock < 0:
            return Response(
                {'detail': f'Stock insuficiente. Stock actual: {refaccion.stock}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        refaccion.stock = nuevo_stock
        refaccion.save()

        logger.info(
            f'Stock ajustado: {refaccion.nombre} | '
            f'{"+" if cantidad > 0 else ""}{cantidad} | '
            f'Nuevo stock: {nuevo_stock} | '
            f'Usuario: {request.user.email}'
        )

        return Response({
            'detail': 'Stock actualizado.',
            'stock_anterior': nuevo_stock - cantidad,
            'stock_nuevo': nuevo_stock,
        })

    @action(detail=False, methods=['get'], url_path='bajo-stock')
    def bajo_stock(self, request):
        """Lista refacciones con stock por debajo del mínimo."""
        qs = self.get_queryset().filter(stock__lte=models.F('stock_minimo'))
        serializer = RefaccionListSerializer(qs, many=True)
        return Response(serializer.data)


class RefaccionCompatibleViewSet(ModelViewSet):
    queryset = RefaccionCompatible.objects.select_related('refaccion').order_by('marca')
    serializer_class = RefaccionCompatibleSerializer
    search_fields = ['marca', 'modelo', 'tipo_dispositivo', 'refaccion__nombre']
    permission_classes = [IsAdminOrReadOnly]
