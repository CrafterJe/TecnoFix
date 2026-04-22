# Pull Request: Renovación de tokens al cambiar contraseña

## Descripción

Al cambiar la contraseña, el backend ahora emite un par de tokens nuevos y los devuelve en la respuesta. El frontend los reemplaza en storage y la sesión continúa sin interrupción ni logout inesperado.

---

## Problema

El endpoint `POST /users/{id}/change-password/` solo devolvía un mensaje de confirmación. Los tokens del usuario seguían válidos hasta su expiración natural, lo que significa que un token robado antes del cambio de contraseña podría seguir usándose durante ese tiempo.

## Solución

Después de `user.set_password()` + `user.save()`, se genera un nuevo par de tokens con `RefreshToken.for_user(user)` y se incluyen en la respuesta `200`. El frontend los reemplaza de inmediato.

No se activa el blacklist de simplejwt (agrega complejidad de base de datos innecesaria para este proyecto), pero los tokens frescos cubren el caso principal: el usuario activo recibe credenciales nuevas y las usa desde ese momento.

---

## Cambios incluidos

### `apps/users/views.py`
- Se importa `RefreshToken` de `rest_framework_simplejwt.tokens`.
- `change_password` genera tokens nuevos tras guardar la contraseña y los retorna en el response junto con `detail`.

---

## Archivos modificados

- `apps/users/views.py` — lógica de renovación de tokens
- `docs/users/doc-feat-change-password-tokens.md` — documentación del endpoint actualizado

---

## Cómo probar

```bash
# 1. Hacer login y guardar tokens
POST /api/v1/auth/login/
{ "email": "tecnico1@tecnofix.com", "password": "Tecnico2024!" }

# 2. Cambiar contraseña
POST /api/v1/users/{id}/change-password/
Authorization: Bearer <access_token>
{ "password_actual": "Tecnico2024!", "password_nuevo": "NuevoPass2024!" }

# Verificar que el response 200 incluye access y refresh nuevos
# Verificar que los tokens nuevos funcionan en peticiones posteriores
```
