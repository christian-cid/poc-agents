# Manual del Haval H6 para la base de conocimiento (RAG)

Informe de calidad del pipeline `scripts/extract_manual.py`. Todas las cifras de este archivo salen de
`_cobertura.json` o de comandos ejecutados sobre el PDF real; lo que no se pudo medir se dice como tal.

**Qué se indexa y qué no.** Solo los 33 archivos `NN-*.md` de esta carpeta (476 717 bytes en total). `LEEME.md`
y `_cobertura.json` son material de control: no se suben a ElevenLabs. Esta sesión no sincronizó nada con
ElevenLabs (no hay clave): **no se ha probado que la plataforma indexe estos archivos ni que el agente los
recupere bien**.

## 1. Fuente

| Dato | Valor (medido) |
| --- | --- |
| Archivo | `manual-haval-h6_compressed.pdf` (no está en el repo; `*.pdf` está en `.gitignore`) |
| Tamaño / huella | 3 643 293 bytes, sha256 `7fe9fd8efd0ed56ca8b2702bfad3bb25cf7e799d2ae96921ec33ddef8bc2aa7b` |
| Páginas | 299; texto seleccionable (no hizo falta OCR) |
| Edición | Portada `2021.12- X HAVAL H6`; introducción fechada 06/09/2021 |
| Desfase de numeración | **página del PDF = página impresa + 3** en las 296 páginas que tienen número impreso (no +2) |

## 2. Qué hace el pipeline

1. **Entrada por página** con tres lecturas del mismo PDF: `pdftotext -raw` (cuenta oficial de caracteres),
   `pdftohtml -xml` (líneas con posición, tamaño, color, negrita y enlaces) y `pdftocairo -svg` (reglas de tablas
   y de recuadros). Se comprueba que el XML contiene exactamente los mismos caracteres que `pdftotext -raw` en las
   299 páginas.
2. **Estructura** desde el propio PDF, sin adivinar por texto: la banda azul superior da el título de cada sección
   (67 secciones; sus títulos coinciden con los del índice del manual, sin faltantes ni sobrantes); el tamaño/color da los títulos (18 pt azul), subtítulos
   (negrita) y avisos (etiquetas Nota / Atención / Advertencia).
3. **Limpieza** conservadora: cada fragmento de texto se conserva o se descarta bajo una categoría registrada.
4. **Párrafos** reconstruidos por interlineado (21 px dentro del párrafo, 23-25 px entre párrafos), continuando
   frases entre columnas y páginas.
5. **Tablas** reconstruidas con las reglas dibujadas (ver sección 5).
6. **Troceo**: un documento por capítulo y secciones contiguas; las secciones pequeñas se fusionan hasta
   ~8 KB y ningún documento pasa de 40 KB. Resultado: 33 documentos de 7 103 a 30 126 bytes.
7. **Informe** `_cobertura.json` por página.

## 3. Cómo reproducirlo

```bash
# requiere poppler-utils (pdftotext, pdftohtml, pdftocairo) y Python 3.10+; sin dependencias de pip
python3 scripts/extract_manual.py RUTA/AL/manual-haval-h6_compressed.pdf          # regenera esta carpeta
python3 scripts/extract_manual.py RUTA/AL/manual-haval-h6_compressed.pdf --check  # solo verifica; no escribe
python3 -m pytest scripts/tests -q                                                 # pruebas (MANUAL_PDF=ruta para las que usan el PDF)
```

`--check` regenera en memoria, compara byte a byte con lo que hay en disco y valida las invariantes (páginas sin
ubicar, tamaños, chino, palabras cortadas, contabilidad de caracteres). Sale con código 1 si algo falla.
El resultado es determinista: dos ejecuciones dan los mismos bytes (probado en `scripts/tests`).

## 4. Cobertura medida

| Medida | Valor |
| --- | --- |
| Páginas totales / con texto / sin texto | 299 / 295 / 4 (PDF 2, 3, 241, 285) |
| Páginas con contenido sin ubicar en un documento | **0** |
| Caracteres de entrada (`pdftotext -raw`) | 473 046 (396 023 sin espacios) |
| Caracteres de salida (texto de los `.md` atribuido a páginas, sin front matter) | 413 983 (350 536 sin espacios) |
| Tamaño total de los `.md` | 476 717 bytes; holgura frente a 2 000 000 bytes: 1 523 283 (76,2 %) |
| Contabilidad por página: entrada = conservado + descartado | cumple en las 299 páginas |
| Contenido conservado completo en la salida | cumple en las 299 páginas |

**Corrección a datos previos.** Las 10 páginas "sin texto" (1, 2, 3, 9, 11, 52, 91, 233, 241, 285) no son todas
vacías. Solo 2, 3, 241 y 285 no tienen contenido (únicamente el número de página). La 1 es la portada, y la 9, 11, 52,
91 y 233 **sí tienen texto real**: son el final de una lista o de un párrafo que cruzó de página (p. ej. el PDF 233
termina una advertencia sobre sillas infantiles con "…incluso la muerte"). Se conservaron y se ubican. Además hay 4
páginas con menos de 100 caracteres que también se conservaron (PDF 167, 173, 286, 294).

### Qué se descartó (caracteres sin espacios; todo registrado en `_cobertura.json`)

| Categoría | Caracteres | Detalle |
| --- | --- | --- |
| Aviso repetido "Equipamiento del vehículo…" | 28 685 | 62 apariciones idénticas (una por inicio de sección). Se conserva la versión distinta de la p. impresa 2 (PDF 5) |
| Pestaña lateral de capítulo | 3 314 | número y nombre del capítulo en el margen |
| Códigos de figura (`2F1830D38071`…) | 2 220 | 185 códigos |
| Números de página | 780 | pies de página |
| Texto chino de la portada | 30 | `书脊厚度默认设计为16mm…` |
| Portada repetida | 7 | "HAVAL" y "H6" duplicados |
| Convertidos en título (se conservan) | 1 722 | banda superior y número de capítulo de las portadillas |

El resto no se quitó: de 396 023 caracteres de entrada sin espacios se descartaron 35 036 (8,8 %).

## 5. Decisiones de formato

- **Remisiones de página.** El manual cita páginas de dos formas: `Limpiaparabrisas trasero 66` (número azul con
  enlace) y `(▷ Page 18)`. Se convierten **de forma consistente** a `(ver p. N)`, con N = página **impresa**
  (los 238 números azules enlazan a la página N+3 del PDF, sin excepciones). Son útiles porque el agente puede decir "ver p. 66 del
  manual". Los puntos guía de los índices (`Llave ……… 18`) pasan a `Llave — p. 18`.
- **Marcadores de página.** Una línea `[p. N]` (página impresa) donde empieza el primer bloque nuevo de cada página.
- **Avisos.** Cada recuadro es un bloque de cita `> **Nota:** …`, `> **Atención:** …` o `> **Advertencia:** …`, con
  la palabra al inicio. Hay 141 / 100 / 101, igual que las etiquetas del PDF. El final del recuadro se detecta por
  su filete inferior, también cuando continúa en la columna o página siguiente.
- **Tablas como registros.** Cada fila es una línea `- Campo: valor; Campo: valor`, con la cabecera repetida en
  cada fila para que se entienda sola (guía 3.5). Se eligió esto y no tablas con barras porque hay celdas
  combinadas (varias filas o columnas) que una tabla markdown no representa sin duplicar o dejar huecos. Cuando
  hay varias cabeceras apiladas se concatenan con `›`. Varios valores dentro de una celda se separan con ` / `.
- **Figuras.** Se marca `[figura no incluida]` **una vez por sección** (la primera figura). No se describe nada de
  lo que muestra una figura. Los iconos de la columna "Iconos" de la barra de estado (pp. 201-204) se marcan
  `Iconos: [icono no incluido]` por fila.
- **Letras Ⓐ Ⓑ…** se conservan unidas a su texto en las leyendas (`- Ⓐ Llave inteligente`) porque el texto
  del manual las cita; no hay etiquetas sueltas sin texto. Las viñetas `〉` pasan a `-`.
- **Símbolos asiáticos.** Los corchetes `【】` y paréntesis `（）` del manual pasan a `[]` y `()`; `、` pasa a `, `.
- **Erratas del manual** (p. ej. "servio Great Wall", "LSC TRANSM.F LUID") se conservan tal cual.

## 6. Qué NO se pudo capturar

- **Iconos de las luces del tablero** (40 luces, PDF 183-191). Son dibujos vectoriales dentro de la página: ni
  `pdftotext` ni `pdfimages` los ven. Cada luz queda con **nombre, significado y acción tal como los dice el
  manual**, y el documento lo avisa en una nota del equipo. El agente no puede reconocer una luz por su forma.
  Los índices del capítulo 8 (PDF 295-299) también llevan icono en el original y aquí solo el nombre.
- **Imágenes y diagramas** (422 imágenes, 185 códigos de figura en 121 páginas): ubicación de controles,
  procedimientos ilustrados. Solo queda el texto que las acompaña.
- **Celdas de tablas que son imágenes** (columna "Iconos").
- **Negritas y subrayados** no se conservan, salvo cuando una línea en negrita es un título corto. Una frase
  completa en negrita queda como párrafo normal.

## 7. Muestras reales (antes → después)

**Muestra 1.** PDF 21, inicio del capítulo 1 (aviso repetido, código de figura, viñetas, corte de palabra, pie).

Antes (`pdftotext -raw`):
```
Equipamiento del vehículo
Favor tenga en cuenta que este manual
incluye todos los equipamientos estándar,
... (aviso de 14 líneas) ...
Información de la llave
25AD69C6CC4B
Ⓐ Llave inteligente
Ⓑ Tarjeta de códigos de la llave
Nota
〉 Por favor, guarde apropiadamente la tar-
jeta de códigos de la llave. Esta tarjeta
...
18
1
Operación
```
Después:
```
## Llave

[p. 18]

### Información de la llave

[figura no incluida]

- Ⓐ Llave inteligente
- Ⓑ Tarjeta de códigos de la llave

> **Nota:**
> - Por favor, guarde apropiadamente la tarjeta de códigos de la llave. Esta tarjeta tiene los códigos ...
```

**Muestra 2.** PDF 7, leyenda con remisiones (números sueltos tras cada ítem).

Antes:
```
Exterior
2F1830D38071
Ⓐ Limpiaparabrisas trasero 66
Ⓙ Tapa del gancho de remolque tra-
sera 255
```
Después:
```
#### Exterior

[figura no incluida]

- Ⓐ Limpiaparabrisas trasero (ver p. 66)
- Ⓙ Tapa del gancho de remolque trasera (ver p. 255)
```

**Muestra 3.** PDF 185 (p. impresa 182), luces del tablero: dos columnas, títulos en negrita partidos en líneas, guiones.

Antes:
```
Luz indicadora de alarma de
120km/h
Si esta luz está encendida, la
velocidad del vehículo supera a
los 120 km/h.
Luz de advertencia de falla en
las bolsas de aire
```
Después:
```
#### Luz indicadora de alarma de 120km/h

Si esta luz está encendida, la velocidad del vehículo supera a los 120 km/h.

#### Luz de advertencia de falla en las bolsas de aire
```

**Muestra 4.** PDF 290 (p. impresa 287), tabla de neumáticos: en el texto plano las celdas combinadas se
desordenan y se pierde qué dato es de qué fila.

Antes:
```
Ítem Datos
Especifica-
ciones
Neumático están-
dar
225/60 R18 100V
225/55 R19 99V
Rueda de repuesto T135/90 R17 104M
```
Después:
```
- Ítem: Especificaciones › Neumático estándar; Datos: 225/60 R18 100V / 225/55 R19 99V
- Ítem: Especificaciones › Rueda de repuesto; Datos: T135/90 R17 104M
```

**Muestra 5.** PDF 247 (p. impresa 244), procedimiento paso a paso del capítulo 5: códigos de figura entre pasos.

Antes:
```
2. Desmonte la cubierta decorativa para
pernos de rueda.
0E6D92D2A7C3
Para vehículos equipados con la cu-
bierta decorativa para pernos de rue-
da, primero quite la cubierta ...
```
Después:
```
2. Desmonte la cubierta decorativa para pernos de rueda.

[figura no incluida]

Para vehículos equipados con la cubierta decorativa para pernos de rueda, primero quite la cubierta ...
```

## 8. Verificación visual hecha (PDF renderizado con `pdftoppm` y comparado con el `.md`)

PDF 44 (cap. 1, tabla de combustible), 106 (cap. 2, tabla Secuencia/Modo/Uso y avisos), 125 (cap. 2, tabla de
radar), 185 (cap. 2, luces; el resto 183-191 se leyó en el `.md` contra el texto original), 204 (cap. 3, tabla de
iconos), 228 (cap. 4, tabla de sillas infantiles, 5 columnas con cabeceras anidadas), 247 (cap. 5, procedimiento),
270 (cap. 6), 289, 290 y 292 (cap. 7, especificaciones) y 299 (cap. 8, índice de luces). Además, una comparación
automática de la secuencia de palabras contra `pdftotext` en 17 páginas de los 8 capítulos no encontró cambios de
orden. **No se revisaron visualmente las 299 páginas.**

Resultado de la revisión de tablas: **ninguna tabla deformada tras los arreglos**; se corrigieron dos fallos
propios durante la verificación (un dato "Rueda de repuesto T135/90…" leído como una sola celda por cruzar una
regla vertical, y valores de una celda unidos sin separador). La revisión humana de los números de las 18
páginas con tablas (SC-004) sigue pendiente.

## 9. Límites conocidos

- **Párrafos**: la reconstrucción usa interlineado; un párrafo puede quedar unido a otro o partido en casos raros
  (7 párrafos empiezan en minúscula tras revisar; algunos son legítimos).
- **Tablas**: se detectan por reglas dibujadas (28 tablas en 18 páginas). Una tabla sin bordes se leería como texto.
  Las celdas vacías no se reproducen. El separador ` / ` entre valores de una celda es una heurística de
  interlineado.
- **Recuadros de aviso** que cruzan páginas: el final se infiere; si una tabla o figura queda dentro de un aviso,
  el aviso se cierra ahí.
- **Variantes dentro del manual**: hay datos por motor (GW4N20 / GW4B15D), tracción, caja DCT y región. El pipeline
  no los separa; las filas llevan el modelo en cada registro, pero el agente deberá pedir la variante (handoff 003).
- `00-contenido-del-manual.md` (índice y portadillas de capítulo) puede meter ruido en la recuperación;
  conviene decidir con pruebas del agente si se indexa. Los capítulos 1 a 8 no dependen de él.
- Nada de esto se ha probado contra ElevenLabs: tamaño, indexado RAG y recuperación siguen **bloqueados** a la
  espera de la clave y de la cuenta.
