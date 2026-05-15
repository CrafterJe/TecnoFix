"""
Migración para soportar AtHome (y futuras fuentes no-Shopify):

- FuenteApi.base_url: URLField → CharField(500) para aceptar rutas locales además de URLs.
- FuenteApi.tipo_parser: agrega choice 'athome_v1' (no cambia la BD, solo validación).
- ApiProductoCatalogo.producto_id_externo: BigIntegerField → CharField(100)
  para soportar SKUs alfanuméricos.
- ApiProductoCatalogo.url_producto: nuevo URLField(blank=True).

La tabla api_productos_catalogo es un caché regenerable, así que el cambio de
tipo en producto_id_externo no requiere conservar datos históricos.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cotizaciones", "0005_fuenteapi_slug_blank"),
    ]

    operations = [
        # 1. base_url: URLField → CharField (acepta rutas locales)
        migrations.AlterField(
            model_name="fuenteapi",
            name="base_url",
            field=models.CharField(
                "URL / ruta base",
                max_length=500,
                help_text=(
                    "URL raíz (Shopify) o ruta al directorio de archivos JSON (AtHome). "
                    "Ej: https://fixoem.com o C:\\datos\\athome"
                ),
            ),
        ),
        # 2. tipo_parser: agrega choice athome_v1 (solo validación Django, sin cambio en BD)
        migrations.AlterField(
            model_name="fuenteapi",
            name="tipo_parser",
            field=models.CharField(
                "Tipo de parser",
                max_length=20,
                choices=[
                    ("shopify_v1", "Shopify v1 (products.json paginado)"),
                    ("athome_v1", "AtHome v1 (archivos JSON locales)"),
                ],
                default="shopify_v1",
                help_text="Estrategia para descargar/parsear productos.",
            ),
        ),
        # 3. Quitar constraint antes de cambiar el tipo del campo
        migrations.RemoveConstraint(
            model_name="apiproductocatalogo",
            name="uq_apiproducto_fuente_externo",
        ),
        # 4. producto_id_externo: BigIntegerField → CharField(100)
        migrations.AlterField(
            model_name="apiproductocatalogo",
            name="producto_id_externo",
            field=models.CharField(
                "ID / SKU externo",
                max_length=100,
            ),
        ),
        # 5. Restaurar constraint (ahora sobre CharField)
        migrations.AddConstraint(
            model_name="apiproductocatalogo",
            constraint=models.UniqueConstraint(
                fields=["fuente", "producto_id_externo"],
                name="uq_apiproducto_fuente_externo",
            ),
        ),
        # 6. Nuevo campo url_producto
        migrations.AddField(
            model_name="apiproductocatalogo",
            name="url_producto",
            field=models.URLField(
                "URL del producto",
                max_length=500,
                blank=True,
            ),
        ),
    ]
