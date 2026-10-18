# Handoff 002 — Tipos de mensaje, ráfagas e inactividad

- **De:** `analista-cdu`
- **A:** `integrador-elevenlabs-whatsapp`
- **CDU:** CDU-001 (`specs/001-preguntas-manual-haval-h6/spec.md`, Historia 5)
- **Fecha:** 2026-10-18

## Necesidad o pregunta

¿Qué puede garantizar la integración nativa de WhatsApp con notas de voz, imágenes y otros adjuntos (documento, sticker, ubicación, contacto, video), con ráfagas de mensajes y con el cierre por inactividad, para fijar el comportamiento esperado en la spec?

## Contexto

- La guía (3.7, 4.1, 4.5) indica: la integración admite texto, audio, imagen, documento, sticker, ubicación y contacto, no video; las notas de voz generan cargos extra de voz; "Enable audio message response" viene activado por defecto; no hay agrupación de mensajes; el cierre por inactividad es de 15 minutos por defecto; la interpretación de fotos depende del modelo y está por verificar.
- No se sabe qué recibe el usuario si envía un tipo no soportado (por ejemplo video) ni si el agente puede responder en texto a una nota de voz entrante.

## Propuesta

La spec pide (Historia 5): respuestas siempre en texto; nota de voz entendida y respondida en texto si es viable, o rechazo amable pidiendo que escriban; fotos no tratadas como fuente de verdad (se pide describir la luz); respuesta corta ante tipos no soportados; cada mensaje de una ráfaga recibe respuesta coherente; conversación nueva tras 15 minutos sin mensaje de despedida.

Pregunto al integrador:

1. ¿Cuál de las dos variantes de nota de voz es viable con costo razonable en Starter?
2. ¿Qué sucede realmente con video y otros tipos (¿respuesta del agente, error visible, silencio)?
3. ¿Se puede limitar la mitigación de ráfagas a las instrucciones del agente, o hay otra opción nativa?
4. Confirmar si el cierre a los 15 minutos puede dejarse sin mensaje y que el siguiente mensaje abre conversación nueva sin memoria.

Con la respuesta, el analista ajusta los escenarios 1 a 5 de la Historia 5; lo que dependa de Christian (voz, fotos) se resuelve en sus preguntas abiertas.

## Respuesta

(vacía: abierto)

## Decisión final

(pendiente)
