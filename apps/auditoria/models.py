from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """
    Registro de auditoría. Captura todas las acciones sobre modelos auditables.
    NO hereda de AuditableMixin para evitar recursión infinita.
    """
    ACTION_CHOICES = [
        ('CREATE', 'Crear'),
        ('UPDATE', 'Actualizar'),
        ('DELETE', 'Eliminar'),
        ('ASSIGN', 'Asignar'),
        ('STATUS_CHANGE', 'Cambio de estado'),
        ('LOGIN', 'Inicio de sesión'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        verbose_name='Usuario',
    )
    action = models.CharField('Acción', max_length=20, choices=ACTION_CHOICES)
    entity = models.CharField('Entidad', max_length=100)
    entity_id = models.PositiveBigIntegerField('ID de entidad', null=True, blank=True)
    old_value = models.JSONField('Valor anterior', default=dict, blank=True)
    new_value = models.JSONField('Valor nuevo', default=dict, blank=True)
    ip_address = models.GenericIPAddressField('Dirección IP', null=True, blank=True)
    created_at = models.DateTimeField('Fecha', auto_now_add=True)

    class Meta:
        db_table = 'audit_log'
        verbose_name = 'Registro de auditoría'
        verbose_name_plural = 'Registros de auditoría'
        ordering = ['-created_at']

    def __str__(self):
        user_str = self.user.nombre if self.user else 'Sistema'
        return f'[{self.action}] {self.entity} #{self.entity_id} por {user_str}'
