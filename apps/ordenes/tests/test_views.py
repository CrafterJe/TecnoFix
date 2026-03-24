import pytest

from apps.clientes.tests.factories import DispositivoFactory
from apps.users.tests.factories import TecnicoFactory

from .factories import OrdenFactory


@pytest.mark.django_db
class TestOrdenViewSet:
    def test_list_ordenes_autenticado(self, admin_client):
        OrdenFactory.create_batch(3)
        resp = admin_client.get('/api/v1/ordenes/')
        assert resp.status_code == 200
        assert resp.data['count'] >= 3

    def test_crear_orden(self, recepcion_client):
        disp = DispositivoFactory()
        data = {
            'dispositivo': disp.pk,
            'problema_reportado': 'Pantalla rota',
        }
        resp = recepcion_client.post('/api/v1/ordenes/', data)
        assert resp.status_code == 201
        assert resp.data['numero_orden'].startswith('ORD-')

    def test_cambiar_estado(self, admin_client):
        orden = OrdenFactory()
        resp = admin_client.post(
            f'/api/v1/ordenes/{orden.pk}/cambiar-estado/',
            {'estado': 'diagnostico'},
        )
        assert resp.status_code == 200
        orden.refresh_from_db()
        assert orden.estado == 'diagnostico'

    def test_asignar_tecnico(self, admin_client):
        orden = OrdenFactory()
        tecnico = TecnicoFactory()
        resp = admin_client.post(
            f'/api/v1/ordenes/{orden.pk}/asignar-tecnico/',
            {'tecnico_id': tecnico.pk},
        )
        assert resp.status_code == 200
        orden.refresh_from_db()
        assert orden.assigned_to == tecnico

    def test_buscar_orden_por_numero(self, admin_client):
        orden = OrdenFactory()
        resp = admin_client.get(f'/api/v1/ordenes/?search={orden.numero_orden}')
        assert resp.status_code == 200
        assert resp.data['count'] >= 1

    def test_filtrar_por_estado(self, admin_client):
        OrdenFactory(estado='recibido')
        OrdenFactory(estado='listo')
        resp = admin_client.get('/api/v1/ordenes/?estado=listo')
        assert resp.status_code == 200
        for item in resp.data['results']:
            assert item['estado'] == 'listo'
