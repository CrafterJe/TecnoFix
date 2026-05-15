from django.utils import timezone


def generate_order_number():
    """
    Genera un número de orden único con formato ORD-YYYYMMDD-NNN.
    Ejemplo: ORD-20240324-001

    Usa select_for_update para evitar duplicados bajo concurrencia.
    """
    from django.db import transaction

    with transaction.atomic():
        from apps.ordenes.models import Orden

        today = timezone.now().date()
        date_str = today.strftime('%Y%m%d')
        prefix = f'ORD-{date_str}-'

        last = (
            Orden.objects.select_for_update()
            .filter(numero_orden__startswith=prefix)
            .order_by('-numero_orden')
            .first()
        )

        if last:
            try:
                seq = int(last.numero_orden.split('-')[-1]) + 1
            except (ValueError, IndexError):
                seq = 1
        else:
            seq = 1

        return f'{prefix}{seq:03d}'


def generate_quote_number():
    """
    Genera un número de cotización único con formato COT-YYYYMMDD-NNN.
    Ejemplo: COT-20240324-001

    Usa select_for_update para evitar duplicados bajo concurrencia.
    """
    from django.db import transaction

    with transaction.atomic():
        from apps.cotizaciones.models import Cotizacion

        today = timezone.now().date()
        date_str = today.strftime('%Y%m%d')
        prefix = f'COT-{date_str}-'

        last = (
            Cotizacion.objects.select_for_update()
            .filter(numero_cotizacion__startswith=prefix)
            .order_by('-numero_cotizacion')
            .first()
        )

        if last:
            try:
                seq = int(last.numero_cotizacion.split('-')[-1]) + 1
            except (ValueError, IndexError):
                seq = 1
        else:
            seq = 1

        return f'{prefix}{seq:03d}'
