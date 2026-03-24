"""
Comando interactivo para sembrar datos de prueba.
Uso: python manage.py seed_data
"""
import random

from django.core.management.base import BaseCommand
from faker import Faker

fake = Faker('es_MX')

MARCAS = ['Samsung', 'Apple', 'Xiaomi', 'Motorola', 'Huawei', 'LG', 'Sony']
MODELOS = {
    'Samsung': ['Galaxy S24', 'Galaxy A54', 'Galaxy Note 20'],
    'Apple': ['iPhone 14', 'iPhone 13', 'iPad Air'],
    'Xiaomi': ['Redmi Note 12', 'Mi 11', 'Poco X5'],
    'Motorola': ['Moto G84', 'Edge 40', 'Moto G73'],
    'Huawei': ['P40', 'Nova 9', 'Mate 40'],
    'LG': ['V60', 'Velvet', 'Wing'],
    'Sony': ['Xperia 5 IV', 'Xperia 10 IV'],
}
PROBLEMAS = [
    'Pantalla rota',
    'No carga',
    'Se apaga solo',
    'Micrófono no funciona',
    'Cámara borrosa',
    'Botón de inicio dañado',
    'No reconoce la SIM',
    'Batería se descarga rápido',
    'Altavoz no suena',
    'Teclado táctil no responde',
]
REFACCIONES = [
    {'nombre': 'Pantalla LCD Samsung Galaxy S24', 'categoria': 'Pantallas', 'stock': 5, 'precio_costo': 800, 'precio_venta': 1500},
    {'nombre': 'Pantalla OLED iPhone 14', 'categoria': 'Pantallas', 'stock': 3, 'precio_costo': 1200, 'precio_venta': 2200},
    {'nombre': 'Batería Samsung Galaxy A54', 'categoria': 'Baterías', 'stock': 10, 'precio_costo': 150, 'precio_venta': 350},
    {'nombre': 'Batería iPhone 13', 'categoria': 'Baterías', 'stock': 8, 'precio_costo': 200, 'precio_venta': 450},
    {'nombre': 'Conector de carga USB-C universal', 'categoria': 'Conectores', 'stock': 15, 'precio_costo': 50, 'precio_venta': 150},
    {'nombre': 'Conector Lightning iPhone', 'categoria': 'Conectores', 'stock': 7, 'precio_costo': 80, 'precio_venta': 200},
    {'nombre': 'Botón Power Samsung', 'categoria': 'Botones', 'stock': 12, 'precio_costo': 30, 'precio_venta': 80},
    {'nombre': 'Micrófono universal', 'categoria': 'Audio', 'stock': 20, 'precio_costo': 25, 'precio_venta': 70},
]


class Command(BaseCommand):
    help = 'Siembra datos de prueba en la base de datos de forma interactiva'

    def handle(self, *args, **options):
        self._mostrar_menu()

    def _mostrar_menu(self):
        while True:
            self.stdout.write('\n' + '=' * 50)
            self.stdout.write(self.style.SUCCESS('  TecnoFix — Datos de Prueba'))
            self.stdout.write('=' * 50)

            # Resumen rápido
            self._mostrar_resumen_rapido()

            self.stdout.write('\n  ¿Qué deseas hacer?')
            self.stdout.write('  1. Sembrar TODOS los datos de prueba')
            self.stdout.write('  2. Solo clientes y dispositivos')
            self.stdout.write('  3. Solo órdenes de servicio')
            self.stdout.write('  4. Solo inventario (refacciones)')
            self.stdout.write('  5. Ver resumen detallado')
            self.stdout.write('  6. Limpiar TODOS los datos de prueba')
            self.stdout.write('  0. Salir')
            self.stdout.write('-' * 50)

            opcion = input('  Opción: ').strip()

            if opcion == '1':
                cantidad = self._pedir_cantidad('clientes', 10)
                self._crear_refacciones()
                self._crear_clientes_y_dispositivos(cantidad)
                self._crear_ordenes(cantidad * 2)
            elif opcion == '2':
                cantidad = self._pedir_cantidad('clientes', 10)
                self._crear_clientes_y_dispositivos(cantidad)
            elif opcion == '3':
                cantidad = self._pedir_cantidad('órdenes', 15)
                self._crear_ordenes(cantidad)
            elif opcion == '4':
                self._crear_refacciones()
            elif opcion == '5':
                self._mostrar_resumen_detallado()
            elif opcion == '6':
                self._limpiar_datos()
            elif opcion == '0':
                self.stdout.write(self.style.SUCCESS('\n  ¡Hasta luego!\n'))
                break
            else:
                self.stdout.write(self.style.WARNING('  Opción no válida.'))

    def _pedir_cantidad(self, entidad, default):
        try:
            valor = input(f'  ¿Cuántos {entidad}? [{default}]: ').strip()
            return int(valor) if valor else default
        except ValueError:
            return default

    def _mostrar_resumen_rapido(self):
        from apps.clientes.models import Cliente
        from apps.inventario.models import Refaccion
        from apps.ordenes.models import Orden

        self.stdout.write(
            f'  BD actual → '
            f'Clientes: {Cliente.objects.count()} | '
            f'Órdenes: {Orden.objects.count()} | '
            f'Refacciones: {Refaccion.objects.count()}'
        )

    def _mostrar_resumen_detallado(self):
        from apps.clientes.models import Cliente, Dispositivo
        from apps.inventario.models import Refaccion
        from apps.ordenes.models import Orden
        from apps.users.models import Usuario

        self.stdout.write('\n  === RESUMEN DE BASE DE DATOS ===')
        self.stdout.write(f'  Usuarios:     {Usuario.objects.count()}')
        self.stdout.write(f'  Clientes:     {Cliente.objects.count()}')
        self.stdout.write(f'  Dispositivos: {Dispositivo.objects.count()}')
        self.stdout.write(f'  Órdenes:      {Orden.objects.count()}')
        self.stdout.write(f'  Refacciones:  {Refaccion.objects.count()}')

        self.stdout.write('\n  Órdenes por estado:')
        from django.db.models import Count
        for item in Orden.objects.values('estado').annotate(total=Count('id')):
            self.stdout.write(f'    {item["estado"]:<25} {item["total"]}')

    def _crear_refacciones(self):
        from apps.inventario.models import Refaccion

        creadas = 0
        for datos in REFACCIONES:
            if not Refaccion.objects.filter(nombre=datos['nombre']).exists():
                Refaccion.objects.create(
                    nombre=datos['nombre'],
                    categoria=datos['categoria'],
                    stock=datos['stock'],
                    stock_minimo=2,
                    precio_costo=datos['precio_costo'],
                    precio_venta=datos['precio_venta'],
                )
                creadas += 1

        self.stdout.write(self.style.SUCCESS(f'  [✓] Refacciones creadas: {creadas}'))

    def _crear_clientes_y_dispositivos(self, cantidad):
        from apps.clientes.models import Cliente, Dispositivo
        from apps.users.models import Usuario

        usuario = Usuario.objects.filter(activo=True).first()
        if not usuario:
            self.stdout.write(self.style.ERROR(
                '  [✗] No hay usuarios. Ejecuta primero: python manage.py create_test_users'
            ))
            return

        clientes_creados = 0
        dispositivos_creados = 0

        for _ in range(cantidad):
            cliente = Cliente.objects.create(
                nombre=fake.name(),
                telefono=fake.phone_number()[:20],
                email=fake.email(),
                created_by=usuario,
            )
            clientes_creados += 1

            # 1-3 dispositivos por cliente
            for _ in range(random.randint(1, 3)):
                marca = random.choice(MARCAS)
                modelo = random.choice(MODELOS[marca])
                Dispositivo.objects.create(
                    cliente=cliente,
                    tipo=random.choice(['celular', 'tablet', 'laptop', 'computadora']),
                    marca=marca,
                    modelo=modelo,
                )
                dispositivos_creados += 1

        self.stdout.write(self.style.SUCCESS(
            f'  [✓] Clientes creados: {clientes_creados} | Dispositivos: {dispositivos_creados}'
        ))

    def _crear_ordenes(self, cantidad):
        from apps.clientes.models import Dispositivo
        from apps.ordenes.models import Orden
        from apps.users.models import Usuario

        dispositivos = list(Dispositivo.objects.all())
        if not dispositivos:
            self.stdout.write(self.style.ERROR(
                '  [✗] No hay dispositivos. Crea clientes primero (opción 2).'
            ))
            return

        usuarios = list(Usuario.objects.filter(activo=True))
        tecnicos = [u for u in usuarios if u.rol == 'tecnico']
        estados = ['recibido', 'diagnostico', 'esperando_refaccion', 'en_reparacion', 'listo', 'entregado']

        creadas = 0
        for _ in range(cantidad):
            estado = random.choice(estados)
            orden = Orden(
                dispositivo=random.choice(dispositivos),
                problema_reportado=random.choice(PROBLEMAS),
                estado=estado,
                created_by=random.choice(usuarios) if usuarios else None,
                received_by=random.choice(usuarios) if usuarios else None,
                costo_estimado=random.randint(200, 3000),
            )

            if tecnicos and estado != 'recibido':
                orden.assigned_to = random.choice(tecnicos)

            if estado == 'entregado':
                orden.costo_final = orden.costo_estimado
                orden.delivered_by = random.choice(usuarios) if usuarios else None

            orden.save()
            creadas += 1

        self.stdout.write(self.style.SUCCESS(f'  [✓] Órdenes creadas: {creadas}'))

    def _limpiar_datos(self):
        confirmacion = input(
            self.style.WARNING('\n  ¿Seguro? Esto eliminará TODOS los datos (excepto usuarios). (s/N): ')
        ).strip().lower()

        if confirmacion != 's':
            self.stdout.write('  Cancelado.')
            return

        from apps.clientes.models import Cliente
        from apps.inventario.models import Refaccion
        from apps.ordenes.models import Orden

        o, _ = Orden.objects.all().delete()
        c, _ = Cliente.objects.all().delete()
        r, _ = Refaccion.objects.all().delete()

        self.stdout.write(self.style.SUCCESS(
            f'  Eliminados → Órdenes: {o} | Clientes: {c} | Refacciones: {r}'
        ))
