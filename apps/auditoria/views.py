from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.viewsets import GenericViewSet

from core.permissions import IsAdmin

from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogViewSet(ListModelMixin, RetrieveModelMixin, GenericViewSet):
    """Solo lectura — exclusivo para administradores."""
    serializer_class = AuditLogSerializer
    permission_classes = [IsAdmin]
    search_fields = ['entity', 'action', 'user__nombre', 'user__email']
    ordering_fields = ['created_at', 'action', 'entity']

    def get_queryset(self):
        qs = AuditLog.objects.select_related('user').order_by('-created_at')
        action = self.request.query_params.get('action')
        entity = self.request.query_params.get('entity')
        if action:
            qs = qs.filter(action=action)
        if entity:
            qs = qs.filter(entity__iexact=entity)
        return qs
