# Freelance Backoffice

Para agentes de código que leen `AGENTS.md` (Codex, Pi, OpenCode y otros).

Antes de hacer nada en este repo, lee `CLAUDE.md`: ahí están qué es esto, dónde están los datos y las reglas. Valen igual para cualquier agente, aunque el archivo se llame así. Las más importantes:

- Una factura emitida no se edita ni se borra: se rectifica.
- Confirma antes de emitir una factura y antes de dar o quitar acceso a un espacio o a un proyecto.
- No inventes datos fiscales ni cifras.
- Los emails se dejan en borrador. Nunca los envíes.
- Nunca pidas ni pegues en el chat un token, y no reescribas la historia de git.

Cada tarea tiene su guía en `.claude/skills/<nombre>/SKILL.md`. Cuando la persona pida algo de esa lista, lee esa guía antes de empezar y síguela:

| Skill | Para qué |
|---|---|
| `configurar` | La primera vez, y los gastos del correo |
| `backoffice` | Clientes, proyectos, hitos, horas y preguntas sobre el negocio |
| `factura` | Emitir, cobrar y rectificar facturas |
| `gasto` | Gastos, gastos fijos y trimestres para la gestoría |
| `espacio` | Propuestas y espacios privados para clientes |
| `trabajo` | Fases, entregables, documentos, decisiones y pruebas de un proyecto |
| `melso` | Mandar facturas y gastos a Melso |
| `mantener` | Actualizar, copias de seguridad y `doctor` |

Claude Code aplica además los permisos de `.claude/settings.json` (por ejemplo, no puede editar a mano una factura emitida). Otros agentes no los leen: configura reglas parecidas en los permisos del tuyo.
