# Handoff 005 — Fallos, límites y pruebas de la consulta de patente

- **De:** `analista-cdu`
- **A:** `integrador-elevenlabs-whatsapp`
- **CDU:** CDU-002 (`specs/002-consulta-vehiculo-por-patente/spec.md`, Historia 3, SC-002, SC-004, SC-006)
- **Fecha:** 2026-10-18

## Necesidad o pregunta

Cuando la consulta de patente falla (sin resultado, error, tiempo agotado, límite excedido, respuesta inesperada), ¿qué puede hacer realmente el agente y cómo se prueban esos casos sin llamar a la API real ni usar patentes reales?

## Contexto

- Hallazgo, **sin probar**: el servicio candidato es gratuito "por ahora", en beta, con límite aproximado de 5 patentes cada 10 segundos, y puede cambiar sin aviso. Los fallos son esperables.
- La spec exige en cada fallo: mensaje simple sin códigos, ofrecer seguir sin la patente, no reintentar en bucle, no inventar datos, y que CDU-001 siga funcionando.
- La constitución (Principio II) pide pruebas del agente por cada criterio; el Principio VII prohíbe patentes y datos reales en el repo.

## Propuesta

1. Documentar qué ocurre en la plataforma cuando la herramienta devuelve error, expira o responde algo no esperado, y cuánto tiempo máximo se puede esperar; proponer el valor del tiempo máximo y si cabe un único reintento.
2. Probar cada modo de falla con respuestas simuladas de la herramienta (pruebas de uso de herramienta y de siguiente respuesta), de modo que AC-02 y AC-05 a AC-08 corran en CI sin llamar a la API real.
3. Usar patentes sintéticas con formato válido en las pruebas automáticas; decir en el plan cómo se evita que una patente sintética coincida con una real.
4. Confirmar si el agente puede comprobar el formato antes de llamar a la herramienta (por prompt) y cómo se verifica que no se llamó con formato inválido (SC-002).
5. Dar una estimación honesta de la latencia que añade la herramienta, o declararla no medible hasta tener la clave (SC-006).

## Respuesta

*(pendiente: la completa `integrador-elevenlabs-whatsapp`)*

## Decisión final

*(pendiente)*
