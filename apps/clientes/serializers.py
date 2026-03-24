from rest_framework import serializers

from .models import Cliente, Dispositivo


class DispositivoSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)

    class Meta:
        model = Dispositivo
        fields = ['id', 'tipo', 'tipo_display', 'marca', 'modelo', 'created_at']
        read_only_fields = ['id', 'created_at']


class ClienteSerializer(serializers.ModelSerializer):
    dispositivos = DispositivoSerializer(many=True, read_only=True)
    created_by_nombre = serializers.CharField(source='created_by.nombre', read_only=True)
    total_dispositivos = serializers.IntegerField(
        source='dispositivos.count', read_only=True
    )

    class Meta:
        model = Cliente
        fields = [
            'id', 'nombre', 'telefono', 'email',
            'created_by', 'created_by_nombre',
            'total_dispositivos', 'dispositivos',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']


class ClienteListSerializer(serializers.ModelSerializer):
    total_dispositivos = serializers.IntegerField(
        source='dispositivos.count', read_only=True
    )

    class Meta:
        model = Cliente
        fields = ['id', 'nombre', 'telefono', 'email', 'total_dispositivos', 'created_at']


class DispositivoCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dispositivo
        fields = ['id', 'cliente', 'tipo', 'marca', 'modelo']
