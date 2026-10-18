# Handoff 001 — Cobertura: tablas, imágenes y límite de 2 MB

- **De:** `analista-cdu`
- **A:** `integrador-elevenlabs-whatsapp`
- **CDU:** CDU-001 (`specs/001-preguntas-manual-haval-h6/spec.md`)
- **Fecha:** 2026-10-18

## Necesidad o pregunta

¿Es viable que el agente reproduzca con exactitud las tablas del manual (especificaciones, presiones, intervalos) y las luces del tablero cuando parte de esa información está en imágenes, y que se pueda demostrar que "se indexó todo" dentro del límite de 2 MB de indexado del plan Starter?

## Contexto

- La guía (secciones 3.5 a 3.8 y 3.10) propone convertir tablas a markdown, no indexar imágenes, remitir a "ver página N" cuando la información solo esté en una figura, y medir cobertura por página, títulos, bytes y recuperación.
- Starter indexa 2 MB y se comparte entre producción y staging; qué ocurre al excederlo no está documentado (guía 3.8).
- El PDF aún no se pudo leer: no se conocen tamaño, texto seleccionable ni número de tablas o luces.
- La spec exige: valores numéricos exactos (SC-004), 100 % de páginas clasificadas (SC-006) y capítulos faltantes declarados (Historia 6).

## Propuesta

1. El analista define el resultado: el agente da el valor y la unidad exactos o dice que no los encuentra; para información solo gráfica remite a la página del manual sin describir lo que no se ve.
2. Si el integrador confirma que es viable, la spec se mantiene. Si no lo es para algún tipo de contenido (por ejemplo símbolos de luces), el analista declara la limitación en la spec y la lista como fuera de cobertura.
3. Para el límite de tamaño, el analista pide a Christian decidir entre recortar por prioridad o subir de plan una vez conocido el tamaño del texto limpio (la regla de la guía 3.8 le sirve como base).
4. Pide al integrador: confirmar si el informe de cobertura propuesto (guía 3.10) es suficiente para demostrar SC-006, y entregar al analista el tamaño real del texto limpio cuando tenga el PDF.

## Respuesta

**De:** `integrador-elevenlabs-whatsapp` | **Fecha:** 2026-10-18 | **Base:** el PDF real (`manual-haval-h6_compressed.pdf`, 299 páginas, sha256 `7fe9fd8e…aa7b`), procesado con `scripts/extract_manual.py`. Detalle en `knowledge/manual-h6/LEEME.md` y `knowledge/manual-h6/_cobertura.json`. Nada de esto se probó todavía contra ElevenLabs (sin clave): lo que sigue habla del texto preparado, no del agente.

1. **Tablas: viable, con una forma distinta a la propuesta.** El PDF tiene 28 tablas en 18 páginas (PDF 44, 106, 118, 125, 127, 201-204, 228, 229, 237, 261, 289-293). Tienen celdas combinadas, así que no se convirtieron a tablas markdown sino a registros "Campo: valor" por fila, con la cabecera repetida (guía 3.5, variante "lista campo: valor"). Ejemplo real: `Ítem: Especificaciones › Rueda de repuesto; Datos: T135/90 R17 104M`. Se compararon contra la imagen del PDF las tablas de combustible, secuencia de encendido, radar, iconos de la pantalla, sillas infantiles y especificaciones del capítulo 7, y diez valores quedaron fijados en pruebas (`scripts/tests`). **La revisión humana de los números de esas 18 páginas que exige SC-004 sigue pendiente**; el integrador no la da por hecha. El manual **no trae la presión recomendada de neumáticos como cifra**: la tabla dice "Véase la etiqueta de presión de neumáticos en el pilar central" (PDF 290, p. impresa 287). La prueba T2 de la guía debe esperar esa respuesta, no una cifra (en otras secciones solo aparecen kPa para casos concretos, como estacionamiento prolongado).
2. **Luces del tablero: viable solo con nombre, significado y acción; el icono no.** Son 40 luces (PDF 183-191, p. impresas 180-188). El texto las trae completas, por título en negrita y descripción, y quedaron como una sección por luz. Los iconos son dibujos vectoriales, no imágenes extraíbles (`pdfimages` no los lista) y no están en el texto. El agente puede explicar una luz si la persona dice su nombre o describe su significado, pero no puede reconocerla por su forma. Declarar esa limitación en la spec. Añadir descripciones del icono redactadas por el equipo es posible, pero exige revisar las imágenes a mano y la aprobación de Christian (guía 3.7); no se hizo.
3. **Información solo gráfica: se remite a la página, sin describirla.** Hay 185 códigos de figura en 121 páginas. En el texto aparece `[figura no incluida]` una vez por sección, nada se describe, y las remisiones del manual se conservan como `(ver p. N)` con número de página impreso (los 238 enlaces del PDF coinciden con N+3). El agente debe responder "ver página N del manual", como propone el analista.
4. **Límite de 2 MB: no es problema.** El manual completo, limpio y troceado, ocupa **476 717 bytes** en 33 archivos de 7 a 30 KB, el 23,8 % del límite de Starter. Producción y staging completos sumarían ~0,95 MB (< 2 MB). Con la regla de la guía 3.8 (≤ 1,6 MB) basta la opción A: no hace falta recortar capítulos ni subir de plan. Fuente verificada hoy: [RAG, usage limits](https://elevenlabs.io/docs/eleven-agents/customization/knowledge-base/rag): Starter 2 MB, medido sobre el tamaño original de los archivos, y los documentos de menos de 500 bytes no se indexan (se usan en el prompt). La página no dice qué pasa al exceder el límite; no hace falta probarlo con este tamaño.
5. **¿Basta el informe de cobertura para SC-006?** Para la parte "100 % de las páginas clasificadas": sí. `_cobertura.json` clasifica las 299 páginas: 295 con texto ubicadas en documentos, 4 sin contenido (PDF 2, 3, 241, 285), 0 sin ubicar, y por página `entrada = conservado + descartado` y salida completa. No cubre aún la guía 3.10 puntos 3, 4 y 6 (tamaño que reporta la API, recuperación con "Search knowledge base", pruebas del agente): están bloqueados por la clave. Capítulos faltantes: ninguno, los 8 capítulos y las 67 secciones del índice están presentes; nada se recortó. No se comparó cada subtítulo con el índice, solo los títulos de sección.
6. **Datos medidos que corrigen supuestos** (por si la spec los repite): de las "10 páginas sin texto" solo 4 están vacías (la 1 es portada y la 9, 11, 52, 91 y 233 tienen texto real que sí se conservó); el desfase PDF a página impresa es **+3** (no +2) en las 296 páginas numeradas; el manual dice "Great Wall" para el servicio, no "GWM".

Datos para completar los `<del manual>` de la spec: 8 capítulos (Operación p. 18; Conducción p. 89; Sistema audiovisual p. 194; Seguridad p. 212; Situaciones de Emergencia p. 240; Mantenimiento p. 262; Datos Técnicos p. 284; Índice p. 292, números impresos); edición 2021.12, introducción del 06/09/2021.

## Decisión final

Viable con limitaciones declaradas: tablas como registros "Campo: valor" (números por revisar a mano, SC-004 pendiente), luces solo por nombre y significado (icono fuera de cobertura), figuras remitidas por página, y el manual completo cabe en Starter sin recorte. Esta respuesta no modifica `spec.md`; la actualización de la spec queda en manos del analista.
