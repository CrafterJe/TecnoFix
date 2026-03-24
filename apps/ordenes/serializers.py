from rest_framework import serializers

from apps.clientes.serializers import DispositivoSerializer

from .models import Evidencia, Orden, OrdenRefaccion


class EvidenciaSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    uploaded_by_nombre = serializers.CharField(source='uploaded_by.nombre', read_only=True)

    class Meta:
        model = Evidencia
        fields = ['id', 'tipo', 'tipo_display', 'imagen', 'uploaded_by', 'uploaded_by_nombre', 'created_at']
        read_only_fields = ['id', 'uploaded_by', 'created_at']


class EvidenciaCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Evidencia
        fields = ['orden', 'imagen', 'tipo']


class OrdenRefaccionSerializer(serializers.ModelSerializer):
    refaccion_nombre = serializers.CharField(source='refaccion.nombre', read_only=True)
    added_by_nombre = serializers.CharField(source='added_by.nombre', read_only=True)

    class Meta:
        model = OrdenRefaccion
        fields = ['id', 'refaccion', 'refaccion_nombre', 'cantidad', 'added_by', 'added_by_nombre']
        read_only_fields = ['id', 'added_by']


class OrdenSerializer(serializers.ModelSerializer):
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    dispositivo_info = DispositivoSerializer(source='dispositivo', read_only=True)
    evidencias = EvidenciaSerializer(many=True, read_only=True)
    refacciones_usadas = OrdenRefaccionSerializer(many=True, read_only=True)
    created_by_nombre = serializers.CharField(source='created_by.nombre', read_only=True)
    assigned_to_nombre = serializers.CharField(source='assigned_to.nombre', read_only=True)

    class Meta:
        model = Orden
        fields = [
            'id', 'numero_orden',
            'dispositivo', 'dispositivo_info',
            'problema_reportado', 'diagnostico',
            'estado', 'estado_display',
            'costo_estimado', 'costo_final',
            'created_by', 'created_by_nombre',
            'received_by', 'assigned_to', 'assigned_to_nombre',
            'delivered_by', 'status_updated_by',
            'evidencias', 'refacciones_usadas',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'numero_orden', 'created_by',
            'status_updated_by', 'created_at', 'updated_at',
        ]


class OrdenListSerializer(serializers.ModelSerializer):
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    cliente_nombre = serializers.CharField(source='dispositivo.cliente.nombre', read_only=True)
    dispositivo_info = serializers.SerializerMethodField()
    assigned_to_nombre = serializers.CharField(source='assigned_to.nombre', read_only=True)

    class Meta:
        model = Orden
        fields = [
            'id', 'numero_orden', 'estado', 'estado_display',
            'cliente_nombre', 'dispositivo_info', 'assigned_to_nombre',
            'costo_estimado', 'created_at',
        ]

    def get_dispositivo_info(self, obj):
        return f'{obj.dispositivo.marca} {obj.dispositivo.modelo}'


class OrdenCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Orden
        fields = ['dispositivo', 'problema_reportado', 'received_by', 'costo_estimado']


class AsignarTecnicoSerializer(serializers.Serializer):
    tecnico_id = serializers.IntegerField()

    def validate_tecnico_id(self, value):
        from apps.users.models import Usuario
        try:
            tecnico = Usuario.objects.get(pk=value, rol='tecnico', activo=True)
        except Usuario.DoesNotExist:
            raise serializers.ValidationError('Técnico no encontrado o inactivo.')
        return value


class CambiarEstadoSerializer(serializers.Serializer):
    ESTADO_CHOICES = Orden.ESTADO_CHOICES
    estado = serializers.ChoiceField(choices=ESTADO_CHOICES)
    diagnostico = serializers.CharField(required=False, allow_blank=True)


class AgregarRefaccionSerializer(serializers.Serializer):
    refaccion_id = serializers.IntegerField()
    cantidad = serializers.IntegerField(min_value=1)

    def validate_refaccion_id(self, value):
        from apps.inventario.models import Refaccion
        try:
            ref = Refaccion.objects.get(pk=value)
        except Refaccion.DoesNotExist:
            raise serializers.ValidationError('Refacción no encontrada.')
        return value
