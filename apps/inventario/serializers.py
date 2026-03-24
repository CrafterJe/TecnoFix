from rest_framework import serializers

from .models import Refaccion, RefaccionCompatible


class RefaccionCompatibleSerializer(serializers.ModelSerializer):
    class Meta:
        model = RefaccionCompatible
        fields = ['id', 'marca', 'modelo', 'tipo_dispositivo']


class RefaccionSerializer(serializers.ModelSerializer):
    compatibilidades = RefaccionCompatibleSerializer(many=True, read_only=True)
    bajo_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = Refaccion
        fields = [
            'id', 'nombre', 'descripcion', 'categoria',
            'stock', 'stock_minimo', 'bajo_stock',
            'precio_costo', 'precio_venta',
            'compatibilidades', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class RefaccionListSerializer(serializers.ModelSerializer):
    bajo_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = Refaccion
        fields = ['id', 'nombre', 'categoria', 'stock', 'stock_minimo', 'bajo_stock', 'precio_venta']


class AjustarStockSerializer(serializers.Serializer):
    cantidad = serializers.IntegerField(help_text='Positivo para entrada, negativo para salida.')
    motivo = serializers.CharField(max_length=200, required=False, default='')

    def validate_cantidad(self, value):
        if value == 0:
            raise serializers.ValidationError('La cantidad no puede ser 0.')
        return value
