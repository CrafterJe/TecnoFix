# Migration manual: limpieza post-data-migration.
# Hace que el FK sea obligatorio en ApiProductoCatalogo, restaura constraints/índices
# y elimina los campos legacy.
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cotizaciones", "0003_migrate_fuente_data"),
    ]

    operations = [
        # 1. fuente FK ahora obligatorio en ApiProductoCatalogo
        migrations.AlterField(
            model_name="apiproductocatalogo",
            name="fuente",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="productos",
                to="cotizaciones.fuenteapi",
                verbose_name="Fuente",
            ),
        ),

        # 2. Restaurar constraint y índice (ahora apuntando al FK)
        migrations.AddConstraint(
            model_name="apiproductocatalogo",
            constraint=models.UniqueConstraint(
                fields=("fuente", "producto_id_externo"),
                name="uq_apiproducto_fuente_externo",
            ),
        ),
        migrations.AddIndex(
            model_name="apiproductocatalogo",
            index=models.Index(fields=["fuente"], name="idx_apiproducto_fuente"),
        ),

        # 3. Eliminar campos legacy
        migrations.RemoveField(
            model_name="apiproductocatalogo",
            name="fuente_legacy",
        ),
        migrations.RemoveField(
            model_name="cotizacionitem",
            name="fuente_legacy",
        ),
    ]
