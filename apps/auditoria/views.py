from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.viewsets import GenericViewSet

from core.permissions import IsAdmin

from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogViewSet(ListModelMixin, RetrieveModelMixin, GenericViewSet):
    """Solo lectura — exclusivo para administradores."""
    queryset = AuditLog.objects.select_related('user').order_by('-created_at')
    serializer_class = AuditLogSerializer
    permission_classes = [IsAdmin]
    search_fields = ['entity', 'action', 'user__nombre', 'user__email']
    ordering_fields = ['created_at', 'action', 'entity']
    filterset_fields = ['action', 'entity']
