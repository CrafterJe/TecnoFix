import pytest

from .factories import RefaccionFactory


@pytest.mark.django_db
class TestRefaccionModel:
    def test_crear_refaccion(self):
        ref = RefaccionFactory()
        assert ref.pk is not None
        assert ref.stock == 10

    def test_bajo_stock_false(self):
        ref = RefaccionFactory(stock=10, stock_minimo=2)
        assert ref.bajo_stock is False

    def test_bajo_stock_true(self):
        ref = RefaccionFactory(stock=1, stock_minimo=5)
        assert ref.bajo_stock is True

    def test_bajo_stock_en_limite(self):
        ref = RefaccionFactory(stock=2, stock_minimo=2)
        assert ref.bajo_stock is True  # stock <= stock_minimo


@pytest.mark.django_db
class TestAjustarStock:
    def test_ajustar_stock_endpoint(self, admin_client):
        ref = RefaccionFactory(stock=10)
        resp = admin_client.post(
            f'/api/v1/inventario/{ref.pk}/ajustar-stock/',
            {'cantidad': 5},
        )
        assert resp.status_code == 200
        ref.refresh_from_db()
        assert ref.stock == 15

    def test_ajustar_stock_negativo(self, admin_client):
        ref = RefaccionFactory(stock=10)
        resp = admin_client.post(
            f'/api/v1/inventario/{ref.pk}/ajustar-stock/',
            {'cantidad': -3},
        )
        assert resp.status_code == 200
        ref.refresh_from_db()
        assert ref.stock == 7

    def test_ajustar_stock_insuficiente(self, admin_client):
        ref = RefaccionFactory(stock=2)
        resp = admin_client.post(
            f'/api/v1/inventario/{ref.pk}/ajustar-stock/',
            {'cantidad': -10},
        )
        assert resp.status_code == 400
