# Extractor: cómo extraer la información de un documento

Este documento define **cómo extraer el contenido de un archivo puesto en `sources/`**
para que el resultado sea:

1. **Completo**: el 100% de la información del original (texto, tablas, listas, enlaces,
   figuras, datos de gráficos, notas).
2. **Eficiente**: se hace con scripts locales, no "leyendo" el archivo entero.
3. **Barato en tokens**: el resultado es Markdown limpio, sin repeticiones ni relleno.

El resultado sirve como fuente para leer, resumir, consultar o **regenerar** el documento
(ver [generator.md](generator.md)).

---

## 1. Reglas de oro (leer antes de empezar)

| Regla | Por qué |
|---|---|
| **Nunca abrir el original directamente en el contexto** (por ejemplo, leer un PDF página por página como imagen). | Cada página leída como imagen cuesta muchos más tokens que su texto, y el texto queda impreciso. |
| **Extraer con `tools/extraer.py`** y leer primero solo `reporte.md`. | El reporte ocupa pocas líneas y dice exactamente qué falta revisar. |
| **Usar la vista (imágenes) solo donde el reporte lo pida**: figuras, gráficos, páginas escaneadas, tablas sin bordes. | Es la única información que el texto no trae. |
| **Transcribir, no resumir.** | Un resumen pierde información; la meta es el 100%. |
| **Eliminar solo lo redundante**: encabezados y pies repetidos, índice, puntos guía, espacios. | Lo eliminado se guarda una vez en un comentario, así no se pierde nada. |
| **Escribir los resultados en archivos y mostrar solo resúmenes en la terminal.** | Lo que se imprime en la terminal también consume tokens. |
| **No volver a extraer lo ya extraído.** Si `extracted/<nombre>/` existe y el original no cambió, reutilizarlo. | Evita trabajo y tokens repetidos. `extraer.py` lo aplica solo: si el original no cambió no hace nada, y si el `.md` fue editado a mano se niega a pisarlo. Con `--forzar` extrae de nuevo y guarda el anterior como `<nombre>.anterior.md`. |

---

## 2. Estructura de carpetas

```
sources/                 originales (no se modifican nunca)
extracted/<nombre>/      resultado de la extracción
    <nombre>.md          contenido completo en Markdown
    assets/              imágenes, recortes de gráficos y páginas escaneadas
    reporte.md           resumen: cobertura y pendientes
    fuente.json          registro del original (nombre y huella); no se edita
documentos/              versiones preparadas para generar (ver generator.md)
output/<nombre>/         PDF generado, su registro de verificación y sus hojas de revisión
tools/extraer.py         extractor
tools/region.py          una franja de una página del original: texto con columnas o recorte
tools/validar.py         estructura del .md (lo que la cobertura no ve)
tools/comparar.py        verificación de palabras contra el original
```

---

## 3. Paso 0: identificar el formato

| Formato | Cómo se extrae | Qué se conserva |
|---|---|---|
| `.pdf` | `tools/extraer.py` (PyMuPDF) | Texto con títulos, negrita, cursiva y código; superíndices y subíndices; listas; tablas; enlaces en su frase; imágenes (JPEG tal cual, transparencia conservada, una referencia por cada aparición); gráficos vectoriales; datos de portada; marcadores. |
| `.docx` | `tools/extraer.py` (python-docx) | Títulos por estilo, formato, hipervínculos con su dirección, listas con viñetas o numeradas y su nivel, tablas en su orden (una celda combinada, una sola vez), imágenes, encabezado, propiedades. |
| `.pptx` | `tools/extraer.py` (python-pptx) | Una sección por diapositiva (las ocultas, marcadas `(oculta)`), viñetas con nivel, tablas, imágenes, **datos de los gráficos** y **notas del orador**. |
| `.xlsx` / `.xlsm` | `tools/extraer.py` (openpyxl) | Una tabla por hoja (las ocultas, marcadas `(oculta)`), sin filas ni columnas vacías. Valores calculados; si no hay valor guardado, la fórmula. Porcentajes con su signo y fechas sin hora. |
| `.json` | `tools/extraer.py` | Listas de objetos → tablas (las claves se escriben una sola vez); objetos → listas `clave: valor`. |
| `.csv` / `.tsv` | `tools/extraer.py` | Tabla Markdown (detecta `,` `;` tab o `|`; una sola columna también). Un salto de renglón dentro de un campo queda como `<br>`. |
| `.md` / `.txt` | `tools/extraer.py` | Se conserva tal cual; solo se limpian espacios y líneas vacías sobrantes. |

Los archivos de texto se leen en UTF-8, UTF-16 o cp1252 (lo que guardan Excel y el Bloc
de notas de Windows). Un archivo protegido con contraseña o dañado termina en un mensaje
de una línea y código 2.

| Formato | Cómo se extrae | Qué se conserva |
|---|---|---|
| `.doc` `.ppt` `.xls` `.odt` `.rtf` | Convertir primero: `soffice --headless --convert-to docx archivo.doc` (o `pdf`). Sin LibreOffice: abrir y "Guardar como" `.docx`/`.xlsx`/`.pptx`. | Igual que el formato convertido. |
| `.html` | Guardar como PDF desde el navegador (o `pandoc archivo.html -o archivo.docx`) y extraer ese archivo. | Igual que el formato convertido. |
| Imagen (`.png`, `.jpg`) o PDF escaneado | Lectura visual: abrir la imagen y transcribir. No hay OCR (Tesseract) instalado. | Transcripción literal + descripción de lo visual. |

Requisitos: `pip install -r requirements.txt`.

---

## 4. Procedimiento

### Paso 1: extraer

```
python tools/extraer.py sources/<archivo>
```

La terminal muestra dos rutas y una línea «Pendientes:». No imprimir el Markdown completo.

| Código | Significa |
|---|---|
| 0 | Extraído y sin pendientes. |
| 1 | Extraído, con pendientes: los nombra la línea «Pendientes:» y los detalla `reporte.md`. |
| 2 | No se extrajo: formato no admitido, archivo protegido o dañado, o hay trabajo manual que se pisaría. |

Las hojas de Excel y los CSV de más de 2.000 filas se recortan y el reporte lo dice;
`--filas 0` extrae todas.

### Paso 2: leer el reporte (siempre primero)

```
extracted/<nombre>/reporte.md
```

Indica: páginas, títulos detectados, tamaño aproximado en tokens, cobertura de palabras
y la lista de pendientes. Si dice **"Cobertura 100% en todas las páginas; sin
observaciones"** y no hay figuras pendientes, la extracción está terminada (código 0).
La sección «Notas (no requieren acción)» es informativa: portada pasada a la cabecera,
índice original omitido. Solo figuran como pendientes las figuras sin pie.

### Paso 3: resolver los pendientes (solo los que aparecen)

| Pendiente en el reporte | Qué hacer | Cómo dejarlo en el `.md` |
|---|---|---|
| **Figura pendiente de describir** (`![FIGURA: describir](assets/...)`) | Abrir la imagen de `assets/`. Si es decorativa (logo, adorno), decirlo en 2-3 palabras. Si tiene información, transcribir todo el texto que contenga y describir lo que muestra. | Reemplazar `FIGURA: describir` por un pie corto. Debajo: `<!-- DESCRIPCIÓN: ... -->` con la transcripción y la descripción. |
| **Gráfico** (`p<N>-vec<M>.png` o imagen con ejes) | Leer los valores y pasarlos a tabla. | `<!-- DATOS DEL GRÁFICO: ... -->` con una tabla Markdown, o una tabla visible si el dato es importante. |
| **Página escaneada** (`PÁGINA ESCANEADA p.N: TRANSCRIBIR`) | Abrir `assets/p<N>-escaneada.png` y transcribir literalmente, con títulos, listas y tablas en Markdown. | Reemplazar la línea de la imagen por la transcripción. |
| **Posible tabla sin reconstruir** | Abrir el recorte `assets/p<N>-tabla<M>.png`. El texto ya está en el `.md` como párrafos sueltos: buscarlo y convertirlo en tabla Markdown. (Las tablas con bordes o con líneas horizontales se reconstruyen solas.) | Tabla Markdown en el mismo lugar. |
| **Dos columnas: verificar orden** | Abrir esa página solo si el texto se lee desordenado en el `.md`. | Reordenar párrafos. |
| **Cobertura < 100% con palabras faltantes** | Buscar esas palabras en el original con un script (no a ojo) y agregarlas en su lugar. | Texto agregado en su posición. |
| **Faltan en ...** (Word, PowerPoint, Excel) | El reporte dice en qué parte del archivo está lo que no se extrajo: pies de página, notas al pie, cuadros de texto, SmartArt, comentarios. La cobertura se calcula contra el archivo real, no contra lo extraído. | Agregar ese texto en su lugar, o en un comentario si es un pie repetido. |
| **Imágenes en el original: N \| extraídas: M** | Hay imágenes que no se guardaron (por ejemplo, las de un marcador de posición de PowerPoint). | Exportarlas con un script a `assets/` y referenciarlas. |
| **Texto único en la zona de encabezado/pie, conservado en el cuerpo** | Suele ser una nota al pie: aparece una sola vez, así que no se trató como pie repetido. | Dejarlo donde corresponde (junto a su llamada) o borrarlo si de verdad era un pie. |
| **Renglones de código reunidos** | El extractor unió renglones que el original partió por falta de ancho. Siempre hace falta que la primera palabra del siguiente no cupiera al final del anterior. Si el siguiente empieza en el borde izquierdo, se une cuando el anterior quedó a medias (comillas o paréntesis sin cerrar, o termina en coma u operador). Si viene 4 letras más adentro (E22), se une cuando el corte cayó a media palabra, en un comentario, con comillas o un paréntesis abierto, antes de un cierre (`);`, `};`, `/>`) o entre dos palabras sin un final de autor (coma, paréntesis, operador, la cabecera de un `if`). El reporte lista cada unión al final, con su página. | Revisar **todas**: si lo unido es otra instrucción, separarlo en su propio renglón con su sangría. |
| **Renglones de código que podrían estar partidos (no se unieron)** | No cabían juntos, pero el segundo tiene sangría propia o el primero está completo (o es un comentario): se dejaron como en el original. | Leer la lista. Unir a mano solo los que continúan la misma instrucción. |
| **Diagramas con texto** (`assets/p<N>-diagrama<M>.png`) | Cajas unidas por flechas: el texto de las cajas y de las flechas ya está en el `.md`, pero suelto y sin decir qué se conecta con qué. Pasarlo a `describir-figuras`. | `<!-- DIAGRAMA ORIGINAL (p.N): ... -->`, una tabla `Componente / Detalle` y otra `Desde / Hacia / Conexión`, en lugar del texto suelto. La imagen no se inserta. |
| **Símbolos sin mapa de caracteres** | La fuente del original no dice qué carácter es (casillas, flechas): quedan como `[SIMBOLO?]` en el `.md`. `validar.py` los rechaza. | Reemplazar cada uno por el símbolo que se ve en esa página (una casilla vacía: `[ ]`). |
| **Guiones conservados al final de un renglón** | Un renglón terminaba en guion y la palabra unida no aparece en otra parte del documento: puede ser un corte (`docu-mentación`) o un guion real (`físico-químico`). Se dejó con guion. | Quitar el guion si era un corte de renglón. |
| **Superíndices o subíndices sin carácter propio** | Los que tienen carácter propio se conservan (`10³`, `H₂O`); el resto quedó en línea (`xcrit`). | Revisar que el sentido no cambie; si cambia, escribirlo de otra forma. |
| **Hoja o CSV: N filas; se extrajeron las primeras M** | La tabla pasa del límite de filas. | Si hacen falta todas: `--filas 0 --forzar`. Para cálculos, usar un script sobre el original. |

Para abrir imágenes, usar las de `assets/` (ya recortadas y en resolución moderada).
Nunca renderizar todas las páginas. Para una franja que el extractor no recortó:

```
python tools/region.py sources/<archivo> <página> imagen "<desde>" "<hasta>" extracted/<nombre>/assets/p<N>-diagrama.png
python tools/region.py sources/<archivo> <página> texto  "<desde>" "<hasta>"    # renglones con su columna
```

**Cobertura 100% no es una extracción correcta.** La cobertura cuenta palabras: no ve
títulos en el nivel equivocado, tablas partidas, rótulos dentro del código ni diagramas
aplanados. Eso lo revisa `tools/validar.py` sobre `documentos/` (generator.md, paso 3).

### Paso 4: verificar el 100%

La extracción está completa cuando se cumple todo:

- [ ] `reporte.md` muestra 100% de cobertura en todas las páginas (o los faltantes se agregaron a mano).
- [ ] No queda ningún `FIGURA: describir`, `TRANSCRIBIR` ni tabla sin reconstruir:
      `grep -n "describir\|TRANSCRIBIR\|SIMBOLO?" extracted/<nombre>/<nombre>.md` no devuelve nada.
- [ ] Los títulos detectados coinciden con los marcadores del PDF original (cuando los tiene),
      **en cantidad y en nivel**: `grep -c "^# "`, `"^## "`, `"^### "`. El nivel sale del
      marcador de la misma página (auditoría, E20); todos en un mismo nivel indica que el
      original no tiene marcadores o que no coinciden: se corrige al preparar.
- [ ] Ningún diagrama ni recuadro de texto quedó aplanado (negritas sueltas sin frases).
- [ ] Los enlaces conservan su URL (`[texto](url)` o línea `Enlaces:` al final de la página).
- [ ] La portada y los encabezados/pies quedaron en la cabecera o en comentarios.

---

## 5. Qué produce el extractor (formato del `.md`)

```
---
titulo: ...            datos de metadatos y portada, compatibles con manual.py
autor: ...
numerar: no            "no" si los títulos ya vienen numerados
fuente: original.pdf
---

<!-- ENCABEZADOS/PIES REPETIDOS (omitidos): ... -->    se guardan una sola vez
<!-- p.1 PORTADA ORIGINAL: ... -->                     texto literal de la portada
<!-- p.2 ÍNDICE ORIGINAL: ... -->                      índice comprimido, sin puntos guía
<!-- p.3 -->                                           marcador de página (rastreo)

# 1. Título de capítulo
Párrafos con **negrita**, *cursiva*, `código` y [enlaces](https://...).
- listas
| tablas | Markdown |
![pie de figura](assets/p4-img47.png)
```

Los comentarios `<!-- -->` no se imprimen al generar el PDF, pero conservan la
información para quien lea el `.md`.

---

## 6. Ahorro de tokens: cómo leer el resultado

- **Documentos cortos** (el reporte indica menos de ~20.000 tokens): leer el `.md` completo de una vez.
- **Documentos largos**: primero obtener el mapa de títulos con números de línea
  (`grep -n "^#" extracted/<nombre>/<nombre>.md`) y luego leer solo las secciones necesarias
  por rango de líneas.
- **Buscar un dato**: `grep -n "palabra" extracted/<nombre>/<nombre>.md` en lugar de leer todo.
- **Varias consultas sobre el mismo documento**: reutilizar la extracción, no repetirla.
- **Tablas grandes (Excel, CSV)**: leer solo encabezados y unas filas; para cálculos, usar un
  script sobre el archivo original en vez de leer todas las filas.

---

## 7. Errores comunes

| Problema | Causa | Solución |
|---|---|---|
| Texto con letras raras o vacío | PDF escaneado o con fuentes sin mapa de caracteres. | El reporte lo marca como escaneado: transcribir desde la imagen. |
| Palabras pegadas o cortadas con guion | Corte de línea del original. | El extractor une `pala-` + `bra` solo si «palabra» aparece en otra parte del documento. Si no, deja el guion y lo lista en el reporte para decidir. |
| Texto extraído con `[SIMBOLO?]` | La fuente del original no dice qué carácter es. | Reemplazarlo por el símbolo que se ve en esa página. |
| Un párrafo partido en dos | Continúa en la página siguiente. | Unirlo al preparar el documento (generator.md). |
| Bloque de código dividido | Cambio de página en el original. | Unir los dos bloques al preparar el documento. |
| Código sin sangría o con renglones partidos | El PDF da la sangría por posición y parte los renglones largos. | El extractor los reconstruye (sangría por posición, renglones reunidos). Sin recuadro de fondo ni texto normal en el documento no puede saber el ancho y no reúne nada. |
| "No se extrajo: el .md fue editado a mano" | Ya hay una extracción con trabajo manual. | Seguir usando esa. Solo si el original cambió: `--forzar` y recuperar el trabajo desde `<nombre>.anterior.md`. |
| Partes en `#`, capítulos en `##` y secciones en `###` | El extractor toma el nivel de los marcadores del PDF, también cuando el título de la página lleva un antetítulo («PARTE I · CAPÍTULO 1 …», auditoría E20). | Si el manual quiere los capítulos en `#` (cada uno en página nueva), pasarlos al preparar. |
| Una página de índice en el cuerpo | El extractor la reconoce también con los puntos guía de a uno (E21); si quedó alguna, el original usa otro dibujo. | Al preparar: cada página de índice a un comentario. |
| Un renglón de código cortado que no se unió | Con sangría +4 se une solo en los casos seguros (E22); tras una coma no se distingue de un argumento por renglón. | Revisar la lista de dudosos del reporte y unir a mano los que continúan la misma instrucción. |
| Una tabla salió como párrafos | Su dibujo no se pudo interpretar. | El reporte la marca; reconstruirla con el recorte. |
| "Formato no soportado" | Formato antiguo o poco común. | Convertir según el Paso 0. |
