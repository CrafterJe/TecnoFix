# Migration manual: crea FuenteApi y agrega campos transicionales
# para refactor de fuente (CharField → FK).
import core.mixins
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cotizaciones", "0001_initial"),
    ]

    operations = [
        # 1. Slug auto-generable en Categoría y Subcategoría
        migrations.AlterField(
            model_name="categoriadispositivo",
            name="slug",
            field=models.SlugField(blank=True, max_length=80, unique=True, verbose_name="Slug"),
        ),
        migrations.AlterField(
            model_name="subcategoriadispositivo",
            name="slug",
            field=models.SlugField(blank=True, max_length=80, verbose_name="Slug"),
        ),

        # 2. Nuevo modelo FuenteApi
        migrations.CreateModel(
            name="FuenteApi",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Creado en")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Actualizado en")),
                ("slug", models.SlugField(help_text="Identificador interno único (ej: fixoem).", max_length=50, unique=True, verbose_name="Slug")),
                ("nombre", models.CharField(help_text="Nombre visible (ej: FixOEM).", max_length=100, verbose_name="Nombre")),
                ("base_url", models.URLField(help_text="URL raíz de la tienda. Ej: https://fixoem.com", verbose_name="URL base")),
                (
                    "tipo_parser",
                    models.CharField(
                        choices=[("shopify_v1", "Shopify v1 (products.json paginado)")],
                        default="shopify_v1",
                        help_text="Estrategia para descargar/parsear productos.",
                        max_length=20,
                        verbose_name="Tipo de parser",
                    ),
                ),
                ("activo", models.BooleanField(default=True, verbose_name="Activa")),
                ("orden", models.PositiveIntegerField(default=0, verbose_name="Orden")),
                ("notas", models.TextField(blank=True, verbose_name="Notas")),
            ],
            options={
                "verbose_name": "Fuente de API",
                "verbose_name_plural": "Fuentes de API",
                "db_table": "cotizacion_fuentes_api",
                "ordering": ["orden", "nombre"],
            },
            bases=(core.mixins.AuditableMixin, models.Model),
        ),

        # 3. ApiProductoCatalogo: renombrar el viejo `fuente` a `fuente_legacy`
        migrations.RemoveConstraint(
            model_name="apiproductocatalogo",
            name="uq_apiproducto_fuente_externo",
        ),
        migrations.RemoveIndex(
            model_name="apiproductocatalogo",
            name="idx_apiproducto_fuente",
        ),
        migrations.RenameField(
            model_name="apiproductocatalogo",
            old_name="fuente",
            new_name="fuente_legacy",
        ),
        migrations.AlterField(
            model_name="apiproductocatalogo",
            name="fuente_legacy",
            field=models.CharField(blank=True, max_length=20, null=True, verbose_name="Fuente (legacy)"),
        ),
        migrations.AddField(
            model_name="apiproductocatalogo",
            name="fuente",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="productos",
                to="cotizaciones.fuenteapi",
                verbose_name="Fuente",
            ),
        ),

        # 4. CotizacionItem: renombrar `fuente` a `fuente_legacy`, agregar es_manual y fuente_api
        migrations.RenameField(
            model_name="cotizacionitem",
            old_name="fuente",
            new_name="fuente_legacy",
        ),
        migrations.AlterField(
            model_name="cotizacionitem",
            name="fuente_legacy",
            field=models.CharField(blank=True, max_length=20, null=True, verbose_name="Fuente (legacy)"),
        ),
        migrations.AddField(
            model_name="cotizacionitem",
            name="es_manual",
            field=models.BooleanField(
                default=False,
                help_text="True si el precio se obtuvo manualmente (no de una API).",
                verbose_name="Es manual",
            ),
        ),
        migrations.AddField(
            model_name="cotizacionitem",
            name="fuente_api",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="items_cotizacion",
                to="cotizaciones.fuenteapi",
                verbose_name="Fuente API",
                help_text="Fuente externa de la que vino el precio. Null si es_manual=True.",
            ),
        ),
    ]
