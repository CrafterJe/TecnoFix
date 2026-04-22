import logging

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from core.permissions import IsAdmin, IsOwnerOrAdmin

from .models import Usuario
from .serializers import (
    ChangePasswordSerializer,
    CustomTokenObtainPairSerializer,
    UsuarioCreateSerializer,
    UsuarioSerializer,
    UsuarioUpdateSerializer,
)

logger = logging.getLogger('apps.users')


class CustomTokenObtainPairView(TokenObtainPairView):
    """Login con JWT — retorna tokens + datos del usuario."""
    serializer_class = CustomTokenObtainPairSerializer


class UsuarioViewSet(ModelViewSet):
    queryset = Usuario.objects.all().order_by('nombre')
    search_fields = ['nombre', 'email']
    ordering_fields = ['nombre', 'email', 'rol', 'fecha_creacion']

    def get_serializer_class(self):
        if self.action == 'create':
            return UsuarioCreateSerializer
        if self.action in ('update', 'partial_update'):
            return UsuarioUpdateSerializer
        return UsuarioSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated()]
        if self.action == 'change_password':
            return [IsAuthenticated(), IsOwnerOrAdmin()]
        return [IsAdmin()]

    @action(detail=True, methods=['post'], url_path='change-password')
    def change_password(self, request, pk=None):
        user = self.get_object()
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if not user.check_password(serializer.validated_data['password_actual']):
            return Response(
                {'password_actual': 'Contraseña incorrecta.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(serializer.validated_data['password_nuevo'])
        user.save()
        #logger.info(f'Contraseña cambiada para usuario {user.email}')

        refresh = RefreshToken.for_user(user)
        return Response({
            'detail': 'Contraseña actualizada correctamente.',
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        })

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        user = self.get_object()
        user.activo = True
        user.save()
        return Response({'detail': f'Usuario {user.nombre} activado.'})

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        user = self.get_object()
        if user == request.user:
            return Response(
                {'detail': 'No puedes desactivar tu propia cuenta.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.activo = False
        user.save()
        return Response({'detail': f'Usuario {user.nombre} desactivado.'})
