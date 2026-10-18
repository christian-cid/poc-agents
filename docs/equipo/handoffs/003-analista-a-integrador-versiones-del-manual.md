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

(vacía: abierto)

## Decisión final

(pendiente)
