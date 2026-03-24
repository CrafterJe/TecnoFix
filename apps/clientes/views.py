from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from core.permissions import IsAdmin, IsAdminOrReadOnly

from .models import Cliente, Dispositivo
from .serializers import (
    ClienteListSerializer,
    ClienteSerializer,
    DispositivoCreateSerializer,
    DispositivoSerializer,
)


class ClienteViewSet(ModelViewSet):
    queryset = Cliente.objects.prefetch_related('dispositivos').order_by('nombre')
    search_fields = ['nombre', 'telefono', 'email']
    ordering_fields = ['nombre', 'created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return ClienteListSerializer
        if self.action in ('create', 'update', 'partial_update'):
            return ClienteSerializer
        return ClienteSerializer

    def get_permissions(self):
        if self.action in ('destroy',):
            return [IsAdmin()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class DispositivoViewSet(ModelViewSet):
    queryset = Dispositivo.objects.select_related('cliente').order_by('marca', 'modelo')
    search_fields = ['marca', 'modelo', 'cliente__nombre']
    ordering_fields = ['marca', 'modelo', 'tipo', 'created_at']

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return DispositivoCreateSerializer
        return DispositivoSerializer

    def get_permissions(self):
        if self.action == 'destroy':
            return [IsAdmin()]
        return [IsAuthenticated()]
