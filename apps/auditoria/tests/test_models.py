import pytest

from apps.auditoria.models import AuditLog
from apps.clientes.tests.factories import ClienteFactory

from .factories import AuditLogFactory


@pytest.mark.django_db
class TestAuditLog:
    def test_crear_audit_log(self):
        log = AuditLogFactory()
        assert log.pk is not None
        assert log.action == 'CREATE'

    def test_str_audit_log(self):
        log = AuditLogFactory()
        assert '[CREATE]' in str(log)

    def test_audit_log_sin_usuario(self):
        log = AuditLogFactory(user=None)
        assert 'Sistema' in str(log)

    def test_signal_crea_audit_log_al_crear_cliente(self):
        """El signal debe crear un AuditLog automáticamente al crear un Cliente."""
        count_antes = AuditLog.objects.filter(entity='Cliente', action='CREATE').count()
        ClienteFactory()
        count_despues = AuditLog.objects.filter(entity='Cliente', action='CREATE').count()
        assert count_despues == count_antes + 1

    def test_signal_crea_audit_log_al_actualizar_cliente(self):
        """El signal debe crear un AuditLog de UPDATE al modificar un Cliente."""
        cliente = ClienteFactory()
        count_antes = AuditLog.objects.filter(entity='Cliente', action='UPDATE').count()
        cliente.nombre = 'Nombre Modificado'
        cliente.save()
        count_despues = AuditLog.objects.filter(entity='Cliente', action='UPDATE').count()
        assert count_despues == count_antes + 1

    def test_solo_admin_puede_ver_audit_logs(self, admin_client, tecnico_client):
        AuditLogFactory.create_batch(3)
        resp_admin = admin_client.get('/api/v1/auditoria/')
        assert resp_admin.status_code == 200

        resp_tecnico = tecnico_client.get('/api/v1/auditoria/')
        assert resp_tecnico.status_code == 403
