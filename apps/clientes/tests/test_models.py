import pytest

from .factories import ClienteFactory, DispositivoFactory


@pytest.mark.django_db
class TestClienteModel:
    def test_crear_cliente(self):
        cliente = ClienteFactory()
        assert cliente.pk is not None
        assert cliente.nombre != ''

    def test_str_cliente(self):
        cliente = ClienteFactory(nombre='María García')
        assert str(cliente) == 'María García'

    def test_cliente_sin_email(self):
        cliente = ClienteFactory(email='')
        assert cliente.email == ''

    def test_dispositivos_relacionados(self):
        cliente = ClienteFactory()
        DispositivoFactory.create_batch(3, cliente=cliente)
        assert cliente.dispositivos.count() == 3


@pytest.mark.django_db
class TestDispositivoModel:
    def test_crear_dispositivo(self):
        disp = DispositivoFactory()
        assert disp.pk is not None
        assert disp.cliente is not None

    def test_str_dispositivo(self):
        disp = DispositivoFactory(marca='Samsung', modelo='S24', tipo='celular')
        assert 'Samsung' in str(disp)
        assert 'S24' in str(disp)
