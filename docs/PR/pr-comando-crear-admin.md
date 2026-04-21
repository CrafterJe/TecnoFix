# Pull Request: Implementación de Comando Interactivo para Gestión de Administradores

## Descripción
Se ha añadido un nuevo comando de gestión personalizado (`create_admin`) para facilitar la administración de usuarios con rol de administrador directamente desde la CLI. Este comando centraliza tareas comunes que antes requerían acceso directo a la base de datos o al shell de Django.

## Funcionalidades Incluidas
Se implementó un menú interactivo con las siguientes opciones:

1. **Crear nuevo administrador:** Validación de email, nombre y contraseña (mínimo 8 caracteres) con entrada oculta.
2. **Listar administradores:** Tabla visual que muestra email, nombre y estado de actividad (✓/✗).
3. **Desactivar administrador:** Cambio de estado a inactivo mediante búsqueda por email con confirmación.
4. **Reactivar administrador:** Cambio de estado a activo para administradores previamente desactivados.
5. **Restablecer contraseña:** Permite cambiar la contraseña de un admin existente usando `set_password` para asegurar el hasheo correcto.

## Detalles Técnicos
- **Seguridad:** Se utiliza el módulo `getpass` para que las contraseñas no sean visibles en la terminal durante la escritura.
- **Validaciones:** Incluye `validate_email` de Django y comprobaciones de existencia de usuario para evitar duplicados o errores de búsqueda.
- **Integridad:** Las actualizaciones de estado y contraseña utilizan `update_fields` para optimizar las consultas a la base de datos.
- **UX en CLI:** Se hace uso de `self.style` para diferenciar mensajes de éxito, advertencia y error por colores en la consola.

---

## Cómo probar el comando
Ejecuta el siguiente comando en la terminal:
```bash
python manage.py create_admin