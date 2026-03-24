import factory
from faker import Faker

from apps.inventario.models import Refaccion, RefaccionCompatible

fake = Faker('es_MX')


class RefaccionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Refaccion

    nombre = factory.Sequence(lambda n: f'Pantalla LCD {n}')
    descripcion = factory.LazyFunction(lambda: fake.sentence())
    categoria = factory.Iterator(['Pantallas', 'Baterías', 'Conectores', 'Chips'])
    stock = 10
    stock_minimo = 2
    precio_costo = factory.LazyFunction(lambda: fake.pydecimal(left_digits=3, right_digits=2, positive=True))
    precio_venta = factory.LazyFunction(lambda: fake.pydecimal(left_digits=3, right_digits=2, positive=True))
