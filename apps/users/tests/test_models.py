import pytest

from apps.users.models import Usuario

from .factories import AdminFactory, RecepcionFactory, TecnicoFactory, UserFactory


@pytest.mark.django_db
class TestUsuarioModel:
    def test_create_user_basic(self):
        user = UserFactory()
        assert user.pk is not None
        assert user.activo is True
        assert user.is_active is True

    def test_user_str(self):
        user = UserFactory(nombre='Juan Pérez', rol='tecnico')
        assert 'Juan Pérez' in str(user)
        assert 'Técnico' in str(user)

    def test_admin_role_properties(self):
        admin = AdminFactory()
        assert admin.is_admin is True
        assert admin.is_tecnico is False
        assert admin.is_recepcion is False

    def test_tecnico_role_properties(self):
        tecnico = TecnicoFactory()
        assert tecnico.is_tecnico is True
        assert tecnico.is_admin is False

    def test_recepcion_role_properties(self):
        recepcion = RecepcionFactory()
        assert recepcion.is_recepcion is True
        assert recepcion.is_admin is False

    def test_email_is_unique(self):
        UserFactory(email='test@test.com')
        with pytest.raises(Exception):
            UserFactory(email='test@test.com')

    def test_deactivate_user(self):
        user = UserFactory(activo=True)
        user.activo = False
        user.save()
        user.refresh_from_db()
        assert user.activo is False
        assert user.is_active is False

    def test_create_superuser(self):
        admin = Usuario.objects.create_superuser(
            email='super@test.com',
            nombre='Super Admin',
            password='superpass123',
        )
        assert admin.rol == 'admin'
        assert admin.is_staff is True
        assert admin.is_superuser is True
