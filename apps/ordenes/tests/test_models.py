import pytest

from .factories import OrdenFactory


@pytest.mark.django_db
class TestOrdenModel:
    def test_crear_orden_genera_numero(self):
        orden = OrdenFactory()
        assert orden.numero_orden != ''
        assert orden.numero_orden.startswith('ORD-')

    def test_numero_orden_formato(self):
        orden = OrdenFactory()
        partes = orden.numero_orden.split('-')
        assert len(partes) == 3
        assert partes[0] == 'ORD'
        assert len(partes[1]) == 8  # YYYYMMDD
        assert partes[2].isdigit()

    def test_numeros_orden_unicos(self):
        o1 = OrdenFactory()
        o2 = OrdenFactory()
        assert o1.numero_orden != o2.numero_orden

    def test_estado_inicial_recibido(self):
        orden = OrdenFactory()
        assert orden.estado == 'recibido'

    def test_str_orden(self):
        orden = OrdenFactory()
        assert orden.numero_orden in str(orden)

    def test_orden_tiene_dispositivo(self):
        orden = OrdenFactory()
        assert orden.dispositivo is not None
        assert orden.dispositivo.cliente is not None
