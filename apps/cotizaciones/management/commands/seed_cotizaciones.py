"""
Comando interactivo para sembrar la configuración base de cotizaciones.
Crea categoría Celulares/Tablets, subcategorías Android/iPhone,
15 tipos de reparación y sus fórmulas según tabla predeterminada.

Uso: python manage.py seed_cotizaciones
"""
from django.core.management.base import BaseCommand

# ─────────────────────────────────────────────
#  Datos base
# ─────────────────────────────────────────────

CATEGORIA = {
    'nombre': 'Celulares/Tablets',
    'slug': 'celular',
    'orden': 1,
}

SUBCATEGORIAS = [
    {'nombre': 'Android', 'slug': 'android', 'orden': 1},
    {'nombre': 'iPhone',  'slug': 'iphone',  'orden': 2},
]

# Fórmulas por subcategoría: (multiplicador, incremento) o 'personalizado'.
# 'personalizado' = el precio se ingresa manualmente, sin cálculo automático.
TIPOS = [
    {
        'nombre': 'Display',
        'orden': 1,
        'formulas': {'android': (2, 400), 'iphone': (2, 400)},
    },
    {
        'nombre': 'Batería',
        'orden': 2,
        'formulas': {'android': (2, 200), 'iphone': (2, 400)},
    },
    {
        'nombre': 'Centro de Carga',
        'orden': 3,
        'formulas': {'android': (2, 200), 'iphone': (2, 400)},
    },
    {
        'nombre': 'Cortes Circuitos',
        'orden': 4,
        'formulas': {'android': 'personalizado', 'iphone': 'personalizado'},
    },
    {
        'nombre': 'Tapa',
        'orden': 5,
        'formulas': {'android': (2, 200), 'iphone': (2, 400)},
    },
    {
        'nombre': 'Chasis',
        'orden': 6,
        'formulas': {'android': (2, 200), 'iphone': (2, 400)},
    },
    {
        'nombre': 'Flex Botón',
        'orden': 7,
        'formulas': {'android': (2, 200), 'iphone': (2, 400)},
    },
    {
        'nombre': 'Botones',
        'orden': 8,
        'formulas': {'android': (2, 200), 'iphone': (2, 400)},
    },
    {
        'nombre': 'Liberación',
        'orden': 9,
        'formulas': {'android': 'personalizado', 'iphone': 'personalizado'},
    },
    {
        'nombre': 'Desbloqueo',
        'orden': 10,
        'formulas': {'android': 'personalizado', 'iphone': 'personalizado'},
    },
    {
        'nombre': 'Flex Específico',
        'orden': 11,
        'formulas': {'android': 'personalizado', 'iphone': 'personalizado'},
    },
    {
        'nombre': 'Limpieza',
        'orden': 12,
        'formulas': {'android': (2, 200), 'iphone': (2, 400)},
    },
    {
        'nombre': 'Cámara',
        'orden': 13,
        'formulas': {'android': (2, 200), 'iphone': (2, 400)},
    },
    {
        'nombre': 'Micrófono',
        'orden': 14,
        'formulas': {'android': (2, 200), 'iphone': (2, 400)},
    },
    {
        'nombre': 'Lente de Cámara',
        'orden': 15,
        'formulas': {'android': (2, 200), 'iphone': (2, 400)},
    },
]


class Command(BaseCommand):
    help = 'Siembra la configuración base de cotizaciones (categoría, subcategorías, tipos y fórmulas).'

    def handle(self, *args, **options):
        self._mostrar_menu()

    # ──────────────────────────────────────────
    #  Menú
    # ──────────────────────────────────────────
    def _mostrar_menu(self):
        while True:
            self.stdout.write('\n' + '=' * 55)
            self.stdout.write(self.style.SUCCESS('  TecnoFix — Seed de Cotizaciones'))
            self.stdout.write('=' * 55)
            self.stdout.write('  1. Crear configuración completa (categoría + tipos + fórmulas)')
            self.stdout.write('  2. Ver configuración actual')
            self.stdout.write('  3. Eliminar toda la configuración de cotizaciones')
            self.stdout.write('  0. Salir')
            self.stdout.write('-' * 55)

            opcion = input('  Opción: ').strip()

            if opcion == '1':
                self._crear_todo()
            elif opcion == '2':
                self._ver_configuracion()
            elif opcion == '3':
                self._eliminar_todo()
            elif opcion == '0':
                self.stdout.write(self.style.SUCCESS('\n  ¡Hasta luego!\n'))
                break
            else:
                self.stdout.write(self.style.WARNING('  Opción no válida.'))

    # ──────────────────────────────────────────
    #  Operaciones
    # ──────────────────────────────────────────
    def _crear_todo(self):
        from apps.cotizaciones.models import (
            CategoriaDispositivo,
            FormulaReparacion,
            SubcategoriaDispositivo,
            TipoReparacion,
        )
        from decimal import Decimal

        self.stdout.write('')

        # 1. Categoría
        cat, creada = CategoriaDispositivo.objects.get_or_create(
            slug=CATEGORIA['slug'],
            defaults={
                'nombre': CATEGORIA['nombre'],
                'orden': CATEGORIA['orden'],
                'activo': True,
            },
        )
        tag = '[CREADA]' if creada else '[YA EXISTE]'
        self.stdout.write(
            (self.style.SUCCESS if creada else self.style.WARNING)(
                f'  {tag} Categoría: {cat.nombre}'
            )
        )

        # 2. Subcategorías
        subs = {}
        for s in SUBCATEGORIAS:
            sub, creada = SubcategoriaDispositivo.objects.get_or_create(
                categoria=cat,
                slug=s['slug'],
                defaults={'nombre': s['nombre'], 'orden': s['orden'], 'activo': True},
            )
            subs[s['slug']] = sub
            tag = '[CREADA]' if creada else '[YA EXISTE]'
            self.stdout.write(
                (self.style.SUCCESS if creada else self.style.WARNING)(
                    f'  {tag} Subcategoría: {sub.nombre}'
                )
            )

        # 3. Tipos de reparación + fórmulas
        self.stdout.write('')
        tipos_creados = 0
        formulas_creadas = 0

        for t in TIPOS:
            tipo, creado = TipoReparacion.objects.get_or_create(
                categoria=cat,
                nombre=t['nombre'],
                defaults={'orden': t['orden'], 'activo': True},
            )
            tag = '[CREADO]' if creado else '[YA EXISTE]'
            self.stdout.write(
                (self.style.SUCCESS if creado else self.style.WARNING)(
                    f'  {tag} Tipo: {tipo.nombre}'
                )
            )
            if creado:
                tipos_creados += 1

            for slug, valor in t['formulas'].items():
                sub = subs.get(slug)
                if not sub:
                    continue

                es_personalizado = valor == 'personalizado'
                mult = None if es_personalizado else Decimal(str(valor[0]))
                inc  = None if es_personalizado else Decimal(str(valor[1]))

                formula, f_creada = FormulaReparacion.objects.get_or_create(
                    tipo_reparacion=tipo,
                    subcategoria=sub,
                    defaults={
                        'es_personalizado': es_personalizado,
                        'multiplicador': mult,
                        'incremento': inc,
                        'activo': True,
                    },
                )
                if f_creada:
                    formulas_creadas += 1
                    expresion = 'Personalizado' if es_personalizado else f'precio*{mult}+{inc}'
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'    [FÓRMULA] {sub.nombre}: {expresion}'
                        )
                    )

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'  Listo. Tipos creados: {tipos_creados} | Fórmulas creadas: {formulas_creadas}'
        ))

    def _ver_configuracion(self):
        from apps.cotizaciones.models import CategoriaDispositivo, TipoReparacion

        categorias = CategoriaDispositivo.objects.prefetch_related(
            'subcategorias', 'tipos_reparacion__formulas__subcategoria',
        ).order_by('orden')

        if not categorias.exists():
            self.stdout.write(self.style.WARNING('\n  No hay configuración de cotizaciones.'))
            return

        for cat in categorias:
            self.stdout.write(f'\n  Categoría: {cat.nombre} (slug: {cat.slug})')
            for sub in cat.subcategorias.order_by('orden'):
                self.stdout.write(f'    Subcategoría: {sub.nombre}')

            tipos = cat.tipos_reparacion.order_by('orden')
            if not tipos.exists():
                self.stdout.write('    Sin tipos de reparación.')
                continue

            self.stdout.write(f'\n  {"TIPO":<25} {"ANDROID":<20} {"IPHONE":<20}')
            self.stdout.write('  ' + '-' * 65)
            for tipo in tipos:
                formulas = {f.subcategoria.slug: f for f in tipo.formulas.all() if f.subcategoria}
                android = self._label_formula(formulas.get('android'))
                iphone  = self._label_formula(formulas.get('iphone'))
                self.stdout.write(f'  {tipo.nombre:<25} {android:<20} {iphone:<20}')

    def _eliminar_todo(self):
        from apps.cotizaciones.models import CategoriaDispositivo

        total = CategoriaDispositivo.objects.count()
        if total == 0:
            self.stdout.write(self.style.WARNING('\n  No hay configuración para eliminar.'))
            return

        confirm = input(
            self.style.WARNING('\n  ¿Eliminar TODA la configuración de cotizaciones? (s/N): ')
        ).strip().lower()
        if confirm != 's':
            self.stdout.write('  Cancelado.')
            return

        # Cascade elimina subcategorías, tipos y fórmulas
        eliminadas, _ = CategoriaDispositivo.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f'  Eliminado. Categorías borradas: {eliminadas}'))

    @staticmethod
    def _label_formula(formula):
        if formula is None:
            return '—'
        if formula.es_personalizado:
            return 'Personalizado'
        m = formula.multiplicador
        i = formula.incremento
        return f'precio*{m.normalize()}+{i.normalize()}'
