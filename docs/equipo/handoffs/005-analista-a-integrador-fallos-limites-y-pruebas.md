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

**Estado: respondido.** **De:** `integrador-elevenlabs-whatsapp` | **Fecha:** 2026-10-18 | **Fuente:** `docs/guias/cdu-002-integracion-consulta-patente.md`, secciones 3.2, 3.4, 7.2 y 9. Registrado aquí por `analista-cdu` a partir de esa guía. Nada está probado.

1. **Tiempo y reintentos:** tiempo máximo propuesto 10 s (rango permitido 5 a 300 s, por defecto 20), a calibrar con la latencia real; sin reintento automático. Los errores llegan al agente sin procesar para que distinga "no encontrada", "límite" y "caída"; el mensaje de cada caso (voseo, sin códigos) está en la sección 3.4 de la guía.
2. **Pruebas sin la API real:** simulaciones con respuestas de la herramienta simuladas, que cubren AC-02 y AC-05 a AC-08. Miden el comportamiento del prompt, no el filtro; el filtro se prueba en la Etapa 0.
3. **Patentes sintéticas:** nunca se envían a la API real; las pruebas automáticas usan respuestas simuladas o un JSON estático, así que no pueden coincidir con una persona real.
4. **Validación de formato:** por prompt; se comprueba con una prueba de uso de herramienta con expresión regular sobre el parámetro. Que "no se llamó" (SC-002) sea verificable queda por confirmar.
5. **Latencia:** no medible hasta tener la clave; se mide en la prueba real de Christian (SC-006).

**Aceptación del analista:** conforme. SC-002 acepta la expresión regular como evidencia y la prueba de "no se llamó" si la plataforma la permite; SC-006 sigue por probar.

## Decisión final

Se adoptan los valores y métodos de la guía (10 s sin reintento automático, simulaciones con mocks, regex sobre el parámetro). Reflejado en `specs/002-consulta-vehiculo-por-patente/spec.md` (Historia 3, SC-002, SC-006, FR-012).
