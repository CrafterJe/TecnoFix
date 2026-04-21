"""
Comando interactivo para gestionar administradores.
Uso: python manage.py create_admin
"""
import getpass

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Gestiona administradores de TecnoFix de forma interactiva'

    def handle(self, *args, **options):
        self._mostrar_menu()

    def _mostrar_menu(self):
        while True:
            self.stdout.write('\n' + '=' * 50)
            self.stdout.write(self.style.SUCCESS('  TecnoFix — Gestión de Administradores'))
            self.stdout.write('=' * 50)
            self.stdout.write('  1. Crear nuevo administrador')
            self.stdout.write('  2. Listar administradores existentes')
            self.stdout.write('  3. Desactivar administrador')
            self.stdout.write('  4. Reactivar administrador')
            self.stdout.write('  5. Restablecer contraseña')
            self.stdout.write('  0. Salir')
            self.stdout.write('-' * 50)

            opcion = input('  Opción: ').strip()

            if opcion == '1':
                self._crear_admin()
            elif opcion == '2':
                self._listar_admins()
            elif opcion == '3':
                self._cambiar_estado(activar=False)
            elif opcion == '4':
                self._cambiar_estado(activar=True)
            elif opcion == '5':
                self._restablecer_password()
            elif opcion == '0':
                self.stdout.write(self.style.SUCCESS('\n  ¡Hasta luego!\n'))
                break
            else:
                self.stdout.write(self.style.WARNING('  Opción no válida. Intenta de nuevo.'))

    def _crear_admin(self):
        from django.core.validators import validate_email
        from django.core.exceptions import ValidationError
        from apps.users.models import Usuario

        self.stdout.write('\n  -- Crear administrador --')

        # Email
        while True:
            email = input('  Email: ').strip()
            if not email:
                self.stdout.write(self.style.WARNING('  El email no puede estar vacío.'))
                continue
            try:
                validate_email(email)
            except ValidationError:
                self.stdout.write(self.style.WARNING('  Email inválido.'))
                continue
            if Usuario.objects.filter(email=email).exists():
                self.stdout.write(self.style.WARNING(f'  Ya existe un usuario con el email {email}.'))
                continue
            break

        # Nombre
        while True:
            nombre = input('  Nombre completo: ').strip()
            if nombre:
                break
            self.stdout.write(self.style.WARNING('  El nombre no puede estar vacío.'))

        # Password
        while True:
            password = getpass.getpass('  Contraseña: ')
            if len(password) < 8:
                self.stdout.write(self.style.WARNING('  La contraseña debe tener al menos 8 caracteres.'))
                continue
            confirmacion = getpass.getpass('  Confirmar contraseña: ')
            if password != confirmacion:
                self.stdout.write(self.style.WARNING('  Las contraseñas no coinciden.'))
                continue
            break

        usuario = Usuario.objects.create_superuser(
            email=email,
            nombre=nombre,
            password=password,
        )

        self.stdout.write(self.style.SUCCESS(
            f'\n  [CREADO] {usuario.nombre} | {usuario.email} | admin'
        ))

    def _listar_admins(self):
        from apps.users.models import Usuario

        admins = Usuario.objects.filter(rol='admin').order_by('nombre')

        if not admins.exists():
            self.stdout.write(self.style.WARNING('\n  No hay administradores registrados.'))
            return

        self.stdout.write(f'\n  {"EMAIL":<35} {"NOMBRE":<25} {"ACTIVO"}')
        self.stdout.write('  ' + '-' * 65)
        for u in admins:
            activo = self.style.SUCCESS('✓') if u.activo else self.style.ERROR('✗')
            self.stdout.write(f'  {u.email:<35} {u.nombre:<25} {activo}')

    def _cambiar_estado(self, activar: bool):
        from apps.users.models import Usuario

        accion = 'reactivar' if activar else 'desactivar'
        estado_label = 'ACTIVO' if activar else 'INACTIVO'

        self.stdout.write(f'\n  -- {accion.capitalize()} administrador --')

        email = input('  Email del administrador: ').strip()
        if not email:
            self.stdout.write(self.style.WARNING('  Email no puede estar vacío.'))
            return

        try:
            usuario = Usuario.objects.get(email=email, rol='admin')
        except Usuario.DoesNotExist:
            self.stdout.write(self.style.WARNING(f'  No se encontró un administrador con el email {email}.'))
            return

        if usuario.activo == activar:
            self.stdout.write(self.style.WARNING(f'  El usuario ya está {estado_label}.'))
            return

        confirmacion = input(
            self.style.WARNING(f'  ¿{accion.capitalize()} a {usuario.nombre}? (s/N): ')
        ).strip().lower()

        if confirmacion != 's':
            self.stdout.write('  Cancelado.')
            return

        usuario.activo = activar
        usuario.save(update_fields=['activo'])
        self.stdout.write(self.style.SUCCESS(f'  [{estado_label}] {usuario.nombre} | {usuario.email}'))

    def _restablecer_password(self):
        from apps.users.models import Usuario

        self.stdout.write('\n  -- Restablecer contraseña --')

        email = input('  Email del administrador: ').strip()
        if not email:
            self.stdout.write(self.style.WARNING('  Email no puede estar vacío.'))
            return

        try:
            usuario = Usuario.objects.get(email=email, rol='admin')
        except Usuario.DoesNotExist:
            self.stdout.write(self.style.WARNING(f'  No se encontró un administrador con el email {email}.'))
            return

        self.stdout.write(f'  Usuario: {usuario.nombre}')

        while True:
            password = getpass.getpass('  Nueva contraseña: ')
            if not password:
                self.stdout.write(self.style.WARNING('  La contraseña no puede estar vacía.'))
                continue
            confirmacion = getpass.getpass('  Confirmar contraseña: ')
            if password != confirmacion:
                self.stdout.write(self.style.WARNING('  Las contraseñas no coinciden.'))
                continue
            break

        usuario.set_password(password)
        usuario.save(update_fields=['password'])
        self.stdout.write(self.style.SUCCESS(f'  [ACTUALIZADO] Contraseña restablecida para {usuario.email}'))
