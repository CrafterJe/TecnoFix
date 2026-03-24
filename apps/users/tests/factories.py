import factory
from django.contrib.auth.hashers import make_password
from faker import Faker

from apps.users.models import Usuario

fake = Faker('es_MX')


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Usuario

    nombre = factory.LazyFunction(lambda: fake.name())
    email = factory.Sequence(lambda n: f'user{n}@tecnofix.test')
    password = factory.LazyFunction(lambda: make_password('testpass123'))
    rol = 'tecnico'
    activo = True
    is_staff = False


class AdminFactory(UserFactory):
    rol = 'admin'
    is_staff = True
    email = factory.Sequence(lambda n: f'admin{n}@tecnofix.test')


class TecnicoFactory(UserFactory):
    rol = 'tecnico'
    email = factory.Sequence(lambda n: f'tecnico{n}@tecnofix.test')


class RecepcionFactory(UserFactory):
    rol = 'recepcion'
    email = factory.Sequence(lambda n: f'recepcion{n}@tecnofix.test')
