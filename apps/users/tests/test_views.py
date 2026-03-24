import pytest
from django.urls import reverse

from .factories import AdminFactory, TecnicoFactory, UserFactory


@pytest.mark.django_db
class TestLogin:
    def test_login_exitoso(self, api_client):
        user = UserFactory()
        user.set_password('testpass123')
        user.save()
        url = reverse('token_obtain_pair')
        resp = api_client.post(url, {'email': user.email, 'password': 'testpass123'})
        assert resp.status_code == 200
        assert 'access' in resp.data
        assert 'refresh' in resp.data
        assert 'user' in resp.data

    def test_login_credenciales_invalidas(self, api_client):
        url = reverse('token_obtain_pair')
        resp = api_client.post(url, {'email': 'noexiste@test.com', 'password': 'mal'})
        assert resp.status_code == 401

    def test_login_usuario_inactivo(self, api_client):
        user = UserFactory(activo=False)
        user.set_password('testpass123')
        user.save()
        url = reverse('token_obtain_pair')
        resp = api_client.post(url, {'email': user.email, 'password': 'testpass123'})
        assert resp.status_code == 401


@pytest.mark.django_db
class TestUsuarioViewSet:
    def test_list_requiere_autenticacion(self, api_client):
        resp = api_client.get('/api/v1/users/')
        assert resp.status_code == 401

    def test_list_usuarios_autenticado(self, admin_client):
        UserFactory.create_batch(3)
        resp = admin_client.get('/api/v1/users/')
        assert resp.status_code == 200
        assert 'results' in resp.data

    def test_crear_usuario_como_admin(self, admin_client):
        data = {
            'nombre': 'Nuevo Técnico',
            'email': 'nuevo@tecnofix.com',
            'password': 'Tecnofix2024!',
            'password_confirm': 'Tecnofix2024!',
            'rol': 'tecnico',
        }
        resp = admin_client.post('/api/v1/users/', data)
        assert resp.status_code == 201

    def test_crear_usuario_sin_admin_falla(self, tecnico_client):
        data = {
            'nombre': 'Test',
            'email': 'test2@test.com',
            'password': 'pass',
            'password_confirm': 'pass',
            'rol': 'tecnico',
        }
        resp = tecnico_client.post('/api/v1/users/', data)
        assert resp.status_code == 403

    def test_desactivar_usuario(self, admin_client, db):
        user = TecnicoFactory()
        resp = admin_client.post(f'/api/v1/users/{user.pk}/deactivate/')
        assert resp.status_code == 200
        user.refresh_from_db()
        assert user.activo is False

    def test_paginacion(self, admin_client):
        UserFactory.create_batch(25)
        resp = admin_client.get('/api/v1/users/')
        assert resp.status_code == 200
        assert resp.data['total_pages'] >= 1
        assert len(resp.data['results']) <= 20
