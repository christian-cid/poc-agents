<!--
Sync Impact Report
- Version change: (plantilla sin ratificar) -> 1.0.0 -> 1.0.1 (PATCH: el despliegue usa la API REST y no el CLI; aprobado por Christian el 2026-10-18)
- Principios modificados: ninguno renombrado; la plantilla vacía se reemplaza por 8 principios nuevos (I-VIII)
- Secciones añadidas: Restricciones y alcance de la POC; Flujo de trabajo y gobernanza; Gobernanza
- Secciones eliminadas: ninguna (todos los marcadores de la plantilla fueron resueltos)
- Pendientes (TODO): ninguno. Los datos aún no definidos (idioma, tono, canal alternativo) se
  marcan [POR DEFINIR] en cada spec, no aquí.
- Este bloque es material temporal de revisión; se retira antes de hacer commit.
-->
# poc-agents Constitution

POC de un agente de WhatsApp construido con ElevenLabs que responde preguntas sobre el auto
(GWM Haval H6) únicamente desde su manual de usuario indexado con RAG, sin backend propio en el
camino crítico. Se construye con Spec-Driven Development (Spec Kit) y se despliega con GitHub
Actions y la API REST de ElevenLabs (el CLI no documenta aún el formato de agentes ni de conocimiento).

## Core Principles

### I. Todo es código versionado
El agente, la base de conocimiento y las pruebas MUST vivir en el repositorio: la configuración
del agente en `agent_configs/`, el conocimiento en `knowledge/`, las pruebas en `test_configs/` y
la automatización en `scripts/`. Nada se configura a mano en el panel de ElevenLabs sin quedar
reflejado en el repo en el mismo cambio; si el panel y el repo difieren, el repo manda.
*Razón:* lo que no está versionado no se puede revisar, reproducir ni revertir.

### II. Pruebas primero
Todo cambio de prompt, de conocimiento o de configuración del agente MUST pasar las pruebas del
agente (`elevenlabs agents test`, localmente y en CI) antes del merge. Un cambio nuevo MUST incluir
al menos una prueba que lo valide, escrita antes o junto con el cambio. Un criterio de aceptación
sin prueba del agente o sin chequeo manual descrito en la spec NO está terminado.
*Razón:* el comportamiento de un agente cambia con cualquier ajuste de texto; solo las pruebas
detectan regresiones.

### III. Respuestas fundamentadas en el manual
El agente MUST responder solo con lo que dice el manual indexado. Si no encuentra la respuesta, MUST
admitirlo y no inventar ni completar con conocimiento general. Las preguntas de seguridad del
vehículo (frenos, airbags, neumáticos, combustible, etc.) MUST responderse solo con lo que dice el
manual, nunca con suposiciones. Cada comportamiento de este principio MUST tener pruebas de caso
límite (pregunta sin respuesta en el manual, pregunta fuera de tema, pregunta de seguridad).
*Razón:* una respuesta inventada sobre un vehículo puede causar daño real.

### IV. Cero credenciales en el repo ni en el chat
`ELEVENLABS_API_KEY` MUST vivir solo en el secreto del Environment de GitHub llamado `POC`, y todo
job que la use MUST declarar `environment: POC`. Ninguna credencial MUST aparecer en archivos,
historial, logs, specs ni conversaciones con los agentes. Si una clave se expone, MUST revocarse y
rotarse de inmediato. Solo la persona dueña del proyecto crea cuentas y maneja credenciales.
*Razón:* una clave filtrada da control total del agente y consumo a costa del proyecto.

### V. Toda funcionalidad nace de una spec
Cada funcionalidad MUST originarse en una spec con criterios de aceptación medibles, un caso de
uso (CDU) por spec. Lo que no se sabe MUST marcarse `[POR DEFINIR]` y no suponerse. Plan, tareas e
implementación MUST poder rastrearse hasta un criterio de aceptación.
*Razón:* evita construir por intuición y permite verificar que "hecho" significa lo acordado.

### VI. Honestidad operativa
No se simula ni se da por hecho lo que no se probó contra el servicio real. Lo que depende de un
servicio no configurado MUST declararse bloqueado. Los datos de plataforma (límites, precios,
comportamiento de ElevenLabs o Meta) MUST verificarse en la documentación vigente y citarse con su
fuente. Los informes de avance MUST distinguir qué se probó de verdad y qué no.
*Razón:* los informes optimistas ocultan bloqueos y trasladan el riesgo a la demostración final.

### VII. Privacidad mínima
Solo se guardan datos de usuarios si la spec dice para qué. El repo MUST NOT contener datos
personales (números de teléfono, nombres, transcripciones reales); las pruebas usan datos
sintéticos. La retención y el análisis de conversaciones SHOULD limitarse a lo que un criterio de
aceptación requiere.
*Razón:* menos datos guardados significa menos exposición y menos obligaciones.

### VIII. Simplicidad
Se MUST usar la integración nativa de ElevenLabs con WhatsApp, sin backend propio, webhook propio
ni herramientas externas, hasta que un CDU demuestre con evidencia que es necesario. Añadir
complejidad MUST justificarse por escrito en el plan del CDU que la requiere.
*Razón:* es una POC; cada pieza propia es una pieza más que mantener, desplegar y asegurar.

## Restricciones y alcance de la POC

- **Plan:** ElevenLabs en plan Starter. Cualquier función que exija otro plan MUST tratarse como
  bloqueo y consultarse a la persona dueña antes de planificarla.
- **Número:** un número dedicado de WhatsApp Business para la POC, importado en ElevenLabs. No se
  usa un número personal ni uno con otro uso.
- **Fuera de alcance:** llamadas de voz, plantillas de mensajes salientes y traspaso a humano. Una
  spec que los necesite MUST abrir primero una enmienda de esta sección.
- **Fuente de conocimiento:** únicamente el manual de usuario del GWM Haval H6, indexado con RAG.
- **Despliegue:** GitHub Actions con la API REST de ElevenLabs (script Python, sin CLI); un solo entorno `POC` por ahora. `staging` y `main` quedan para cuando exista más de un entorno.

## Flujo de trabajo y gobernanza

- **Roles:** `analista-cdu` define el qué (spec); `integrador-elevenlabs-whatsapp` define el cómo
  (plan, tareas, implementación y pruebas). Se coordinan según `docs/equipo/COORDINACION.md`, y
  ninguno cambia archivos del otro sin un handoff aprobado.
- **Ciclo por CDU:** spec Propuesta -> revisión de viabilidad -> spec Aprobada -> plan y tareas ->
  implementación con pruebas -> verificación del analista -> Hecho.
- **Compuertas de calidad:** no se hace merge con pruebas del agente en rojo; no se despliega a
  `main` sin pasar por `staging`.
- **Decisiones de la persona dueña:** cuentas, planes, idioma, tono y canal alternativo se
  preguntan a la persona dueña y se registran en la spec o en un handoff.

## Governance

- **Supremacía:** esta constitución prevalece sobre cualquier otra práctica, plantilla o
  instrucción de los agentes. Si hay conflicto, se corrige el otro documento o se enmienda esta.
- **Enmiendas:** se proponen por cambio en este archivo con su motivo, impacto en specs y planes
  existentes, y la aprobación explícita de la persona dueña del proyecto. Una enmienda MUST
  actualizar la versión, la fecha de última modificación y, si aplica, los artefactos afectados.
- **Versionado semántico:** MAJOR para eliminar o redefinir un principio de forma incompatible;
  MINOR para añadir un principio o sección, o ampliar materialmente la guía; PATCH para
  aclaraciones y correcciones de redacción.
- **Revisión de cumplimiento:** cada `plan.md` MUST incluir una verificación contra los principios
  I-VIII (qué principio aplica y cómo se cumple); cada revisión de PR MUST confirmar el
  cumplimiento. Toda desviación MUST justificarse por escrito en el plan y aprobarse.

**Version**: 1.0.1 | **Ratified**: 2026-10-18 | **Last Amended**: 2026-10-18
