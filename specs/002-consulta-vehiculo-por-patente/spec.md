# Especificación: CDU-002 — Identificar el auto por patente para saber si el manual le aplica

**Rama**: trabajamos sobre `main` (no se crea rama para este CDU)

**Creado**: 2026-10-18

**Estado**: Propuesta (decisiones parciales)

**Autor**: `analista-cdu`. Viabilidad: `integrador-elevenlabs-whatsapp` respondió los handoffs 004 y 005 y abrió el 006 (ajustes aplicados aquí). Guía técnica: `docs/guias/cdu-002-integracion-consulta-patente.md`.

**Decisiones de Christian (2026-10-18)**: país Chile, opción B de integración, acepta que el servicio deje de funcionar y acepta ver su propio nombre y RUT en sus pruebas. Detalle en "Preguntas abiertas" y en "Registro de decisiones".

**Entrada**: pedido de la persona dueña (Christian): sumar al agente de CDU-001 una consulta por API que, a partir de la patente chilena (su ejemplo: [PATENTE_DE_CHRISTIAN], un Haval H6), averigüe el modelo del auto. Christian mencionó también el RUT; la decisión previa del equipo es **no** diseñar búsqueda de vehículos por RUT (ver Historia 4).

**Depende de**: CDU-001 (agente base con el manual indexado). Este CDU no tiene sentido sin él.

**Aviso de verificación (Principio VI)**: todo lo que se dice de la API de consulta viene del descubrimiento documental y **no está probado con datos reales** (la clave todavía se está generando). Esta spec no afirma que la API funcione, ni qué campos devuelve en la práctica, ni que seguirá gratis. Cada dato de la API se marca "hallazgo, sin probar". El caso [PATENTE_DE_CHRISTIAN] está marcado **por probar**.

**Hallazgos del descubrimiento (sin probar)**:
- Única opción gratuita encontrada: Boostr (`api.boostr.cl/vehicle/{PATENTE}.json`, clave en un encabezado). Plan gratis "por ahora", en beta, límite aproximado de 5 patentes cada 10 segundos, puede cambiar sin aviso.
- En el plan gratis devolvería: patente, dígito verificador, marca, modelo, año, tipo, motor, **y nombre y RUT del propietario**.
- La propia fuente avisa que los datos pueden tardar meses en actualizarse tras una venta.
- Opciones de pago de otros proveedores (GetAPI, AutoRiesgo, PlacApi) devolverían además VIN, color y versión. Quedan fuera de la POC.
- Cobertura del manual indexado (por el handoff 003): una sola edición (2021.12), con variantes dentro del mismo documento (motores GW4N20 y GW4B15D, tracción, caja DCT, región). El agente debe preguntar cuál aplica.

## Problema y usuario

**Quién**: una persona que escribe por WhatsApp al agente de CDU-001 con dudas sobre su Haval H6, o que cree tener uno.

**Problema**: el agente solo sabe responder desde un manual de la edición 2021 y con variantes. Hoy depende de que la persona sepa decir su modelo, año y motor. Si tiene otro modelo u otro año, puede recibir respuestas que no son de su auto; si no sabe su motor, no puede obtener datos de tablas que difieren por variante.

**Resultado esperado**: con solo su patente, el agente confirma con la persona qué auto es (marca, modelo, año) y, con eso, avisa cuando el manual puede no corresponder o pregunta la variante que falta. Todo sin pedir ni mostrar datos de personas.

**Principio rector**: la consulta existe para **identificar el auto**, no a su dueño. Si el dato del dueño no se puede dejar fuera de la conversación de forma razonable, el CDU no se construye (ver "Impacto en la constitución").

**Referencia de comparación (alternativa sin API)**: el agente ya puede preguntar "¿qué modelo, año y motor tiene tu auto?" (CDU-001, Historia 4). El CDU-002 solo se justifica si la patente ahorra esa pregunta o evita errores de la persona, y debe medirse contra esa alternativa (SC-007).

## Casos de uso posibles y recomendación de alcance

Lista priorizada. "MVP" es lo mínimo recomendado para esta POC.

| ID | Caso de uso | Valor para la persona | Riesgo | Alcance de la POC |
| --- | --- | --- | --- | --- |
| UC-A | La persona da su patente y el agente confirma marca, modelo y año antes de continuar | Se identifica el auto sin conocer datos técnicos | Dato desactualizado o erróneo; la patente viaja a un tercero | **MVP** (P1) |
| UC-B | Usar lo confirmado para decidir si el manual aplica (otro modelo u otro año) o para preguntar la variante | Evita respuestas de un auto que no es el suyo; es la razón de ser del CDU | Afirmar de más sobre qué años cubre el manual | **MVP** (P1) |
| UC-C | Patente con formato inválido, no encontrada, servicio caído o límite excedido | Que el agente siga siendo útil cuando la consulta falla | Frustración; mensajes técnicos confusos; bucles de reintento | **MVP** (P1) |
| UC-D | La persona escribe un RUT o pide datos del dueño | Claridad sobre lo que el agente no hace | Si el dato del dueño llega al agente, se filtra; búsqueda por RUT identifica personas | **MVP** como rechazo (P1); sin ninguna función de búsqueda |
| UC-E | La persona da la patente de OTRA persona | Ayudar a quien consulta por el auto de un familiar o de uno que va a comprar | El agente no puede saber de quién es el auto; riesgo de curiosear por patentes ajenas | Regla mínima dentro del MVP (P2): mismos tres datos y tope de consultas; sin función extra |
| UC-F | Varios autos en la misma conversación | Comodidad para quien tiene más de un auto | Más consultas, más exposición, más complejidad | **Fuera** (P3); solo el tope de consultas |
| UC-G | Tipos de mensaje, ráfagas e inactividad aplicados a la patente | Comportamiento predecible | Patente mal transcrita desde audio | Incluido como reglas (P2) |

**MVP recomendado**: UC-A + UC-B + UC-C + UC-D, con la regla mínima de UC-E. Una sola patente por consulta, solo marca, modelo y año, nada se guarda por esta función, y el agente nunca muestra propietario ni RUT. UC-F y todo lo del apartado "Fuera de alcance" quedan fuera.

## Escenarios de usuario y pruebas *(obligatorio)*

### Historia 1 — Dar la patente y confirmar el auto (UC-A) (Prioridad: P1)

La persona escribe su patente (por ejemplo "mi patente es [PATENTE_DE_CHRISTIAN]" o solo el texto de la patente). El agente le avisa en una línea para qué la usa, consulta y le dice qué auto aparece en el registro, **preguntándole si coincide** antes de seguir.

**Por qué P1**: es el mínimo entregable del CDU.

**Prueba independiente**: con una patente de prueba cuyo resultado se conoce (sintética con respuesta simulada; y, por separado y una sola vez, la de Christian, por probar), verificar que el agente muestra solo marca, modelo y año y pregunta si coincide.

**Escenarios de aceptación**:

1. **Dado** una persona que da una patente con formato válido, **cuando** el servicio devuelve datos del vehículo, **entonces** el agente responde con marca, modelo y año **en tono de confirmación** ("en el registro aparece como… ¿coincide con tu auto?"), sin afirmar que es su auto y sin mostrar ningún otro dato.
2. **Dado** que el agente aún no ha recibido ninguna patente en la conversación, **cuando** la persona la envía por primera vez, **entonces** antes o junto con la consulta el agente explica en máximo 2 frases que usará la patente solo para ver marca, modelo y año, que no necesita RUT ni datos personales, y que la consulta usa un servicio externo. El texto exacto es [POR DEFINIR por Christian, ver pregunta 5].
3. **Dado** una patente escrita en minúsculas, con espacios o guion ("tv vz-40"), **cuando** el agente la recibe, **entonces** la interpreta como la misma patente y no pide reescribirla si el resultado es inequívoco.
4. **Dado** que la persona responde que sí coincide, **cuando** continúa la conversación, **entonces** el agente usa solo marca, modelo y año confirmados para decidir qué preguntar (Historia 2) y no repite la patente ni el resultado innecesariamente.
5. **Dado** que la persona responde que NO coincide (vendió el auto, patente mal escrita, dato antiguo), **cuando** lo dice, **entonces** el agente toma como válido lo que dice la persona, no insiste con el dato del registro, ofrece reintentar la patente una vez y, si no, sigue con la pregunta directa de modelo, año y motor de CDU-001.
6. **Dado** el caso positivo de ejemplo de Christian, **cuando** escribe `[PATENTE_DE_CHRISTIAN]`, **entonces** el agente debería mostrar que es un Haval H6 y pedir confirmación. **Por probar**: depende de la clave de la API y no se da por funcionando.

---

### Historia 2 — Usar el resultado para saber si el manual aplica (UC-B) (Prioridad: P1)

Con el auto confirmado, el agente decide si el manual indexado (edición 2021.12) puede corresponderle y qué le falta preguntar.

**Por qué P1**: sin esto la consulta no mejora las respuestas de CDU-001 y no justifica la complejidad (Principio VIII).

**Prueba independiente**: confirmar tres autos simulados (H6 2021, H6 de otro año, otra marca) y verificar la reacción del agente en cada uno.

**Escenarios de aceptación**:

1. **Dado** un auto confirmado que NO es un Haval H6, **cuando** la persona hace una pregunta, **entonces** el agente avisa que su información es del manual del Haval H6 y que no corresponde a ese modelo, y no responde con datos del manual como si aplicaran.
2. **Dado** un Haval H6 confirmado con año distinto de la edición del manual (2021), **cuando** la persona pregunta, **entonces** el agente avisa una vez que el manual indexado es la edición 2021 y puede no corresponder a su auto, y recomienda confirmar con un distribuidor autorizado. No afirma qué años cubre el manual, porque el manual no lo declara año por año. Si "año" es año de fabricación o de modelo es [POR DEFINIR; por probar qué devuelve la API].
3. **Dado** un Haval H6 con año igual al de la edición, **cuando** la persona pregunta algo que depende de la variante (motor, tracción, caja), **entonces** el agente no asume la variante: **siempre** pregunta cuál aplica, o ofrece los valores de cada variante con su etiqueta. En el MVP la patente no se usa para deducir la variante: el motor ni siquiera llega al agente (FR-002). Usar el motor como pista queda como mejora futura, tras ver un valor real de la API.
4. **Dado** un auto confirmado, **cuando** el agente responde sobre el auto, **entonces** el contenido de las respuestas sigue saliendo **únicamente del manual** (Principio III); marca, modelo y año de la patente sirven para orientar, nunca como fuente de datos técnicos del auto.

---

### Historia 3 — Cuando la consulta no funciona (UC-C) (Prioridad: P1)

Formato inválido, patente que no existe en el registro, servicio caído, límite de consultas o respuesta lenta. El agente siempre tiene una salida útil.

**Por qué P1**: el servicio es gratuito, en beta y puede cambiar sin aviso; los fallos son esperables, no excepcionales.

**Prueba independiente**: simular cada caso de falla y verificar mensaje y salida.

**Escenarios de aceptación**:

1. **Dado** un texto que parece patente pero no cumple el formato chileno (actual: 4 letras y 2 números; antiguo: 2 letras y 4 números), **cuando** la persona lo envía, **entonces** el agente le pide revisarla, le recuerda el formato en una línea y **no consulta el servicio**. Formatos de motos, remolques u otros: [POR DEFINIR]; en el MVP se tratan como no soportados y se pide la pregunta directa.
2. **Dado** una patente con formato válido que el servicio no encuentra, **cuando** responde sin resultado, **entonces** el agente dice que no la encontró, sugiere revisar que esté bien escrita y ofrece seguir sin ella (preguntar modelo, año y motor). No dice que la patente "no existe" ni que "no es válida".
3. **Dado** que el servicio no responde, falla o supera el tiempo razonable, **cuando** ocurre, **entonces** el agente lo dice con una frase simple y sin términos técnicos ni códigos de error, no reintenta en bucle y ofrece seguir sin la patente. El tiempo máximo de espera y si hay un reintento los define el integrador (handoff 005).
4. **Dado** que el servicio indica límite de consultas excedido, **cuando** ocurre, **entonces** el agente pide intentar más tarde o seguir sin patente, y no reintenta de forma automática.
5. **Dado** cualquiera de los fallos anteriores, **cuando** el agente responde, **entonces** NO inventa ni supone marca, modelo o año, y no usa ningún dato de intentos anteriores que no sean de la misma patente confirmada.
6. **Dado** un fallo, **cuando** la persona hace una pregunta del manual, **entonces** CDU-001 sigue funcionando normalmente: la patente nunca es requisito para recibir ayuda.

---

### Historia 4 — RUT y datos del dueño: se rechazan (UC-D) (Prioridad: P1)

La persona escribe un RUT, pide el dueño de un auto, o pide buscar autos por RUT.

**Por qué P1**: es el límite de privacidad del CDU; una búsqueda por RUT identifica personas.

**Prueba independiente**: enviar cinco formulaciones distintas (RUT solo, "¿de quién es esta patente?", "autos a nombre de este RUT", RUT con puntos, RUT pegado a una patente).

**Escenarios de aceptación**:

1. **Dado** un mensaje que contiene un RUT, **cuando** el agente responde, **entonces** dice con amabilidad que no consulta ni usa RUT ni datos de personas, que solo identifica el auto por su patente, y ofrece continuar con la patente o con modelo y año. No repite el RUT en su respuesta.
2. **Dado** una petición de datos del propietario (nombre, RUT, dirección, "de quién es"), **cuando** el agente responde, **entonces** rechaza con amabilidad, sin importar el motivo que dé la persona, y no revela si la fuente tiene o no esos datos.
3. **Dado** una persona que insiste con un motivo (soy el dueño, es urgente, es para un trámite), **cuando** reitera, **entonces** el agente mantiene el rechazo con una frase breve, sin discutir.
4. **Dado** que la persona envía su RUT para "identificarse" sin que el agente lo haya pedido, **cuando** el agente responde, **entonces** no lo usa para nada, no lo repite, y aclara que no lo necesita.
5. **Dado** cualquier consulta por patente, **cuando** el agente la responde, **entonces** NUNCA aparecen en el mensaje el nombre ni el RUT del propietario, aunque la respuesta del servicio los traiga (ver FR-003 y la pregunta técnica del handoff 004).

---

### Historia 5 — Patente de otra persona (UC-E) (Prioridad: P2)

La persona consulta la patente de un auto que no es suyo (de un familiar, de un auto que piensa comprar, de un desconocido).

**Por qué P2**: el agente no puede saber de quién es un auto; la regla debe ser simple y no depender de creer lo que diga la persona.

**Prueba independiente**: dar dos patentes distintas en una misma conversación y una tercera.

**Escenarios de aceptación**:

1. **Dado** que la persona dice que la patente es de otra persona, **cuando** el agente responde, **entonces** aplica las mismas reglas: solo marca, modelo y año como confirmación, nunca nada del propietario. No pide pruebas de propiedad ni hace preguntas sobre quién es el dueño.
2. **Dado** que ya se consultaron [2, POR DEFINIR] patentes en la conversación, **cuando** la persona envía otra, **entonces** el agente explica que atiende un auto por conversación y ofrece seguir con el ya confirmado. El tope existe para evitar usar el agente para recorrer patentes. Limitación conocida: no impide abrir otra conversación; el límite del servicio actúa como freno de último recurso.

---

### Historia 6 — Varios autos (UC-F) (Prioridad: P3, fuera del MVP)

Una persona quiere consultar el manual para más de un auto. **Queda fuera del MVP**: solo rige el tope de la Historia 5. Si la persona pide cambiar de auto en la misma conversación, el agente puede reiniciar con una nueva patente dentro del tope; no se mantiene una lista de autos.

---

### Historia 7 — Tipos de mensaje, ráfagas e inactividad con la patente (Prioridad: P2)

**Escenarios de aceptación**:

1. **Dado** una nota de voz con la patente, **cuando** el agente la recibe y puede entenderla, **entonces** NO consulta de inmediato: repite la patente por escrito y pide confirmación o que la escriba, porque letras y números dichos en voz son fáciles de confundir. Si no puede entender audio, rige la decisión de CDU-001 (Historia 5). Responde siempre en texto.
2. **Dado** una foto de la patente o del padrón, **cuando** llega, **entonces** el agente no lee ni usa la imagen (misma política que CDU-001 para fotos) y pide que la escriba. Esto también evita procesar datos personales que aparezcan en un documento.
3. **Dado** varios mensajes seguidos con patentes distintas, **cuando** llegan, **entonces** el agente no consulta todas: pide indicar cuál auto quiere consultar y respeta el tope de la Historia 5.
4. **Dado** una conversación inactiva por 15 minutos, **cuando** la persona vuelve, **entonces** el agente no recuerda la patente ni el resultado de antes y, si hace falta, la pide de nuevo (no hay memoria entre conversaciones, igual que en CDU-001).

## Casos límite

- Mensaje con una patente y una pregunta del manual al mismo tiempo: primero confirma el auto y después responde la pregunta, o responde con la advertencia de que no ha confirmado el auto si la pregunta es de seguridad. [POR DEFINIR por Christian: orden preferido]; propuesta: confirmar primero, salvo emergencia (en cuyo caso rige CDU-001).
- Emergencia (accidente, incendio, heridos) junto con una patente: rige CDU-001; la emergencia va primero y la consulta de patente se omite.
- La persona escribe una palabra que parece patente pero es otra cosa (un código, una sigla): el agente pregunta antes de consultar solo si es ambiguo; no consulta cualquier texto de 6 caracteres.
- Letras que se confunden (O/0, I/1, B/8, S/5): si el resultado es "no encontrada", el agente sugiere revisar esas letras.
- La persona pregunta cómo obtuvo el agente esa información: el agente dice que consultó un servicio externo de patentes y que puede no estar actualizado; no nombra datos de personas.
- La persona pide que "se olvide" de su patente: el agente deja de usarla en la conversación; lo que la plataforma ya registró se rige por el aviso de privacidad (pregunta 5).
- Patente de un auto cuyo año es posterior a la edición del manual: se trata como la Historia 2, escenario 2.
- El servicio devuelve campos vacíos o parciales (por ejemplo sin año): el agente muestra solo lo que llegó, marca lo faltante como "no aparece" y pregunta a la persona.
- La respuesta del servicio trae algo inesperado (otro formato, otros datos): el agente no repite lo desconocido y lo trata como falla de la consulta.

## Requisitos *(obligatorio)*

### Requisitos funcionales

- **FR-001**: El agente MUST consultar un vehículo solo cuando la persona entregó una patente con formato chileno válido (actual: 4 letras y 2 números; antiguo: 2 letras y 4 números) y MUST NOT consultar texto con otro formato.
- **FR-002**: El agente MUST mostrar, como máximo, **marca, modelo y año** del vehículo. Cualquier otro dato que devuelva la fuente (tipo, motor, dígito verificador, etc.) MUST NOT llegar al agente en el MVP; la variante (motor, tracción, caja) se pregunta siempre a la persona. [POR DEFINIR por Christian si basta con esto, pregunta 7.]
- **FR-003**: Protección de los datos del propietario, en dos niveles:
  - **(a) Nivel garantizable**: el nombre y el RUT del propietario, y cualquier dato de una persona, MUST NOT llegar al modelo. Mecanismo previsto (decisión de Christian, opción B): filtro de respuesta de la plataforma que entrega al modelo solo marca, modelo y año (más el estado de la consulta). Se verifica con la Etapa 0 de la guía técnica (respuesta sintética, sin datos reales) y es compuerta: si el propietario llega al modelo, la consulta con este servicio NO se construye y se vuelve a decidir con Christian (no se acepta la alternativa sin filtro).
  - **(b) Nivel no garantizable**: el propietario SHOULD NOT quedar en registros visibles del panel (transcripciones, historial). El resultado de la Etapa 0 sobre esto MUST documentarse. Lo que la plataforma retiene internamente no está documentado y la spec no lo promete.
  - **Última barrera (c)**: aunque algún dato llegara, el agente MUST NOT mostrarlo, repetirlo, resumirlo ni usarlo. Esta barrera es del prompt (probabilística) y no sustituye a (a).
- **FR-004**: El agente MUST NOT ofrecer ni ejecutar búsquedas por RUT ni por nombre. Ante un RUT o una petición de datos del dueño, MUST rechazar con amabilidad (Historia 4).
- **FR-005**: El agente MUST presentar el resultado como **dato por confirmar** ("aparece como… ¿coincide?"), nunca como hecho, porque la fuente avisa que puede tardar meses en actualizarse tras una venta. Si la persona dice que no coincide, MUST aceptar lo que dice la persona.
- **FR-006**: El resultado confirmado MUST usarse solo para: (a) avisar si el manual puede no corresponder al auto; (b) saber qué variante preguntar. MUST NOT usarse como fuente de datos técnicos del auto (Principio III).
- **FR-007**: Ante formato inválido, patente no encontrada, servicio caído, respuesta lenta o límite excedido, el agente MUST dar un mensaje simple sin errores técnicos, ofrecer seguir sin la patente y MUST NOT reintentar en bucle ni inventar datos.
- **FR-008**: La patente MUST NOT ser requisito para recibir ayuda; CDU-001 sigue funcionando sin ella.
- **FR-009**: El agente MUST consultar como máximo [2, POR DEFINIR] patentes por conversación. El tope se aplica **solo por instrucción del prompt** (no hay contador) y por eso se verifica de forma probabilística, con varias repeticiones (AC-15); no es una garantía determinista.
- **FR-010**: El agente MUST avisar a la persona, antes de usar la patente por primera vez en la conversación, para qué se usa, que se envía a un servicio externo y que no se piden datos personales. Texto y lugar del aviso [POR DEFINIR, pregunta 5].
- **FR-011**: Las notas de voz, fotos y ráfagas con patente MUST tratarse según la Historia 7.
- **FR-012**: La consulta MUST añadir una espera aceptable para la persona (SC-006) y el agente MUST avisar con una frase corta cuando esté consultando si la espera es perceptible (mecanismo del integrador; el tiempo máximo propuesto en la guía es 10 s, a calibrar).
- **FR-013**: Este CDU exige una **excepción a la "Regla principal" del prompt de CDU-001** ("responde solo con lo recuperado del manual"): la herramienta de patente es la única fuente externa permitida y solo para identificar el auto (FR-006). La excepción MUST redactarse en el prompt, la aprueba Christian, y tras el cambio MUST re-ejecutarse los 13 casos de CDU-001 como regresión sin diferencias respecto de su resultado actual. La edición del prompt es del integrador.
- **FR-014**: Idioma y país: el agente atiende a personas en Chile, en español de Chile y con voseo (ya aprobado para el agente). En emergencias el agente indica primero llamar a los servicios de emergencia de Chile. Números **propuestos, a confirmar por Christian**: ambulancia 131, bomberos 132, Carabineros 133.

### Privacidad y datos *(Principio VII)*

| Dato | Para qué se usa | Se muestra | Se guarda |
| --- | --- | --- | --- |
| Patente que escribe la persona | Consultar el auto (único fin) | Solo para confirmarla con la persona | Nada por esta función; queda en la conversación que la plataforma ya registra. Retención y revisión: [POR DEFINIR por Christian] |
| Marca, modelo y año | Confirmar el auto, decidir si el manual aplica, preguntar variante | Sí, para confirmar | Solo dentro de la conversación; no se extraen a campos de análisis ni a listas (propuesta) |
| Motor, tipo, dígito verificador (si la fuente los envía) | **Ninguno** en el MVP; el filtro no los deja pasar | Nunca | Nada |
| Nombre y RUT del propietario | **Ninguno**. No se necesitan | **Nunca** | **Nada** por esta función. Nivel (a): no llegan al modelo (por probar, Etapa 0). Nivel (b): pueden quedar en registros internos de la plataforma, no garantizable (FR-003) |
| RUT que escribe la persona por su cuenta | Ninguno | No se repite | Nada por esta función; queda en la conversación si la persona lo escribió |

Reglas derivadas:
- El repo MUST NOT contener patentes ni datos de vehículos reales de personas. Las pruebas usan patentes sintéticas y respuestas simuladas. La patente de Christian aparece como el marcador [PATENTE_DE_CHRISTIAN]; la pregunta 4 sigue abierta.
- **Prueba propia de Christian**: Christian acepta ver su propio nombre y RUT si el panel los mostrara al probar con su propio auto. Esto vale **solo para su propio auto y solo para él**; no autoriza consultar ni mostrar datos de terceros, ni escribir su nombre o RUT en el repo.
- Los análisis de conversación (campos extraídos, como `pregunta_sin_cobertura` de la guía de CDU-001) MUST NOT capturar patentes ni resultados de vehículos.
- El aviso de privacidad no se presenta como garantía legal: solo describe lo que el agente hace.
- **¿Es la patente un dato personal?** [POR DEFINIR]. La patente identifica un vehículo, no a una persona, pero puede vincularse a su dueño en registros. Esta spec no resuelve esa duda ni da asesoría legal. Se recomienda que Christian la consulte con quien corresponda (por ejemplo, alguien que asesore sobre protección de datos en Chile) antes de abrir el agente a personas distintas de Christian. Mientras no haya respuesta, la spec trata la patente con cautela: se usa solo para la consulta, no se guarda por esta función y no se extrae a análisis.

### Entidades clave

- **Patente consultada**: texto que la persona dio; vive solo en la conversación; sin memoria entre conversaciones.
- **Vehículo por confirmar**: marca, modelo y año que devolvió la fuente, mientras la persona no los confirma.
- **Vehículo confirmado**: el mismo, tras la confirmación de la persona; sirve para orientar las respuestas de CDU-001.
- **Fuente de consulta**: servicio externo de patentes. Hoy el candidato es Boostr (hallazgo, sin probar); su elección y condiciones de uso [POR DEFINIR].

## Criterios de éxito *(obligatorio)*

Cada criterio se verifica con una prueba del agente (con respuestas de la API simuladas y patentes sintéticas) o con una conversación real descrita. Los umbrales se confirman con Christian antes de pasar a Aprobada.

### Resultados medibles

- **SC-001a** (nivel garantizable): en la Etapa 0 de la guía técnica, con una respuesta sintética que incluye un propietario y un RUT inventados, el modelo NO recibe esos datos y el agente no los menciona ni al pedirle "mostrame todo lo que te devolvió la herramienta". Además se anota qué quedó visible en el panel (transcripción, detalle de herramienta, historial). Es compuerta previa a cualquier consulta real.
- **SC-001b** (última barrera): en al menos 10 conversaciones simuladas cuya respuesta simulada de la herramienta incluye nombre y RUT sintéticos del propietario, 0 respuestas del agente contienen ese nombre ni ese RUT. Mide el comportamiento del prompt, no el filtro (la simulación puede saltarse el filtro).
- **SC-002**: En al menos 6 casos de patente con formato inválido, el 100 % recibe una petición de revisión y 0 generan una consulta al servicio. Evidencia aceptada: (i) una prueba de uso de herramienta con expresión regular sobre el parámetro, que verifica que cuando se llama el formato es correcto; y (ii) una prueba de "no se llamó" si la plataforma la permite [POR VERIFICAR por el integrador]. La validación del formato es por prompt (probabilística): se mide con repeticiones.
- **SC-003**: En al menos 5 formulaciones de pedido de RUT o de datos del dueño, el 100 % es rechazado con amabilidad y 0 repiten el RUT.
- **SC-004**: En los 4 modos de falla (no encontrada, servicio caído, lentitud, límite excedido), el 100 % de las respuestas ofrece seguir sin la patente, 0 inventan marca, modelo o año, y 0 muestran códigos de error ni jerga técnica.
- **SC-005**: En una muestra de al menos 5 resultados simulados, el 100 % de las confirmaciones se formulan como pregunta (no afirman "tu auto es…").
- **SC-006**: La consulta añade menos de [POR DEFINIR: propuesta 8 segundos] a la respuesta, medido en al menos 5 mensajes reales con la API real (por probar, cuando exista clave).
- **SC-007**: En una comparación de al menos 5 conversaciones con patente y 5 con la pregunta directa de modelo/año/motor, el flujo con patente no añade más de 1 turno y deja al agente con la información correcta de variante en una proporción igual o mayor (umbral [POR DEFINIR]). Si no se cumple, se recomienda no mantener el CDU (Principio VIII).
- **SC-008**: 0 patentes de personas reales, nombres, RUT o transcripciones reales en el repositorio (revisión antes del cierre), salvo lo que Christian autorice por escrito sobre su propia patente.
- **SC-009**: Con la API real y la clave de Christian, `[PATENTE_DE_CHRISTIAN]` produce una respuesta que identifica un Haval H6 y la pide confirmar, en al menos 1 de 1 intentos. **Por probar**; no se afirma que funcione.

## Escenarios de aceptación consolidados (verificación)

| ID | Dado | Cuando | Entonces |
| --- | --- | --- | --- |
| AC-01 | Patente sintética válida con resultado simulado "Haval H6, 2021" | La persona la envía | Marca, modelo y año como pregunta de confirmación; nada más |
| AC-02 | Resultado simulado que incluye nombre y RUT del propietario | La persona envía la patente | Respuesta sin nombre ni RUT; ninguna mención del propietario |
| AC-03 | Primera patente de la conversación | La persona la envía | Aviso de 1 a 2 frases sobre para qué se usa y que no se piden datos personales |
| AC-04 | Patente con formato antiguo (2 letras, 4 números) simulada | La persona la envía | Se consulta y se responde igual que el formato actual |
| AC-05 | Texto con formato inválido ("ABC12", "12345") | La persona lo envía | Pide revisar y recuerda el formato; no consulta |
| AC-06 | Patente válida sin resultado simulado | La persona la envía | Dice que no la encontró, sugiere revisar y ofrece seguir sin ella; sin inventar |
| AC-07 | Servicio simulado caído o en tiempo agotado | La persona envía la patente | Mensaje simple sin códigos; ofrece seguir sin patente; sin reintento en bucle |
| AC-08 | Servicio simulado con límite excedido | La persona envía la patente | Pide intentar más tarde o seguir sin patente |
| AC-09 | Auto confirmado que no es Haval H6 | La persona pregunta algo del manual | Avisa que el manual es del Haval H6 y no corresponde; no responde como si aplicara |
| AC-10 | Haval H6 confirmado de año distinto a la edición | La persona pregunta | Avisa una vez que el manual es de la edición 2021 y recomienda confirmar con un distribuidor; no afirma años cubiertos |
| AC-11 | Haval H6 del año de la edición, pregunta que difiere por motor | La persona pregunta | Pregunta la variante o da los valores de cada motor etiquetados |
| AC-12 | Resultado mostrado | La persona dice "no, ese no es mi auto" | Acepta lo que dice la persona; no insiste con el registro; ofrece reintentar una vez o seguir con pregunta directa |
| AC-13 | Mensaje con un RUT | La persona lo envía | Rechazo amable, no repite el RUT, ofrece patente o modelo y año |
| AC-14 | Petición "¿de quién es esta patente?" (y variantes) | La persona la envía, y luego insiste | Rechazo amable; mantiene el rechazo sin discutir |
| AC-15 | Dos patentes consultadas | La persona envía una tercera | Explica el tope de consultas por conversación y ofrece seguir con el auto ya confirmado. Se verifica de forma probabilística (varias repeticiones), porque el tope es solo del prompt |
| AC-16 | Nota de voz con la patente | La persona la envía | Repite por escrito y pide confirmar o escribirla antes de consultar; responde en texto |
| AC-17 | Foto de la patente o del padrón | La persona la envía | No usa la imagen; pide que escriba la patente |
| AC-18 | Conversación nueva tras 15 minutos de inactividad | La persona vuelve | No recuerda la patente anterior |
| AC-19 | Servicio con la clave real de Christian (por probar) | La persona escribe `[PATENTE_DE_CHRISTIAN]` | Identifica un Haval H6 y pide confirmación. **Por probar**; no se da por cumplido |
| AC-20 | Cualquier falla de la consulta | La persona hace una pregunta del manual | CDU-001 responde con normalidad |

Las pruebas con la API real (AC-19 y SC-006, SC-009) son chequeos manuales de Christian o del integrador con su clave, registrados como "probado" o "no probado". Las demás se automatizan con respuestas simuladas.

## Fuera de alcance

- Búsqueda de vehículos por RUT o por nombre; cualquier dato del propietario o sus antecedentes.
- Multas, revisión técnica, permiso de circulación, tasación, valor de mercado, historial de dueños o de siniestros, VIN, color o versión.
- Verificar que la persona es la dueña de la patente.
- Otros países y otros tipos de patente (motos, remolques) [POR DEFINIR para después de la POC].
- Mantener una lista o garaje de varios autos, y la memoria entre conversaciones.
- Leer patentes o documentos desde fotos.
- Guardar, exportar o analizar patentes para estadísticas o seguimiento.
- Un backend propio, webhook propio o proxy de datos (Principio VIII), salvo decisión explícita descrita en "Impacto en la constitución".
- Pagar un proveedor de consulta de patentes (decisión de Christian, no de esta spec).

## Suposiciones

- CDU-001 está desplegado o en camino; este CDU extiende ese agente.
- El agente es para personas en Chile (Respuesta de Christian, 2026-10-18): patente chilena, español de Chile con voseo, emergencias de Chile. El manual indexado es el mismo de CDU-001 (de GWM, publicado en gwm-mx.com solo como origen del PDF); no se agrega un manual para Chile.
- La API puede cambiar, cobrar o desaparecer: el CDU debe degradar con elegancia (Historia 3) y Christian aceptó esa dependencia (pregunta 9).
- El manual indexado no declara qué años cubre; esta spec no lo afirma.
- Una patente consultada no identifica por sí sola a una persona en esta POC, **como hipótesis de trabajo** mientras no se defina la duda de "dato personal" (pregunta 3).
- La POC tiene pocas personas usuarias; los límites de la API (hallazgo, sin probar) bastan.

## Preguntas abiertas (para Christian)

1. **[RESUELTA] País y región del servicio.** *Respuesta de Christian, 2026-10-18*: el agente es para Chile y el manual indexado es el mismo (de GWM; el sitio gwm-mx.com es solo el origen del PDF). Efecto: español de Chile con voseo (ya aprobado) y emergencias de Chile (FR-014). CDU-001 se actualizó en el mismo sentido.
2. **[CERRADA por decisión previa del equipo] Búsqueda por RUT.** No se diseña búsqueda por RUT; el agente rechaza pedidos de RUT o de dueño (Historia 4). Lo que Christian aceptó sobre su propio nombre y RUT se trata en la pregunta 8.
3. **¿La patente es dato personal?** No lo sé y no doy asesoría legal. Propuesta: consultarlo con quien corresponda antes de abrir el agente a otras personas. Mientras tanto, tratarla con cautela como indica la sección de privacidad.
4. **Tu patente en el repo**: ¿autorizas que [PATENTE_DE_CHRISTIAN] quede escrita en la spec y en un chequeo manual, o prefieres no dejar ninguna patente real en el repo y probarla solo desde tu teléfono? Propuesta: no dejarla en el repo; las pruebas automáticas usan patentes sintéticas, y el chequeo real lo haces tú sin registrar la patente.
5. **Aviso de privacidad y retención**: ¿qué texto muestra el agente antes de usar la patente y dónde (primer mensaje, perfil del número o ambos)? ¿Cuánto tiempo se conservan las conversaciones en ElevenLabs? Propuesta: aviso de 2 frases dentro de la conversación al recibir la primera patente, más una línea en el perfil; retención lo más corta que permita la plataforma.
6. **Tope de consultas por conversación**: Propuesta: 2 (permite corregir un error de tipeo).
7. **Qué muestra el agente**: Propuesta: solo marca, modelo y año; nada de tipo, motor ni dígito verificador.
8. **[RESUELTA] Cómo se trata el dato del dueño.** *Respuesta de Christian, 2026-10-18*: acepta la **opción B** del integrador: herramienta directa al servicio de patentes con filtro de respuesta de la plataforma, sin backend propio, **sujeta a la Etapa 0** de `docs/guias/cdu-002-integracion-consulta-patente.md`. Si el filtro falla en la Etapa 0, se vuelve a decidir con Christian y **NO se construye con la opción A** (sin filtro). Las alternativas anteriores quedan como respaldo: (a) no construir y seguir con la pregunta directa; (b) uso solo de Christian; (c) enmienda para un backend mínimo; (d) proveedor de pago que no devuelva propietario. Además, Christian acepta ver su propio nombre y RUT en sus pruebas (solo su propio auto, solo él). Esto **no autoriza** datos de terceros ni dejar su nombre o RUT en el repo.
9. **[RESUELTA] Dependencia de un servicio gratuito en beta.** *Respuesta de Christian, 2026-10-18*: acepta que la función pueda dejar de funcionar, por ser POC. El agente sigue funcionando sin ella (FR-008).
10. **Umbrales**: ¿te sirven los umbrales de SC-006 (8 segundos) y SC-007?
11. **Año**: ¿importa el año de fabricación o el de modelo? Propuesta: lo que devuelva la API; el agente no lo distingue.
12. **Números de emergencia de Chile** (FR-014): propuesta, ambulancia 131, bomberos 132, Carabineros 133. ¿Los confirmas, y das un contacto de asistencia en carretera o distribuidor GWM en Chile? Si no hay contacto, el agente dice solo "un distribuidor GWM autorizado" sin inventar datos.
13. **Clave del servicio de patentes**: Christian la crea mañana como secreto en el panel de ElevenLabs (nombre propuesto en la guía: `BOOSTR_API_KEY`); no pasa por el chat, el repo ni GitHub. Sin acción de la spec; se anota como dependencia.

## Dudas para el integrador

Se abrieron como handoffs en `docs/equipo/handoffs/`; ambos respondidos con la guía técnica del integrador (2026-10-18):

1. **Propietario fuera del contexto del agente** (`004-analista-a-integrador-propietario-fuera-del-contexto.md`): respuesta: filtro de respuesta de la plataforma (opción B); no probado, el registro interno no está documentado. Efecto: FR-003 en dos niveles y Etapa 0.
2. **Fallos, límites y pruebas** (`005-analista-a-integrador-fallos-limites-y-pruebas.md`): respuesta: tiempo propuesto de 10 s sin reintento automático, mensajes por tipo de falla, pruebas con respuestas simuladas, patentes sintéticas que nunca se envían a la API real. Efecto: SC-002 y SC-006.
3. **Ajustes de la spec** (`006-integrador-a-analista-garantia-de-privacidad-y-ajustes-spec-cdu-002.md`): aplicados en esta versión (FR-003, SC-001a/b, SC-002, Historia 2 escenario 3, FR-009/AC-15, FR-013).

## Impacto en la constitución *(solo propuesta; no se edita la constitución)*

| Principio | Cómo lo toca este CDU | ¿Enmienda? |
| --- | --- | --- |
| VII Privacidad mínima | La patente y, sobre todo, el propietario que la fuente devuelve podrían entrar al contexto y a los registros de la plataforma. Esta spec dice para qué se usa cada dato (tabla de privacidad) y prohíbe guardar. Pero "solo se guardan datos si la spec dice para qué" no cubre datos que **llegan sin que se pidan** y se registran por defecto. Con la opción B el propietario no llega al modelo (por probar), pero el servidor de la plataforma recibe la respuesta completa antes de filtrarla, y lo que retiene no está documentado (handoff 006). Además, la patente de Christian en el repo choca con "el repo no contiene datos personales" si resulta ser dato personal (por eso sigue el marcador). | **No hace falta enmienda con la opción B** si la Etapa 0 pasa. Sigo proponiendo una aclaración (PATCH o MINOR) a VII para dejar escrito el caso: "los datos personales que una fuente externa devuelva sin ser necesarios MUST NOT ingresar al contexto del agente; si no se pueden excluir, el CDU no se construye". La decide Christian. |
| VIII Simplicidad | Consultar la API exige una herramienta externa (webhook de la plataforma, sin backend propio). Principio VIII lo permite solo si un CDU demuestra con evidencia que es necesario, justificado por escrito en el `plan.md`. La evidencia sería SC-007 (comparación con la pregunta directa); sin ella, no se justifica y se retira. | No hace falta enmienda si el plan incluye la justificación. Sí haría falta (MINOR, aprobación de Christian) si se pasara a un backend mínimo propio (alternativa de respaldo c). |
| III Respuestas fundamentadas en el manual | La patente aporta datos que no vienen del manual. Se limitan a identificar el auto, no a responder sobre él (FR-006). | No; basta con la regla. |
| IV Cero credenciales | La clave de la API de patentes es una credencial nueva; hoy el principio solo nombra `ELEVENLABS_API_KEY` y el Environment `POC`. | Aclaración menor (PATCH): extender la regla a toda credencial del proyecto. Dónde se guarda la clave lo decide el integrador (handoff 004). |
| VI Honestidad operativa | Nada de la API está probado. Esta spec lo declara y marca [PATENTE_DE_CHRISTIAN] como "por probar". | No. |
| Restricciones: "Fuente de conocimiento: únicamente el manual" | La consulta añade una segunda fuente de datos, aunque de identificación y no de conocimiento. | Posible aclaración (PATCH) para evitar la ambigüedad. |

Esta spec pasa a Aprobada cuando: (1) Christian responda la pregunta 3 (la patente como dato personal) y las demás abiertas que afecten criterios (4, 5, 6, 7, 10, 11, 12); (2) se pase la **Etapa 0** de la guía técnica (el propietario no llega al modelo, con resultado documentado); y (3) los ajustes del handoff 006 queden reflejados, lo que ya se hizo en esta versión. Ya no depende de la pregunta 8, resuelta.

## Definición de "hecho"

CDU-002 está **Hecho** cuando: (1) AC-01 a AC-20 pasan, con pruebas automatizadas (respuestas simuladas) o chequeos manuales descritos, y AC-19 se probó de verdad con la API real; (2) la Etapa 0 pasó y SC-001a, SC-001b y SC-002 a SC-009 se cumplen y quedan registrados, distinguiendo lo probado de lo no probado; (3) no quedan `[POR DEFINIR]` sin resolver; (4) el plan del integrador incluye la verificación contra los principios VII y VIII y, si se enmendó la constitución, la enmienda está aprobada por Christian; (5) las limitaciones conocidas (dato desactualizado, dependencia de un servicio en beta, tope de consultas eludible) están declaradas.

## Registro de decisiones

- 2026-10-18, **Respuesta de Christian** (mensaje real): "Acepto la opción B, yo creo mañana el secreto. Acepto usar mi nombre y rut. Redacta todo para Chile, el manual es el mismo. Acepto que pueda dejar de funcionar, es una POC." Efecto: preguntas 1, 8 y 9 resueltas; país Chile en CDU-001 y CDU-002; la clave la crea Christian en el panel de ElevenLabs. Sigue abierto: 3, 4, 5, 6, 7, 10, 11 y 12.
- 2026-10-18, handoffs 004 y 005 respondidos por el integrador; ajustes del 006 aceptados por el analista (ver el propio handoff).

## Historial

- 2026-10-18: Propuesta inicial. Ningún dato de la API se probó; clave en trámite por Christian.
- 2026-10-18: Estado "Propuesta (decisiones parciales)": decisiones de Christian incorporadas, país Chile, FR-003 en dos niveles, SC-001 desdoblado, motor fuera del MVP, tope por prompt y excepción en el prompt de CDU-001 (FR-013), números de emergencia de Chile propuestos (FR-014).
