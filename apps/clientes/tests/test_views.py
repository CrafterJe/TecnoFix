import pytest

from .factories import ClienteFactory, DispositivoFactory


@pytest.mark.django_db
class TestClienteViewSet:
    def test_list_clientes(self, admin_client):
        ClienteFactory.create_batch(5)
        resp = admin_client.get('/api/v1/clientes/')
        assert resp.status_code == 200
        assert resp.data['count'] >= 5

    def test_crear_cliente(self, recepcion_client):
        data = {'nombre': 'Pedro Ramírez', 'telefono': '555-1234', 'email': 'pedro@mail.com'}
        resp = recepcion_client.post('/api/v1/clientes/', data)
        assert resp.status_code == 201
        assert resp.data['nombre'] == 'Pedro Ramírez'

    def test_buscar_cliente(self, admin_client):
        ClienteFactory(nombre='Luis Hernández')
        resp = admin_client.get('/api/v1/clientes/?search=Luis')
        assert resp.status_code == 200
        assert resp.data['count'] >= 1

    def test_eliminar_cliente_requiere_admin(self, tecnico_client):
        cliente = ClienteFactory()
        resp = tecnico_client.delete(f'/api/v1/clientes/{cliente.pk}/')
        assert resp.status_code == 403

    def test_eliminar_cliente_como_admin(self, admin_client):
        cliente = ClienteFactory()
        resp = admin_client.delete(f'/api/v1/clientes/{cliente.pk}/')
        assert resp.status_code == 204
