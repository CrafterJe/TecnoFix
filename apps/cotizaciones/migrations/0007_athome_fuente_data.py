"""
Data migration: registra AtHome como FuenteApi activa.

La ruta base_url se calcula en tiempo de migración a partir de la ubicación
de este archivo, apuntando a la carpeta AtHome que está al mismo nivel
que el proyecto TecnoFix.

Si los archivos se mueven, actualizar el registro desde /admin/cotizaciones/fuenteapi/.
"""
from pathlib import Path

from django.db import migrations


def _athome_path():
    # Este archivo: .../TecnoFix/TecnoFix/apps/cotizaciones/migrations/0007_*.py
    # Subiendo 5 niveles llegamos a la carpeta padre de TecnoFix (Projects/TecnoFix/)
    migration_file = Path(__file__).resolve()
    tecnofix_parent = migration_file.parent.parent.parent.parent.parent
    return str(tecnofix_parent / "AtHome")


def crear_fuente_athome(apps, schema_editor):
    FuenteApi = apps.get_model("cotizaciones", "FuenteApi")
    if FuenteApi.objects.filter(slug="athome").exists():
        return
    FuenteApi.objects.create(
        slug="athome",
        nombre="AtHome",
        base_url=_athome_path(),
        tipo_parser="athome_v1",
        activo=True,
        orden=3,
        notas="Catálogo local AtHome (20 archivos JSON, ~500 productos c/u).",
    )


def eliminar_fuente_athome(apps, schema_editor):
    FuenteApi = apps.get_model("cotizaciones", "FuenteApi")
    FuenteApi.objects.filter(slug="athome").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("cotizaciones", "0006_athome_schema"),
    ]

    operations = [
        migrations.RunPython(crear_fuente_athome, eliminar_fuente_athome),
    ]
