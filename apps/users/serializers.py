from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Usuario


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """JWT con datos del usuario incluidos en la respuesta."""

    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = UsuarioSerializer(self.user).data
        return data


class UsuarioSerializer(serializers.ModelSerializer):
    rol_display = serializers.CharField(source='get_rol_display', read_only=True)

    class Meta:
        model = Usuario
        fields = [
            'id', 'nombre', 'email', 'rol', 'rol_display',
            'activo', 'fecha_creacion',
        ]
        read_only_fields = ['id', 'fecha_creacion']


class UsuarioCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = Usuario
        fields = ['nombre', 'email', 'password', 'password_confirm', 'rol']

    def validate(self, attrs):
        if attrs['password'] != attrs.pop('password_confirm'):
            raise serializers.ValidationError({'password_confirm': 'Las contraseñas no coinciden.'})
        return attrs

    def create(self, validated_data):
        return Usuario.objects.create_user(**validated_data)


class UsuarioUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ['nombre', 'rol', 'activo']


class ChangePasswordSerializer(serializers.Serializer):
    password_actual = serializers.CharField(write_only=True)
    password_nuevo = serializers.CharField(write_only=True, validators=[validate_password])
    password_nuevo_confirm = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs['password_nuevo'] != attrs['password_nuevo_confirm']:
            raise serializers.ValidationError(
                {'password_nuevo_confirm': 'Las contraseñas nuevas no coinciden.'}
            )
        return attrs
