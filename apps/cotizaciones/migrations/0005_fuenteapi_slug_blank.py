# Migration manual: marca el slug de FuenteApi como blank=True
# (no afecta BD, solo validación de Django; el save() lo auto-genera del nombre).
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cotizaciones", "0004_fuenteapi_cleanup"),
    ]

    operations = [
        migrations.AlterField(
            model_name="fuenteapi",
            name="slug",
            field=models.SlugField(
                blank=True,
                help_text='Identificador interno único (ej: fixoem). Se auto-genera del nombre si va vacío.',
                max_length=50,
                unique=True,
                verbose_name="Slug",
            ),
        ),
    ]
