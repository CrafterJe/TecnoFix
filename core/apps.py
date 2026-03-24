import logging

from django.apps import AppConfig

logger = logging.getLogger('core')


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    default = True
    name = 'core'
    verbose_name = 'Core'

    def ready(self):
        self._connect_audit_signals()

    def _connect_audit_signals(self):
        from django.apps import apps
        from django.db.models.signals import post_delete, post_save, pre_save

        from core.mixins import AuditableMixin
        from core.signals import audit_post_delete, audit_post_save, audit_pre_save

        connected = 0
        for model in apps.get_models():
            if issubclass(model, AuditableMixin) and not model._meta.abstract:
                pre_save.connect(audit_pre_save, sender=model, weak=False)
                post_save.connect(audit_post_save, sender=model, weak=False)
                post_delete.connect(audit_post_delete, sender=model, weak=False)
                connected += 1

        logger.info(f'Audit signals connected to {connected} models')
