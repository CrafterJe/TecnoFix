# Data migration: crea FuenteApi iniciales (FixOEM, SupraTecMX)
# y migra los registros existentes desde el CharField legacy hacia los FKs.
from django.db import migrations


FUENTES_INICIALES = [
    {
        "slug": "fixoem",
        "nombre": "FixOEM",
        "base_url": "https://fixoem.com",
        "tipo_parser": "shopify_v1",
        "orden": 1,
    },
    {
        "slug": "supratecmx",
        "nombre": "SupraTec",
        "base_url": "https://www.supratecmx.com",
        "tipo_parser": "shopify_v1",
        "orden": 2,
    },
]


# Mapeo de CotizacionItem.fuente_legacy → slug de FuenteApi
ITEM_FUENTE_MAP = {
    "api1": "fixoem",
    "api2": "supratecmx",
}


def crear_fuentes_y_migrar(apps, schema_editor):
    FuenteApi = apps.get_model("cotizaciones", "FuenteApi")
    ApiProductoCatalogo = apps.get_model("cotizaciones", "ApiProductoCatalogo")
    CotizacionItem = apps.get_model("cotizaciones", "CotizacionItem")

    # 1. Crear las fuentes iniciales
    fuentes_por_slug = {}
    for f in FUENTES_INICIALES:
        fuente, _ = FuenteApi.objects.get_or_create(
            slug=f["slug"],
            defaults={
                "nombre": f["nombre"],
                "base_url": f["base_url"],
                "tipo_parser": f["tipo_parser"],
                "orden": f["orden"],
                "activo": True,
            },
        )
        fuentes_por_slug[f["slug"]] = fuente

    # 2. Migrar ApiProductoCatalogo: fuente_legacy (string) → fuente (FK)
    for slug, fuente in fuentes_por_slug.items():
        ApiProductoCatalogo.objects.filter(fuente_legacy=slug).update(fuente=fuente)

    # 3. Migrar CotizacionItem: fuente_legacy → es_manual + fuente_api (FK)
    CotizacionItem.objects.filter(fuente_legacy="manual").update(es_manual=True)
    for legacy_value, fuente_slug in ITEM_FUENTE_MAP.items():
        fuente = fuentes_por_slug.get(fuente_slug)
        if fuente:
            CotizacionItem.objects.filter(fuente_legacy=legacy_value).update(
                fuente_api=fuente,
                es_manual=False,
            )


def revertir(apps, schema_editor):
    # No-op: la operación inversa es destructiva (los datos están en los nuevos FKs).
    # Si necesitas revertir, hay que migrar manualmente los datos al CharField legacy.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("cotizaciones", "0002_fuenteapi_schema"),
    ]

    operations = [
        migrations.RunPython(crear_fuentes_y_migrar, revertir),
    ]
