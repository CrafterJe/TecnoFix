"""
Comando interactivo para crear usuarios de prueba.
Uso: python manage.py create_test_users
"""
from django.core.management.base import BaseCommand

USUARIOS_PRUEBA = [
    {
        'email': 'admin@tecnofix.com',
        'nombre': 'Administrador TecnoFix',
        'password': 'Admin2024!',
        'rol': 'admin',
        'is_staff': True,
    },
    {
        'email': 'tecnico1@tecnofix.com',
        'nombre': 'Carlos Rodríguez',
        'password': 'Tecnico2024!',
        'rol': 'tecnico',
    },
    {
        'email': 'tecnico2@tecnofix.com',
        'nombre': 'Ana Martínez',
        'password': 'Tecnico2024!',
        'rol': 'tecnico',
    },
    {
        'email': 'recepcion1@tecnofix.com',
        'nombre': 'Laura González',
        'password': 'Recepcion2024!',
        'rol': 'recepcion',
    },
    {
        'email': 'recepcion2@tecnofix.com',
        'nombre': 'Miguel Torres',
        'password': 'Recepcion2024!',
        'rol': 'recepcion',
    },
]


class Command(BaseCommand):
    help = 'Crea usuarios de prueba para TecnoFix de forma interactiva'

    def handle(self, *args, **options):
        self._mostrar_menu()

    def _mostrar_menu(self):
        while True:
            self.stdout.write('\n' + '=' * 50)
            self.stdout.write(self.style.SUCCESS('  TecnoFix — Usuarios de Prueba'))
            self.stdout.write('=' * 50)
            self.stdout.write('  1. Crear TODOS los usuarios de prueba')
            self.stdout.write('  2. Crear solo administrador')
            self.stdout.write('  3. Crear solo técnicos')
            self.stdout.write('  4. Crear solo recepción')
            self.stdout.write('  5. Listar usuarios de prueba existentes')
            self.stdout.write('  6. Eliminar todos los usuarios de prueba')
            self.stdout.write('  0. Salir')
            self.stdout.write('-' * 50)

            opcion = input('  Opción: ').strip()

            if opcion == '1':
                self._crear_usuarios(USUARIOS_PRUEBA)
            elif opcion == '2':
                admins = [u for u in USUARIOS_PRUEBA if u['rol'] == 'admin']
                self._crear_usuarios(admins)
            elif opcion == '3':
                tecnicos = [u for u in USUARIOS_PRUEBA if u['rol'] == 'tecnico']
                self._crear_usuarios(tecnicos)
            elif opcion == '4':
                recepcion = [u for u in USUARIOS_PRUEBA if u['rol'] == 'recepcion']
                self._crear_usuarios(recepcion)
            elif opcion == '5':
                self._listar_usuarios()
            elif opcion == '6':
                self._eliminar_usuarios()
            elif opcion == '0':
                self.stdout.write(self.style.SUCCESS('\n  ¡Hasta luego!\n'))
                break
            else:
                self.stdout.write(self.style.WARNING('  Opción no válida. Intenta de nuevo.'))

    def _crear_usuarios(self, lista):
        from apps.users.models import Usuario

        creados = 0
        existentes = 0

        for datos in lista:
            email = datos['email']
            if Usuario.objects.filter(email=email).exists():
                self.stdout.write(self.style.WARNING(f'  [YA EXISTE] {email}'))
                existentes += 1
                continue

            user_data = {k: v for k, v in datos.items() if k != 'password'}
            user = Usuario(**user_data)
            user.set_password(datos['password'])
            user.save()
            self.stdout.write(
                self.style.SUCCESS(f'  [CREADO] {email} | {datos["rol"]} | pass: {datos["password"]}')
            )
            creados += 1

        self.stdout.write(f'\n  Creados: {creados} | Ya existían: {existentes}')

    def _listar_usuarios(self):
        from apps.users.models import Usuario

        emails = [u['email'] for u in USUARIOS_PRUEBA]
        usuarios = Usuario.objects.filter(email__in=emails)

        if not usuarios.exists():
            self.stdout.write(self.style.WARNING('\n  No hay usuarios de prueba en la base de datos.'))
            return

        self.stdout.write(f'\n  {"EMAIL":<35} {"NOMBRE":<25} {"ROL":<12} {"ACTIVO"}')
        self.stdout.write('  ' + '-' * 80)
        for u in usuarios:
            activo = '✓' if u.activo else '✗'
            self.stdout.write(f'  {u.email:<35} {u.nombre:<25} {u.rol:<12} {activo}')

    def _eliminar_usuarios(self):
        from apps.users.models import Usuario

        confirmacion = input(
            self.style.WARNING('\n  ¿Seguro que quieres eliminar los usuarios de prueba? (s/N): ')
        ).strip().lower()

        if confirmacion != 's':
            self.stdout.write('  Cancelado.')
            return

        emails = [u['email'] for u in USUARIOS_PRUEBA]
        eliminados, _ = Usuario.objects.filter(email__in=emails).delete()
        self.stdout.write(self.style.SUCCESS(f'  {eliminados} usuario(s) eliminado(s).'))
