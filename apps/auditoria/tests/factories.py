import factory

from apps.auditoria.models import AuditLog
from apps.users.tests.factories import UserFactory


class AuditLogFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AuditLog

    user = factory.SubFactory(UserFactory)
    action = 'CREATE'
    entity = 'Usuario'
    entity_id = factory.Sequence(lambda n: n)
    old_value = {}
    new_value = {'nombre': 'Test'}
    ip_address = '127.0.0.1'
