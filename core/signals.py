import logging

logger = logging.getLogger('core')


def _to_serializable(value):
    """Convierte un valor a algo JSON-serializable."""
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def instance_to_dict(instance):
    """Convierte una instancia de modelo a dict serializable."""
    if instance is None:
        return {}
    return {
        field.name: _to_serializable(getattr(instance, field.name, None))
        for field in instance._meta.fields
    }


def audit_pre_save(sender, instance, **kwargs):
    """Captura el estado anterior antes de guardar (para auditoría de UPDATE)."""
    if instance.pk:
        try:
            old = sender.objects.get(pk=instance.pk)
            instance._audit_old_state = instance_to_dict(old)
        except sender.DoesNotExist:
            instance._audit_old_state = {}
    else:
        instance._audit_old_state = {}


def audit_post_save(sender, instance, created, **kwargs):
    """Registra CREATE o UPDATE en AuditLog."""
    try:
        from apps.auditoria.models import AuditLog
        from core.middleware import get_current_ip, get_current_user

        old_values = getattr(instance, '_audit_old_state', {})
        new_values = instance_to_dict(instance)

        AuditLog.objects.create(
            user=get_current_user(),
            action='CREATE' if created else 'UPDATE',
            entity=sender.__name__,
            entity_id=instance.pk,
            old_value=old_values if not created else {},
            new_value=new_values,
            ip_address=get_current_ip() or '',
        )
    except Exception as exc:
        logger.error(f'Error al crear AuditLog ({sender.__name__}): {exc}')


def audit_post_delete(sender, instance, **kwargs):
    """Registra DELETE en AuditLog."""
    try:
        from apps.auditoria.models import AuditLog
        from core.middleware import get_current_ip, get_current_user

        AuditLog.objects.create(
            user=get_current_user(),
            action='DELETE',
            entity=sender.__name__,
            entity_id=instance.pk,
            old_value=instance_to_dict(instance),
            new_value={},
            ip_address=get_current_ip() or '',
        )
    except Exception as exc:
        logger.error(f'Error al crear AuditLog DELETE ({sender.__name__}): {exc}')
