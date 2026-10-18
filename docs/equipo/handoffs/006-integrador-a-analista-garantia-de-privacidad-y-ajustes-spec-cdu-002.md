# Handoff 006: Qué garantía de privacidad puede prometer la spec del CDU-002

- **De:** `integrador-elevenlabs-whatsapp`
- **A:** `analista-cdu`
- **CDU:** CDU-002 (`specs/002-consulta-vehiculo-por-patente/spec.md`: FR-003, FR-009, SC-001, SC-002, Historia 2 escenario 3)
- **Fecha:** 2026-10-18

## Necesidad o pregunta

Con lo que la plataforma permite y documenta, ¿aceptás reescribir FR-003 (y los criterios que dependen de él) en dos niveles, "el propietario no llega al modelo" (garantizable, por probar) y "no queda en ningún registro de la plataforma" (no garantizable ni documentado), y ajustar los criterios que el prompt no puede asegurar por sí solo?

## Contexto

Fuente completa y citas: `docs/guias/cdu-002-integracion-consulta-patente.md` (secciones 1, 2, 3 y 9). Nada está probado: no hay clave de Boostr ni se llamó a ElevenLabs.

- La API de ElevenLabs documenta, en una herramienta de servidor, un `response_filter` de lista permitida "applied to the response before the LLM sees it", con modo `allow` y rutas con puntos. Con eso, la herramienta puede entregar al modelo solo marca, modelo y año. Esto responde la pregunta de fondo del handoff 004 sin backend propio y sin enmienda.
- La documentación **no dice** si el dato filtrado queda fuera del transcript, del historial o de los registros internos (el campo `sanitize` de otra función sí menciona el transcript; el filtro no). La retención por defecto es de 2 años y es configurable; la disponibilidad por plan no está documentada.
- Lo que el prompt asegura es probabilístico. El tope de patentes (FR-009) no tiene contador: solo se aplica por prompt.
- Las pruebas de simulación con respuesta simulada de la herramienta miden la reacción del prompt; no demuestran que el filtro funcione. Para eso la guía propone una "Etapa 0" con un JSON sintético y un agente de prueba (sección 7.1).
- La validación de formato de patente solo se puede imponer por prompt; la documentación no muestra restricciones de patrón en el parámetro. "No se llamó" (SC-002) tiene una vía de prueba incierta.

## Propuesta

1. **FR-003** en dos partes: (a) MUST NOT llegar al modelo (mecanismo: filtro de la plataforma; verificado en la Etapa 0); (b) SHOULD NOT quedar en registros visibles del panel, con el resultado de la Etapa 0 documentado, y declarando que lo que ElevenLabs retiene internamente no está documentado. Si (a) falla, el CDU no se construye con Boostr.
2. **Pregunta 8 de la spec**: agregar la vía (d) "filtro de la plataforma", que no necesita enmienda. Las vías a/b/c quedan como respaldo.
3. **SC-001**: dividir en SC-001a (el modelo no recibe el propietario, medido en la Etapa 0) y SC-001b (con propietario simulado, 0 respuestas lo muestran, medido en conversaciones simuladas).
4. **Historia 2 escenario 3**: quitar el motor como pista en el MVP (el filtro lo deja fuera, igual que la pregunta 7); la variante se pregunta siempre.
5. **FR-009 / AC-15**: indicar que se aplica por prompt y que se verifica de forma probabilística (con repeticiones).
6. **SC-002**: aceptar la prueba de uso de herramienta con expresión regular sobre el parámetro como evidencia de formato correcto, y una prueba de "no se llamó" si la plataforma la permite (por verificar).
7. **Prompt**: avisar que el CDU-002 exige una excepción a la "Regla principal" de CDU-001 y re-ejecutar los 13 casos de CDU-001; el texto propuesto está en la sección 3.5 de la guía. El aviso de privacidad sigue siendo de Christian.

## Respuesta

**Estado: respondido.** **De:** `analista-cdu` | **Fecha:** 2026-10-18. Acepto los siete ajustes y quedaron aplicados en `specs/002-consulta-vehiculo-por-patente/spec.md`:

1. **FR-003** partido en niveles: (a) no llega al modelo (garantizable, se prueba en la Etapa 0); (b) no queda en registros visibles del panel (SHOULD, se documenta el resultado y no se promete lo que la plataforma retiene internamente); y un tercer nivel (c), la última barrera del prompt. Si (a) falla no se construye con este servicio.
2. **Pregunta 8**: Christian aceptó la vía de filtro de la plataforma (opción B); las vías anteriores quedan de respaldo. No se acepta la opción sin filtro.
3. **SC-001** desdoblado en SC-001a (Etapa 0, el modelo no recibe el propietario) y SC-001b (10 conversaciones simuladas, 0 respuestas lo muestran).
4. **Historia 2, escenario 3** y **FR-002**: el motor sale del MVP; la variante se pregunta siempre. Usar el motor como pista queda como mejora futura tras ver un valor real. La tabla de privacidad se ajustó.
5. **FR-009 y AC-15**: tope por prompt, verificación probabilística con repeticiones.
6. **SC-002**: la prueba de uso de herramienta con expresión regular es evidencia aceptada; la de "no se llamó" se acepta si la plataforma la permite (por verificar).
7. **Prompt**: nuevo **FR-013**: el CDU-002 exige una excepción a la "Regla principal" de CDU-001, la aprueba Christian, la redacta el integrador, y se re-ejecutan los 13 casos de CDU-001. El aviso de privacidad sigue siendo de Christian (pregunta 5, abierta).

Además, por la respuesta de Christian: país Chile, emergencias 131/132/133 como propuesta a confirmar (FR-014), y la spec 001 se actualizó en el mismo sentido. Nota para el integrador: el borrador de prompt de la guía (sección 3.5) usa voseo, coherente con lo aprobado.

## Decisión final

Ajustes del integrador aceptados y aplicados; sin desacuerdos. La spec CDU-002 queda en "Propuesta (decisiones parciales)".
