# Handoff 004 — Que el propietario no entre al contexto del agente (sin backend propio)

- **De:** `analista-cdu`
- **A:** `integrador-elevenlabs-whatsapp`
- **CDU:** CDU-002 (`specs/002-consulta-vehiculo-por-patente/spec.md`, FR-003, Historia 4, "Impacto en la constitución")
- **Fecha:** 2026-10-18

## Necesidad o pregunta

Con la integración nativa y sin backend propio (Principio VIII), ¿se puede consultar una API de patentes de modo que el agente y los registros de ElevenLabs reciban **solo marca, modelo y año** y no el nombre ni el RUT del propietario? Si no se puede, ¿qué queda registrado exactamente y dónde, y dónde se guarda la clave de esa API sin violar el Principio IV?

## Contexto

- Hallazgo del descubrimiento, **sin probar** (la clave la está generando Christian): Boostr (`api.boostr.cl/vehicle/{PATENTE}.json`, clave en encabezado `X-API-KEY`) devolvería en su plan gratis patente, dígito verificador, marca, modelo, año, tipo, motor y nombre y RUT del propietario.
- Si esa respuesta completa entra a una herramienta del agente, quedaría en el contexto del modelo y en los registros de ElevenLabs. Una búsqueda por RUT identifica personas; la decisión del equipo es no diseñarla.
- La spec pide que el agente nunca muestre el propietario, pero que eso sea la última barrera y no la única (FR-003).
- El Principio VIII permite una herramienta externa solo si el plan la justifica; un backend propio exigiría enmienda.
- El Principio IV nombra solo `ELEVENLABS_API_KEY` y el Environment `POC`; la clave de la API de patentes es una credencial nueva.

## Propuesta

1. Verificar en la documentación vigente de ElevenLabs (y citarla) si una herramienta de servidor/webhook puede: (a) enviar la clave como encabezado secreto guardado en la plataforma y no en el repo; (b) limitar lo que el modelo recibe a campos concretos de la respuesta (por ejemplo, extrayéndolos a variables) sin que el resto llegue al modelo; (c) funcionar en el plan Starter y con WhatsApp.
2. Si existe ese mecanismo, usarlo y probarlo con una respuesta simulada que incluya nombre y RUT (SC-001 de la spec).
3. Si no existe, decir con claridad qué queda en contexto y en registros, para que Christian decida entre las opciones de la pregunta 8 de la spec (no construir; construir solo para pruebas propias; o enmienda para un backend mínimo). No hace falta que el integrador elija; sí que lo declare como bloqueo o limitación.
4. Indicar si los campos de análisis de conversación pueden configurarse para que no capturen la patente ni el resultado, y qué retención permite la plataforma (Starter).
5. Proponer en el plan dónde vive la clave de la API de patentes; la spec no define el mecanismo. Christian la maneja; no debe pasar por el chat ni por el repo.

## Respuesta

*(pendiente: la completa `integrador-elevenlabs-whatsapp`)*

## Decisión final

*(pendiente)*
