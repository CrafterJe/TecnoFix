from rest_framework import serializers

from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    user_nombre = serializers.CharField(source='user.nombre', read_only=True, default='Sistema')
    action_display = serializers.CharField(source='get_action_display', read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            'id', 'user', 'user_nombre', 'action', 'action_display',
            'entity', 'entity_id', 'old_value', 'new_value',
            'ip_address', 'created_at',
        ]
        read_only_fields = fields
