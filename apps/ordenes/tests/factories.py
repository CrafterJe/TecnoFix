import factory
from faker import Faker

from apps.clientes.tests.factories import DispositivoFactory
from apps.ordenes.models import Evidencia, Orden, OrdenRefaccion
from apps.users.tests.factories import TecnicoFactory, UserFactory

fake = Faker('es_MX')


class OrdenFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Orden

    dispositivo = factory.SubFactory(DispositivoFactory)
    problema_reportado = factory.LazyFunction(lambda: fake.sentence())
    estado = 'recibido'
    created_by = factory.SubFactory(UserFactory)
    received_by = factory.SubFactory(UserFactory)


class OrdenConTecnicoFactory(OrdenFactory):
    assigned_to = factory.SubFactory(TecnicoFactory)
    estado = 'en_reparacion'
