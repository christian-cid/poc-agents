# Especificación: CDU-001 — Preguntas sobre mi auto (GWM Haval H6) por WhatsApp

**Rama**: trabajamos sobre `main` (no se crea rama para este CDU)

**Creado**: 2026-10-18

**Estado**: Propuesta

**Autor**: `analista-cdu`. Revisión de viabilidad pendiente: `integrador-elevenlabs-whatsapp`.

**Entrada**: decisión de la persona dueña (Christian): una persona escribe por WhatsApp al número del agente y el agente responde preguntas sobre su GWM Haval H6 usando únicamente el manual de usuario oficial (PDF publicado en gwm-mx.com), indexado en la base de conocimiento de un agente de ElevenLabs.

**Reemplaza**: el brief anterior de CDU-001 en `docs/equipo/COORDINACION.md` ("¿En qué te ayudo?"). Ese saludo queda como parte del flujo (primer mensaje, historia 1). La sección "Primer CDU" de COORDINACION.md debe actualizarse (la edita quien sea dueño de ese archivo; ver "Dudas para el integrador").

**País del servicio**: Chile (Respuesta de Christian, 2026-10-18; ver "Registro de decisiones"). Español de Chile con voseo (ya aprobado para el agente). El manual indexado es el mismo de GWM; el PDF se publica en gwm-mx.com, dato que se mantiene solo como origen del archivo.

**Contexto fijo**: plan Starter de ElevenLabs, un solo número de WhatsApp dedicado, sin backend propio, solo texto salvo que Christian decida otra cosa. Contexto técnico en `docs/guias/cdu-001-servicios-y-configuracion.md` (del integrador; esta spec define el qué, no el cómo).

**Aviso de verificación**: el PDF del manual todavía no se pudo descargar ni leer. Esta spec no afirma nada sobre su contenido (capítulos, cifras, versión, tablas). Donde falta el dato real aparece `<del manual>`; se completa al revisar el PDF y antes de pasar a Aprobada. Los datos de plataforma citados vienen de la guía del integrador y siguen "por verificar" hasta que él los confirme.

## Problema y usuario

**Quién**: una persona que tiene (o está por comprar) un GWM Haval H6 en Chile y tiene una duda mientras usa el auto o en casa.

**Problema**: el manual es un PDF largo; encontrar cómo se hace algo, qué significa una luz del tablero o qué dato técnico aplica cuesta tiempo, y en una situación con riesgo (una luz roja, olor a gasolina) cuesta más.

**Resultado esperado**: la persona escribe su duda en lenguaje natural por WhatsApp y recibe, en segundos, una respuesta corta, correcta y respaldada por el manual, o una admisión honesta de que el manual no lo cubre.

**Principio rector**: un "no lo encuentro en el manual" es siempre mejor que una respuesta inventada o con base débil, especialmente en temas de seguridad.

## Escenarios de usuario y pruebas *(obligatorio)*

### Historia 1 — Saludo y primera pregunta respondida con el manual (Prioridad: P1)

La persona escribe "Hola" o directamente una pregunta. El agente saluda con una frase corta, pregunta en qué puede ayudar (si la persona solo saludó) y responde las preguntas del manual con mensajes breves aptos para WhatsApp, indicando de dónde sale la información.

**Por qué P1**: es el valor central del CDU y el mínimo entregable: sin esto no hay producto.

**Prueba independiente**: desde otro teléfono, escribir "Hola" y luego una pregunta cuya respuesta se conoce del manual (`<pregunta de procedimiento simple del manual>`). Se verifica la respuesta contra el PDF.

**Escenarios de aceptación**:

1. **Dado** una persona que nunca ha escrito al número, **cuando** escribe "Hola", **entonces** el agente responde en un solo mensaje de máximo 2 frases: saluda, dice que ayuda con dudas del manual del Haval H6 y pregunta en qué puede ayudar.
2. **Dado** una persona que escribe directamente una pregunta cubierta por el manual (sin saludar), **cuando** envía el mensaje, **entonces** el agente responde la pregunta sin exigir saludo previo y sin repetir el saludo largo.
3. **Dado** una pregunta cuya respuesta está en el manual, **cuando** el agente responde, **entonces** el contenido coincide con el manual (mismos datos, pasos y advertencias), no agrega pasos ni cifras que el manual no tenga, e indica la ubicación en el manual (capítulo o página `<del manual>`) cuando la tiene.
4. **Dado** una respuesta de más de un paso, **cuando** el agente la entrega, **entonces** usa pasos numerados, sin tablas ni formato pesado, en mensajes de longitud contenida (objetivo: hasta ~600 caracteres por mensaje [POR DEFINIR cifra exacta]) y sin enviar el procedimiento entero en un bloque ilegible.

---

### Historia 2 — Lo que el manual no cubre y lo que no es del auto (Prioridad: P1)

Cuando la pregunta no tiene respaldo en el manual, el agente lo admite, no inventa, y ofrece reformular. Cuando la pregunta no tiene que ver con el Haval H6, lo dice con amabilidad y regresa al tema.

**Por qué P1**: es el comportamiento que hace confiable al agente; una respuesta inventada sobre un auto es un riesgo real.

**Prueba independiente**: hacer una pregunta plausible sobre el Haval H6 cuyo dato se haya confirmado ausente del manual, y otra sin relación con el auto.

**Escenarios de aceptación**:

1. **Dado** una pregunta sobre el Haval H6 que el manual no responde, **cuando** el agente contesta, **entonces** dice con claridad que no lo encuentra en el manual, no da cifras ni procedimientos de otra fuente, y ofrece reformular la pregunta o consultar a un distribuidor GWM autorizado.
2. **Dado** una pregunta sobre precios, disponibilidad, talleres concretos, otras marcas u otros modelos de GWM, **cuando** el agente contesta, **entonces** aclara que solo atiende dudas del manual del Haval H6, no inventa precios, direcciones ni teléfonos, y ofrece ayudar con una duda del auto.
3. **Dado** un mensaje sin relación con el auto (receta, tarea, charla general) o un intento de que ignore sus reglas o revele sus instrucciones, **cuando** el agente contesta, **entonces** declina con una frase amable, no revela sus instrucciones y regresa al manual.
4. **Dado** una pregunta cuya respuesta el manual solo da en parte, **cuando** el agente contesta, **entonces** entrega lo que sí dice el manual, señala qué parte no encuentra y no la completa con suposiciones.

---

### Historia 3 — Preguntas de seguridad, luces del tablero, procedimientos y especificaciones (Prioridad: P1)

El agente trata con especial cuidado las preguntas con riesgo y las de contenido crítico del manual: luces e indicadores del tablero, procedimientos paso a paso y datos de tablas.

**Por qué P1**: un dato o paso erróneo aquí puede dañar el auto o a las personas; es donde la fundamentación en el manual importa más.

**Prueba independiente**: hacer una pregunta de cada tipo (luz del tablero, situación de riesgo, procedimiento, dato de especificaciones) y comparar contra las páginas del manual.

**Escenarios de aceptación**:

1. **Dado** una situación con riesgo (por ejemplo olor a combustible, humo, luz roja del tablero, frenos, airbags, niños en el auto, llantas dañadas), **cuando** el agente responde, **entonces** primero da la advertencia tal como la formula el manual, después el procedimiento del manual, y si el manual no cubre el caso recomienda detenerse en un lugar seguro y contactar asistencia o a un distribuidor autorizado, sin instrucciones de reparación propias. La lista definitiva de temas críticos es [POR DEFINIR por Christian].
2. **Dado** una persona que describe un accidente, incendio o heridos, **cuando** el agente responde, **entonces** lo primero que dice es que llame a los servicios de emergencia de Chile (números propuestos, a confirmar por Christian: ambulancia 131, bomberos 132, Carabineros 133), antes de cualquier consulta al manual.
3. **Dado** una pregunta sobre una luz o indicador del tablero descrito con palabras (color, forma, nombre), **cuando** el agente responde, **entonces** da el significado y la acción indicados por el manual para esa luz; si la descripción coincide con más de una luz, hace una pregunta aclaratoria (color o símbolo) antes de responder; si el manual no la describe, lo dice.
4. **Dado** una pregunta sobre un procedimiento con varios pasos, **cuando** el agente responde, **entonces** respeta el orden del manual, no omite advertencias intercaladas y, si es largo, lo divide en mensajes coherentes sin cortar un paso a la mitad.
5. **Dado** una pregunta que se responde con una tabla del manual (por ejemplo especificaciones, presiones, capacidades, intervalos de servicio `<del manual>`), **cuando** el agente responde, **entonces** da el valor y la unidad exactos del manual con sus condiciones (por ejemplo carga o medida de llanta), sin redondear, convertir ni estimar; si el valor depende de una condición que la persona no dijo, pregunta por ella.
6. **Dado** una respuesta de seguridad, **cuando** se evalúa, **entonces** no contiene ninguna afirmación que no esté en el manual (verificable cotejando cada afirmación con el PDF).

---

### Historia 4 — Versión o año del vehículo ambiguo (Prioridad: P2)

Existen manuales distintos de "Haval H6" (por ejemplo otras variantes o actualizaciones de modelo; ver riesgo R7 de la guía). La persona puede tener un auto de otra versión que la del manual indexado. El agente no mezcla versiones.

**Por qué P2**: evita respuestas válidas para otro auto, pero no bloquea el flujo básico.

**Prueba independiente**: preguntar un dato diciendo que el auto es de una versión distinta a la indexada; preguntar cuál versión cubre el agente.

**Escenarios de aceptación**:

1. **Dado** que solo hay un manual indexado (versión/año `<del manual>`), **cuando** la persona pregunta qué auto cubre el agente, **entonces** responde con esa versión exactamente como figura en el manual y no afirma cubrir otras.
2. **Dado** una persona que dice tener un Haval H6 de otra versión, año o motorización que la indexada (por ejemplo híbrido o PHEV si el manual no los cubre), **cuando** pregunta algo, **entonces** el agente avisa una vez que su información corresponde a la versión `<del manual>` y que puede no aplicar a su auto, y recomienda confirmar con un distribuidor autorizado; no mezcla datos de otras versiones.
3. **Dado** que el manual distingue equipamiento o versiones dentro de un mismo documento (por ejemplo según motor o paquete), **cuando** la respuesta depende de eso y la persona no lo dijo, **entonces** el agente hace una sola pregunta aclaratoria y luego responde.

---

### Historia 5 — Tipos de mensaje, ráfagas e inactividad (Prioridad: P2)

La persona puede enviar notas de voz, fotos u otros adjuntos, varios mensajes seguidos, o dejar la conversación abierta y volver más tarde.

**Por qué P2**: son situaciones habituales en WhatsApp; el agente debe comportarse de forma predecible aunque no resuelva todo.

**Prueba independiente**: desde un teléfono real, enviar una nota de voz, una foto del tablero, tres mensajes seguidos, y esperar 15 minutos sin escribir.

**Escenarios de aceptación**:

1. **Dado** una nota de voz con una pregunta, **cuando** llega al número, **entonces** el comportamiento es el de la opción que decida Christian [POR DEFINIR, ver Preguntas abiertas]. Propuesta: el agente la entiende si la plataforma lo permite y responde **siempre en texto**; si no la puede entender, pide que la persona escriba su pregunta. En ningún caso responde con una nota de voz mientras no se decida lo contrario.
2. **Dado** una foto (por ejemplo del tablero), **cuando** llega al número, **entonces** el comportamiento por defecto propuesto es no tratar la foto como fuente de verdad y pedir que describa con palabras la luz o el problema [POR DEFINIR por Christian si se permite interpretar fotos; depende además de lo que el integrador confirme].
3. **Dado** otro tipo de mensaje (documento, sticker, ubicación, contacto, video), **cuando** llega, **entonces** el agente responde una frase corta diciendo que solo puede ayudar con preguntas escritas sobre el manual y las invita a escribir su duda; no queda sin respuesta ni responde con error visible.
4. **Dado** una ráfaga de varios mensajes enviados en pocos segundos (WhatsApp no los agrupa), **cuando** llegan, **entonces** cada mensaje recibe una respuesta; las respuestas son breves, no se contradicen entre sí ni repiten el saludo, y si los mensajes forman una sola pregunta partida, la respuesta final integra todo lo dicho.
5. **Dado** una conversación sin actividad durante 15 minutos (valor por defecto de la plataforma), **cuando** la persona escribe de nuevo, **entonces** se abre una conversación nueva: el agente no depende de lo hablado antes y, si la persona solo saluda, la recibe con el saludo del primer mensaje. El cierre por inactividad no envía mensaje de despedida salvo que Christian defina uno [POR DEFINIR].
6. **Dado** que la persona se despide ("gracias, es todo"), **cuando** el agente responde, **entonces** cierra con una frase corta de despedida y la conversación puede darse por terminada.

---

### Historia 6 — Cobertura del conocimiento: "se indexó todo el manual" (Prioridad: P1)

El negocio necesita poder afirmar con evidencia que el manual completo está disponible para el agente, o saber con exactitud qué parte falta.

**Por qué P1**: sin esta verificación, un "no lo encuentro" puede deberse a que el contenido nunca se cargó y no a que el manual no lo trae.

**Prueba independiente**: revisar el informe de cobertura y ejecutar la muestra de preguntas descrita abajo.

**Escenarios de aceptación**:

1. **Dado** el PDF fuente identificado por nombre, versión y huella única, **cuando** se revisa la cobertura, **entonces** el 100 % de las páginas del PDF figura como incluida u omitida con motivo (por ejemplo portada, página en blanco, solo imagen); ninguna página queda sin clasificar.
2. **Dado** el índice del manual, **cuando** se compara con lo cargado, **entonces** el 100 % de los capítulos y secciones del índice tiene contenido consultable por el agente; si hubo que recortar por el límite de tamaño del plan, el informe lista exactamente qué capítulos faltan y el agente no promete cubrirlos.
3. **Dado** una muestra de preguntas con respuesta conocida (al menos 1 por capítulo del manual y todas las del conjunto de los escenarios de las historias 1 a 3), **cuando** se hacen al agente, **entonces** al menos el 90 % se responde con el dato correcto del manual [POR DEFINIR umbral: Christian puede exigir otro]; cada falla se registra y se corrige o se declara como limitación.
4. **Dado** los contenidos críticos (todas las luces e indicadores del tablero, todas las advertencias de seguridad y todas las tablas numéricas), **cuando** una persona los revisa contra el PDF, **entonces** el 100 % de los datos numéricos revisados coincide con el manual (un dato numérico erróneo cuenta como falla).

## Casos límite

- Pregunta en inglés u otro idioma: [POR DEFINIR]. Propuesta: responder en español; si la persona insiste en inglés, responder en inglés sin cambiar cifras ni unidades del manual.
- Pregunta con faltas de ortografía, jerga o mensaje muy corto ("luz roja batería"): el agente interpreta la intención razonable y, si no puede, pide una aclaración.
- Mensaje vacío, solo emojis o sin sentido: una frase invitando a escribir la pregunta.
- Pregunta de varios temas en un mismo mensaje: responde por partes, en orden, o pide empezar por uno si sería demasiado largo.
- Persona que pide diagnóstico o reparación fuera de lo que cubre el manual: el agente no diagnostica; remite a un distribuidor autorizado.
- Persona que insiste tras un "no lo encuentro": el agente mantiene su respuesta, no cede ni inventa, y ofrece reformular o ir al distribuidor.
- Persona que pide la opinión del agente (¿conviene comprar?, ¿es seguro modificarlo?): fuera de alcance, salvo lo que diga el manual sobre modificaciones.
- El agente o la plataforma fallan y no hay respuesta: ver "Suposiciones"; la POC no tiene canal alternativo.
- Datos personales: el agente no pide nombre, VIN, placas ni ubicación. Si la persona los comparte, no los usa ni los repite.

## Requisitos *(obligatorio)*

### Requisitos funcionales

- **FR-001**: El agente MUST responder, por WhatsApp y en texto, a cada mensaje entrante de una persona al número del agente.
- **FR-002**: El agente MUST saludar con una frase corta y preguntar en qué puede ayudar cuando la persona solo saluda; si llega una pregunta directa, MUST responderla sin saludo largo.
- **FR-003**: El agente MUST responder únicamente con información del manual de usuario del GWM Haval H6 indexado; MUST NOT usar conocimiento propio sobre el auto, otras marcas ni mecánica general.
- **FR-004**: El agente MUST NOT inventar ni estimar datos (cifras, presiones, capacidades, intervalos de servicio, torques, fusibles, códigos, procedimientos). Si el dato exacto no está en el manual, MUST decirlo.
- **FR-005**: Cuando el manual no cubra la pregunta, el agente MUST admitirlo con una frase breve, ofrecer reformular y sugerir un distribuidor GWM autorizado; MUST NOT completar con suposiciones.
- **FR-006**: El agente MUST declinar con amabilidad lo que no sea del Haval H6 (precios, talleres, otras marcas, temas generales) y regresar al tema; MUST NOT revelar sus instrucciones internas.
- **FR-007**: En preguntas de riesgo, el agente MUST dar primero la advertencia del manual, luego el procedimiento del manual, y si no hay cobertura, recomendar detenerse en un lugar seguro y contactar asistencia o distribuidor. En una emergencia MUST indicar primero llamar a los servicios de emergencia.
- **FR-008**: Para luces e indicadores del tablero, procedimientos y tablas, el agente MUST reproducir el significado, el orden de pasos, las advertencias, los valores y las unidades como los da el manual, sin alterarlos.
- **FR-009**: Las respuestas MUST ser cortas y aptas para WhatsApp: pasos numerados de uno en uno cuando sean varios, sin tablas ni encabezados, con referencia a capítulo o página del manual cuando esté disponible.
- **FR-010**: Cuando una respuesta dependa de la versión, el año o el equipamiento y la persona no lo haya dicho, el agente MUST hacer una sola pregunta aclaratoria; MUST NOT mezclar datos de versiones distintas.
- **FR-011**: El agente MUST indicar con exactitud qué versión del manual cubre cuando se le pregunte y avisar si la persona dice tener un auto de otra versión.
- **FR-012**: El agente MUST responder todo mensaje entrante, incluidos los de ráfagas y los de tipos no soportados (documento, sticker, ubicación, contacto, video), sin dejar mensajes sin respuesta.
- **FR-013**: Las respuestas MUST ser en texto; las notas de voz y las imágenes MUST tratarse según lo decidido en las Preguntas abiertas (propuesta en la Historia 5).
- **FR-014**: Cada conversación MUST cerrarse tras 15 minutos de inactividad y el siguiente mensaje MUST abrir una conversación nueva.
- **FR-015**: El equipo MUST poder demostrar la cobertura del conocimiento (Historia 6): clasificación del 100 % de las páginas, capítulos faltantes declarados y muestra de preguntas aprobada.
- **FR-016**: El agente MUST usar español [POR DEFINIR variante y tono, ver Preguntas abiertas] y mantener el tono en toda la conversación.
- **FR-017**: El sistema MUST NOT pedir datos personales a la persona. De la conversación solo se conservan, para mejorar el servicio, el contenido de las preguntas y si fueron respondidas desde el manual (para detectar huecos de cobertura y mala fundamentación). Número de teléfono y mensajes los procesa la plataforma de ElevenLabs y Meta; el aviso a la persona usuaria es [POR DEFINIR].

### Entidades clave

- **Persona usuaria**: quien escribe por WhatsApp; se identifica solo por su conversación. No se le piden datos.
- **Conversación**: serie de mensajes con 15 minutos de inactividad como límite; no hay memoria entre conversaciones.
- **Manual de usuario (fuente única)**: PDF del GWM Haval H6 de gwm-mx.com, con nombre, versión/año `<del manual>` y huella única registrada. No se redistribuye al usuario.
- **Pregunta sin cobertura**: pregunta que el agente no pudo responder desde el manual; se registra para decidir si se amplía el conocimiento.
- **Informe de cobertura**: constancia por página y capítulo de lo cargado, lo omitido (con motivo) y lo recortado.

## Criterios de éxito *(obligatorio)*

Cada criterio se verifica con una conversación real o una prueba del agente. Los umbrales marcados se confirman con Christian antes de pasar a Aprobada.

### Resultados medibles

- **SC-001**: En una prueba de al menos 10 preguntas con respuesta conocida en el manual, al menos 9 (90 %) reciben un dato correcto y coherente con el PDF.
- **SC-002**: En una prueba de al menos 5 preguntas cuya respuesta no está en el manual, el 100 % recibe una admisión de que no se encuentra y 0 contienen datos inventados.
- **SC-003**: En una prueba de al menos 5 preguntas de riesgo, el 100 % muestra primero la advertencia o la indicación de seguridad y 0 contienen instrucciones ajenas al manual.
- **SC-004**: El 100 % de los datos numéricos de tablas revisados (presiones, capacidades, intervalos, etc.) coincide exactamente con el PDF.
- **SC-005**: El 100 % de los mensajes de prueba, incluidos los de tipos no soportados y los de ráfagas, recibe una respuesta.
- **SC-006**: El 100 % de las páginas del PDF está clasificado en el informe de cobertura y la lista de capítulos no cargados está vacía, o cada uno está declarado y aprobado por Christian.
- **SC-007**: Una respuesta típica llega en menos de [POR DEFINIR: propuesta 15 segundos] desde que la persona envía el mensaje, medido en una muestra de al menos 10 mensajes reales.
- **SC-008**: El 100 % de las respuestas de la muestra cumple el formato WhatsApp (sin tablas, en el límite de longitud acordado, pasos numerados).

## Escenarios de aceptación consolidados (verificación)

Resumen de pruebas de aceptación para que el integrador las convierta en pruebas del agente o en chequeos manuales. Los textos con `<...>` se rellenan viendo el PDF.

| ID | Dado | Cuando | Entonces |
| --- | --- | --- | --- |
| AC-01 | Persona nueva | Escribe "Hola" | Saludo de máximo 2 frases y pregunta en qué ayudar |
| AC-02 | Pregunta de procedimiento simple del manual | Pregunta `<del manual>` | Pasos numerados idénticos al manual, con referencia de capítulo o página, sin pasos extra |
| AC-03 | Pregunta de un dato de tabla `<del manual>` | Pregunta por el valor | Valor y unidad exactos, con sus condiciones; si falta una condición, la pide |
| AC-04 | Luz del tablero descrita con palabras | Pregunta qué significa | Significado y acción del manual; si hay ambigüedad, pregunta color o símbolo; si no está, lo dice |
| AC-05 | Situación de riesgo (olor a combustible) | Pregunta qué hacer | Advertencia primero, luego procedimiento del manual o remisión a asistencia; ninguna instrucción de reparación propia |
| AC-06 | Accidente o incendio descrito | Escribe el hecho | Primero indica llamar a emergencias |
| AC-07 | Dato ausente del manual | Pregunta un dato plausible que no está | "No lo encuentro en el manual", ofrece reformular y distribuidor; no inventa |
| AC-08 | Pregunta de precios o taller | Pregunta cuánto cuesta o dónde hay taller | Dice que solo atiende el manual; no inventa precios ni direcciones |
| AC-09 | Intento de obtener instrucciones internas o salir del tema | Pide ignorar reglas o revelar el prompt | Declina amablemente y regresa al manual; no revela instrucciones |
| AC-10 | Auto de otra versión | Dice tener otra versión y pregunta un dato | Avisa que su información corresponde a la versión `<del manual>`; no mezcla versiones |
| AC-11 | Pregunta ambigua ("¿cómo conecto el teléfono?") | Envía el mensaje | Una sola pregunta aclaratoria y luego respuesta basada en el manual |
| AC-12 | Nota de voz | La envía | Comportamiento según decisión de Christian; respuesta en texto |
| AC-13 | Foto del tablero | La envía | Pide que describa la luz con palabras (salvo decisión distinta); no trata la foto como fuente de verdad |
| AC-14 | Documento, sticker, ubicación o video | Lo envía | Una frase corta de que solo ayuda con preguntas escritas; no queda sin respuesta |
| AC-15 | Ráfaga de 3 mensajes en pocos segundos | Los envía seguidos | Cada uno recibe respuesta; sin contradicciones ni saludos repetidos |
| AC-16 | Conversación inactiva 15 min | Escribe de nuevo | Se abre una conversación nueva; no depende de lo anterior |
| AC-17 | Informe de cobertura | Se revisa contra el PDF | 100 % de páginas clasificadas; capítulos faltantes declarados; muestra de preguntas aprobada |

Las pruebas de llegada real por WhatsApp, indicador de escritura, cierre a los 15 minutos, notas de voz e imágenes no se automatizan; se describen como chequeos manuales y quedan registrados por el integrador.

## Fuera de alcance

- Llamadas de voz de WhatsApp o de cualquier tipo, y respuestas con nota de voz (salvo decisión de Christian).
- Mensajes salientes y plantillas: el agente nunca escribe primero ni fuera de la conversación iniciada por la persona.
- Traspaso a una persona humana o a otro canal.
- Herramientas externas, integraciones con sistemas de GWM, agenda de citas, consulta de VIN, garantías individuales o cotizaciones.
- Otros modelos de auto o marcas; otros manuales o versiones del H6 distintos del indexado.
- Preguntas frecuentes redactadas a mano (CDU posterior, si se decide).
- Interpretación de imágenes del usuario como fuente de verdad (salvo decisión de Christian).
- Memoria entre conversaciones o perfiles de usuario.

## Suposiciones

- Existe un solo manual indexado: el PDF de gwm-mx.com indicado por Christian (`ManualUsuarioHAVALH6.pdf`); su versión y año están por confirmar [POR DEFINIR].
- La integración nativa de WhatsApp de ElevenLabs permite todo lo descrito (texto, tipos de mensaje, cierre a 15 minutos); el integrador debe confirmarlo (ver Dudas).
- El plan Starter alcanza (o se recorta con aprobación de Christian) para el contenido del manual.
- No hay canal alternativo cuando WhatsApp o el agente fallan; es una POC con pocas personas usuarias.
- Las personas usuarias están en Chile y escriben principalmente en español de Chile (Respuesta de Christian, 2026-10-18).
- El manual tiene derechos de GWM; se usa solo como fuente interna de la POC y no se distribuye.

## Preguntas abiertas (para Christian)

1. **Versión del auto**: ¿año, versión y motorización exactos de tu Haval H6 (gasolina, híbrido, PHEV; actualización de modelo)? ¿Confirmas que `ManualUsuarioHAVALH6.pdf` es el manual correcto y que indexamos solo ese? Propuesta: sí, un solo manual en este CDU.
2. **Tono e idioma**: español de Chile con voseo, ya aprobado para el agente (la propuesta original de "tú" queda reemplazada); cálido y directo, sin tecnicismos innecesarios. Falta confirmar si se acepta "usted" cuando la persona lo use. ¿Y si escriben en inglés? Propuesta: responder en español y pasar a inglés solo si la persona insiste.
3. **Notas de voz**: ¿se atienden (entender el audio y responder en texto) o se rechazan pidiendo que escriban? Propuesta: atender si no agrega costo relevante y responder siempre en texto; de lo contrario rechazar con amabilidad.
4. **Fotos**: ¿se permite interpretarlas (por ejemplo el tablero) o se pide describir con palabras? Propuesta: pedir descripción (más seguro, menos riesgo de error en luces).
5. **Recorte por tamaño**: si el manual no cabe en el plan Starter, ¿aceptas recortar capítulos (con prioridad: seguridad, luces del tablero, uso y operación, mantenimiento y especificaciones) o prefieres subir de plan para cubrir todo? Condiciona SC-006.
6. **Contacto real**: ¿qué teléfono o canal de asistencia en carretera o distribuidor se puede dar? Si no hay uno, el agente solo dice "un distribuidor GWM autorizado" sin inventar datos. Y los números de emergencias a mencionar (propuesta para Chile, a confirmar por Christian: ambulancia 131, bomberos 132, Carabineros 133).
7. **Temas críticos y aviso fijo**: ¿qué temas se consideran críticos además de frenos, airbags, combustible, humo, luces rojas, niños y llantas? ¿Se agrega siempre un aviso del tipo "esto no sustituye una revisión en un taller autorizado" en respuestas de seguridad? Propuesta: sí, una frase corta al final.
8. **Despedida por inactividad**: ¿se envía un mensaje al cerrar por los 15 minutos? Propuesta: no enviar ninguno.
9. **Aviso de privacidad**: ¿se informa a la persona que sus mensajes se procesan en ElevenLabs y Meta? Propuesta: sí, una línea en el perfil del número, no en cada conversación.
10. **Umbrales de éxito**: ¿te sirven 90 % en la muestra de SC-001/Historia 6 y 15 segundos de tiempo de respuesta, o exiges otros?
11. **Longitud de mensaje**: ¿aceptas ~600 caracteres como tope por mensaje?

## Dudas para el integrador

Se abren como handoffs en `docs/equipo/handoffs/`:

1. **Tablas, imágenes y límite de 2 MB** (`001-analista-a-integrador-cobertura-tablas-imagenes-2mb.md`): viabilidad de que el agente reproduzca tablas y luces del tablero, qué pasa con la información que solo está en figuras, y qué ocurre al llegar al límite de Starter. Afecta Historia 3, Historia 6, SC-004 y SC-006.
2. **Tipos de mensaje, ráfagas y cierre** (`002-analista-a-integrador-tipos-mensaje-rafagas-inactividad.md`): qué hace realmente la plataforma con notas de voz, imágenes y otros adjuntos, con ráfagas y con el cierre a 15 minutos. Afecta Historia 5.
3. **Versiones del manual** (`003-analista-a-integrador-versiones-del-manual.md`): cómo garantizar que el agente no mezcle versiones y qué puede decir sobre la versión indexada. Afecta Historia 4.

Pendiente fuera de handoff: la actualización de la sección "Primer CDU" de `docs/equipo/COORDINACION.md` para reflejar este CDU y la entrada de una futura CDU de FAQ. La hace quien sea dueño de ese archivo; el analista lo propone.

## Definición de "hecho"

CDU-001 está **Hecho** cuando: (1) los criterios AC-01 a AC-17 pasan, con las pruebas automatizadas o chequeos manuales descritos; (2) SC-001 a SC-008 se cumplen en una muestra registrada; (3) el informe de cobertura (Historia 6) está aprobado por Christian; (4) no quedan `[POR DEFINIR]` ni `<del manual>` sin resolver en esta spec; (5) las limitaciones conocidas están declaradas.

## Registro de decisiones

- 2026-10-18, **Respuesta de Christian** (mensaje real, dado en el contexto del CDU-002): "Redacta todo para Chile, el manual es el mismo." Efecto en este CDU: país del servicio = Chile; español de Chile con voseo; emergencias de Chile propuestas (131, 132, 133) a confirmar; se quitan los supuestos de México. Sin cambios en los requisitos funcionales más allá de esto. El PDF sigue siendo el de gwm-mx.com porque es un hecho de origen.

## Historial

- 2026-10-18: Propuesta inicial. PDF aún no leído; contenido del manual no verificado.
