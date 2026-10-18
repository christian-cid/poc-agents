# Coordinación del equipo de agentes

Dos agentes trabajan sobre la POC y se coordinan por archivos del repositorio, no por memoria de conversación.

| Agente | Responsabilidad | Es dueño de |
| --- | --- | --- |
| `analista-cdu` | Qué y por qué: casos de uso y criterios de aceptación | `specs/NNN-*/spec.md` |
| `integrador-elevenlabs-whatsapp` | Cómo: agente, canal WhatsApp, conversaciones, despliegue y pruebas | `plan.md` y `tasks.md` de cada CDU, `agent_configs/`, `test_configs/`, `scripts/`, `.github/workflows/` |

La persona dueña del proyecto decide lo que ninguno de los dos puede decidir (cuentas, planes, idioma, tono, canal alternativo) y es la única que crea cuentas y maneja credenciales.

## Flujo por CDU

1. `analista-cdu` escribe la spec y la deja con estado **Propuesta**.
2. `integrador-elevenlabs-whatsapp` la revisa y responde si es viable. Si no lo es o falta información, abre un handoff.
3. Cuando ambos están de acuerdo, la spec pasa a **Aprobada** y el integrador escribe el plan y las tareas.
4. El integrador implementa y prueba. Cada criterio de aceptación queda cubierto por una prueba del agente o por un chequeo manual descrito en la spec.
5. `analista-cdu` verifica el resultado contra los criterios y marca el CDU como **Hecho**, o abre un handoff con lo que falta.

## Handoffs

Un handoff es un archivo en `docs/equipo/handoffs/` llamado `NNN-de-a-asunto.md` (por ejemplo `001-integrador-a-analista-idioma.md`). Contiene:

- **De / A / CDU:** quién pregunta, a quién y de qué caso de uso.
- **Necesidad o pregunta:** una sola, concreta.
- **Contexto:** qué se sabe y qué fuente lo respalda.
- **Propuesta:** lo que haría quien pregunta, para que responder sea decir sí o ajustar.
- **Respuesta:** la completa quien recibe. Mientras esté vacía, el handoff está abierto.
- **Decisión final:** una línea. Si cambia una spec, se actualiza `spec.md` y se enlaza el handoff.

Si la respuesta depende de la persona dueña del proyecto, el agente receptor lo dice en la sección Respuesta y se lo informa en su resumen final.

## Reglas comunes

- Se respeta la constitución del proyecto (`.specify/memory/constitution.md`).
- Ninguno cambia archivos del otro sin un handoff aprobado; lo que no es suyo lo propone.
- Todo dato de plataforma (límites, precios, comportamiento) se verifica en la documentación vigente y se cita.
- Lo que depende de un servicio no configurado se declara bloqueado; no se simula ni se da por hecho.

## Primer CDU

**CDU-001 — Responder "¿En qué te ayudo?" por WhatsApp.** Brief inicial de la persona dueña, para que `analista-cdu` lo convierta en spec:

- **Flujo:** una persona escribe un mensaje a un número de WhatsApp Business; un agente de ElevenLabs le responde preguntando en qué la puede ayudar.
- **Piezas que el integrador debe cubrir:**
  - Cerebro: agente de ElevenLabs con un prompt que responde a este caso de uso.
  - Herramientas de integración con WhatsApp: importación del número y mensajería habilitada.
  - Conversaciones: comportamiento y análisis básico en el panel.
  - Despliegue: agente como código y entornos para desplegar.
  - Pruebas: tests del agente que validen el criterio de aceptación.
- **Fuera de este CDU:** FAQ y RAG, que serán un CDU posterior.
