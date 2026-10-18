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

(vacía: abierto)

## Decisión final

(pendiente)
