import pytest

from .factories import RefaccionFactory


@pytest.mark.django_db
class TestRefaccionViewSet:
    def test_list_refacciones(self, admin_client):
        RefaccionFactory.create_batch(5)
        resp = admin_client.get('/api/v1/inventario/')
        assert resp.status_code == 200
        assert resp.data['count'] >= 5

    def test_crear_refaccion_como_admin(self, admin_client):
        data = {
            'nombre': 'Batería iPhone 14',
            'categoria': 'Baterías',
            'stock': 5,
            'stock_minimo': 1,
            'precio_costo': '150.00',
            'precio_venta': '350.00',
        }
        resp = admin_client.post('/api/v1/inventario/', data)
        assert resp.status_code == 201

    def test_crear_refaccion_como_tecnico_falla(self, tecnico_client):
        data = {'nombre': 'Test', 'stock': 1, 'stock_minimo': 1}
        resp = tecnico_client.post('/api/v1/inventario/', data)
        assert resp.status_code == 403

    def test_bajo_stock_endpoint(self, admin_client):
        RefaccionFactory(stock=0, stock_minimo=5)
        resp = admin_client.get('/api/v1/inventario/bajo-stock/')
        assert resp.status_code == 200
        assert len(resp.data) >= 1
