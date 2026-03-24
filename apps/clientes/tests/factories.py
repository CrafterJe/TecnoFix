import factory
from faker import Faker

from apps.clientes.models import Cliente, Dispositivo
from apps.users.tests.factories import UserFactory

fake = Faker('es_MX')


class ClienteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Cliente

    nombre = factory.LazyFunction(lambda: fake.name())
    telefono = factory.LazyFunction(lambda: fake.phone_number()[:20])
    email = factory.Sequence(lambda n: f'cliente{n}@mail.com')
    created_by = factory.SubFactory(UserFactory)


class DispositivoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Dispositivo

    cliente = factory.SubFactory(ClienteFactory)
    tipo = 'celular'
    marca = factory.Iterator(['Samsung', 'Apple', 'Xiaomi', 'Motorola'])
    modelo = factory.LazyFunction(lambda: fake.word().capitalize())
