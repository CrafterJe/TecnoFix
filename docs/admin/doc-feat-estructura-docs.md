# Convenciones de documentación — TecnoFix Backend

## Estructura de carpetas

```
docs/
├── admin/        → guías internas, convenciones y decisiones de arquitectura
├── PR/           → descripciones de pull requests
├── users/        → documentación y testing del módulo de usuarios
├── clientes/     → documentación y testing del módulo de clientes y dispositivos
├── ordenes/      → documentación y testing del módulo de órdenes y evidencias
├── inventario/   → documentación y testing del módulo de inventario
├── auditoria/    → documentación y testing del módulo de auditoría
└── core/         → documentación de utilidades compartidas (mixins, signals, permisos)
```

Si un módulo nuevo no tiene subcarpeta, se crea en ese momento.

## Convención de nombres de archivos

| Tipo | Formato | Ejemplo |
|---|---|---|
| Documentación / guía | `doc-<tipo>-<nombre>.md` | `doc-feat-ordenes-estados.md` |
| Guía de testing | `testing-<nombre>.md` | `testing-autenticacion.md` |
| Pull request | `pr-<tipo>-<nombre>.md` | `pr-feat-ajuste-stock.md` |

Donde `<tipo>` es uno de: `feat`, `fix`, `refactor`.

El nombre del archivo lo elige quien documenta directamente — no se pregunta al usuario salvo que la subcarpeta no sea obvia.

## Flujo de trabajo

1. Leer archivos relevantes antes de escribir código o crear archivos.
2. Presentar análisis + propuesta concreta.
3. Esperar aprobación explícita antes de ejecutar.

## Commits

El mensaje de commit se propone en el chat en texto plano con este formato:

```
feat(modulo): descripcion breve en imperativo

- detalle 1
- detalle 2
```

El desarrollador ejecuta el commit manualmente después de probar y confirmar.

## Pull Requests

- El archivo PR se crea en `docs/PR/pr-<tipo>-<nombre>.md`.
- El mensaje de commit propuesto va en el chat, no dentro del archivo.
- `gh pr create` nunca se ejecuta desde el asistente — solo se crea el archivo.
