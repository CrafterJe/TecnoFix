import pytest


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def admin_user(db):
    from apps.users.tests.factories import UserFactory
    return UserFactory(rol='admin')


@pytest.fixture
def tecnico_user(db):
    from apps.users.tests.factories import UserFactory
    return UserFactory(rol='tecnico')


@pytest.fixture
def recepcion_user(db):
    from apps.users.tests.factories import UserFactory
    return UserFactory(rol='recepcion')


@pytest.fixture
def admin_client(api_client, admin_user):
    from rest_framework_simplejwt.tokens import RefreshToken
    refresh = RefreshToken.for_user(admin_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client


@pytest.fixture
def tecnico_client(api_client, tecnico_user):
    from rest_framework_simplejwt.tokens import RefreshToken
    refresh = RefreshToken.for_user(tecnico_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client


@pytest.fixture
def recepcion_client(api_client, recepcion_user):
    from rest_framework_simplejwt.tokens import RefreshToken
    refresh = RefreshToken.for_user(recepcion_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client
