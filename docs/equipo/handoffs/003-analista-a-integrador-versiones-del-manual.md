# Handoff 003 — Versiones del manual y no mezclarlas

- **De:** `analista-cdu`
- **A:** `integrador-elevenlabs-whatsapp`
- **CDU:** CDU-001 (`specs/001-preguntas-manual-haval-h6/spec.md`, Historia 4)
- **Fecha:** 2026-10-18

## Necesidad o pregunta

¿Cómo se asegura que el agente no mezcle información de versiones distintas del Haval H6 y que pueda decir con exactitud qué versión cubre?

## Contexto

- La guía (sección 2, "Datos del PDF", y riesgo R7) indica que en gwm-mx.com existen otros manuales de H6 (`Haval-H6-PHEV-user-manual.pdf`, `H6FL-manual-2025.2.21.pdf`) y que el archivo pedido por Christian es `ManualUsuarioHAVALH6.pdf`. No se pudo abrir ninguno, así que no se sabe qué versión cubre cada uno ni si el pedido incluye varias variantes.
- La spec propone para CDU-001 un solo manual indexado y fuera de alcance los demás.

## Propuesta

1. Un solo PDF indexado, identificado en el contenido y en la configuración con nombre, versión/año y huella.
2. El agente responde la versión cubierta tal como figura en el manual, avisa una vez cuando la persona dice tener otra, y hace una pregunta aclaratoria cuando el manual distingue equipamientos dentro del mismo documento.
3. Si en el futuro hay más de un manual, será un CDU aparte (otro agente o separación clara por versión), no una mezcla dentro de este.

Pregunto al integrador:

1. ¿Es viable que el agente cite con exactitud la versión indexada (por ejemplo desde un archivo de contexto pequeño en la base de conocimiento)?
2. ¿Hay algún riesgo técnico de que al indexar un solo PDF con secciones por variante la recuperación mezcle datos de variantes? ¿Cómo se prueba (propuesta de prueba: una pregunta cuyo valor difiere entre variantes)?

## Respuesta

**De:** `integrador-elevenlabs-whatsapp` | **Fecha:** 2026-10-18 | **Base:** el PDF real procesado con `scripts/extract_manual.py` (ver `knowledge/manual-h6/LEEME.md`). El comportamiento del agente no se probó: no hay clave ni agente en ElevenLabs.

**Qué es el PDF.** Un solo manual, edición **2021.12** (portada `2021.12- X HAVAL H6`; introducción fechada **06/09/2021**), 299 páginas, 3 643 293 bytes, sha256 `7fe9fd8efd0ed56ca8b2702bfad3bb25cf7e799d2ae96921ec33ddef8bc2aa7b`. Christian confirmó que su auto es del 2021: coincide. Medido sobre el texto: 0 menciones de HEV, PHEV, híbrido o México; la transmisión es DCT de 7 velocidades (GW7DCT1/2-A02 y HT7DCT1-A02). Los otros manuales de la guía (`Haval-H6-PHEV-user-manual.pdf`, `H6FL-manual-2025.2.21.pdf`) no se tocaron.

1. **¿Puede el agente citar la versión exacta? Sí, viable.** La edición queda en el front matter de los 33 archivos (`fuente: ManualUsuarioHAVALH6, edición 2021-12 (introducción fechada 06/09/2021)`) y la portada y la fecha de la introducción están en `00-introduccion-y-consejos-de-seguridad.md`. No hace falta un archivo de contexto aparte. El nombre y la huella del PDF viven en `_cobertura.json`, no en el texto indexado, para no ensuciar la recuperación. **Pendiente de plataforma:** que el agente conteste "edición 2021.12" al preguntarle por la versión, y para que no dependa de la recuperación, conviene que el system prompt lo repita en una frase (el borrador v0.1 ya menciona la edición 2021).
2. **Riesgo de mezcla: existe, pero entre variantes DENTRO del manual, no entre manuales.** El mismo PDF cubre dos motores (GW4N20: 150 kW; GW4B15D: 110 kW), tracción en dos o cuatro ruedas, dos cajas DCT, equipamiento "por país" (el texto de combustible distingue "EAU, Qatar, … Australia" de "otras regiones") y volante a la izquierda o a la derecha. El propio manual avisa que no todo el equipamiento está instalado en cada auto (aviso repetido 62 veces; se conservó la versión de la p. impresa 2). Como las filas de las tablas llevan el modelo en cada registro (por ejemplo `Modelo de motor: GW4N20; …: 5,0±0,1` frente a `GW4B15D; …: 4,0±0,1`), la recuperación puede devolver ambas; el agente debe pedir el motor o dar los dos valores etiquetados, no uno solo.
3. **Prueba propuesta (por ejecutar cuando haya plataforma).** Next Reply: "¿Cuánto aceite lleva el motor?" y "¿Cuántos caballos o kW tiene?". Éxito: el agente da los valores de GW4N20 y de GW4B15D con su etiqueta, o pregunta el motor primero. Fallo: da un solo valor sin decir de qué motor. Segunda prueba: "¿Mi auto es híbrido?" debe admitir que el manual no menciona versiones híbridas (0 menciones).
4. **El manual no distingue años dentro del documento.** No hay datos "por año" que mezclar; si la persona dice tener otro año, vale la regla de la propuesta (aviso una sola vez).

## Decisión final

Un solo manual (edición 2021.12), con la edición en cada archivo indexado; el riesgo de mezcla es entre variantes dentro del manual (motor, tracción, caja, región) y se cubre con pregunta aclaratoria y la prueba del punto 3, pendiente de plataforma. No se modificó `spec.md`.
