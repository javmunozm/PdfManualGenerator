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
output/                  PDFs generados
tools/extraer.py         extractor
tools/comparar.py        verificación de cobertura
```

---

## 3. Paso 0: identificar el formato

| Formato | Cómo se extrae | Qué se conserva |
|---|---|---|
| `.pdf` | `tools/extraer.py` (PyMuPDF) | Texto con títulos, negrita, cursiva y código; listas; tablas; enlaces; imágenes; gráficos vectoriales; datos de portada; marcadores. |
| `.docx` | `tools/extraer.py` (python-docx) | Títulos por estilo, formato, listas, tablas en su orden, imágenes, encabezado, propiedades. |
| `.pptx` | `tools/extraer.py` (python-pptx) | Una sección por diapositiva, viñetas con nivel, tablas, imágenes, **datos de los gráficos** y **notas del orador**. |
| `.xlsx` / `.xlsm` | `tools/extraer.py` (openpyxl) | Una tabla por hoja, sin filas ni columnas vacías. Valores calculados; si no hay valor guardado, la fórmula. |
| `.json` | `tools/extraer.py` | Listas de objetos → tablas (las claves se escriben una sola vez); objetos → listas `clave: valor`. |
| `.csv` / `.tsv` | `tools/extraer.py` | Tabla Markdown (detecta `,` `;` tab o `|`). |
| `.md` / `.txt` | `tools/extraer.py` | Se conserva tal cual; solo se limpian espacios y líneas vacías sobrantes. |
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

La terminal solo muestra dos rutas. No imprimir el Markdown completo.

### Paso 2: leer el reporte (siempre primero)

```
extracted/<nombre>/reporte.md
```

Indica: páginas, títulos detectados, tamaño aproximado en tokens, cobertura de palabras
y la lista de pendientes. Si dice **"Cobertura 100% en todas las páginas; sin
observaciones"** y no hay figuras pendientes, la extracción está terminada.

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
| **Renglones de código reunidos** | El extractor unió renglones que cree que el original partió por falta de ancho. La regla une de más (auditoría, E17): el reporte lista cada unión al final, con su página. | Revisar **todas**: si lo unido es otra instrucción (otra variable, otra sentencia, texto detrás de un comentario), separarlo en su propio renglón con su sangría. |
| **Símbolos sin mapa de caracteres** | La fuente del original no dice qué carácter es (casillas, flechas): quedan como NUL en el `.md`. `validar.py` los rechaza. | Reemplazar cada uno por el símbolo que se ve en esa página (una casilla vacía: `[ ]`). |

Para abrir imágenes, usar las de `assets/` (ya recortadas y en resolución moderada).
Nunca renderizar todas las páginas.

### Paso 4: verificar el 100%

La extracción está completa cuando se cumple todo:

- [ ] `reporte.md` muestra 100% de cobertura en todas las páginas (o los faltantes se agregaron a mano).
- [ ] No queda ningún `FIGURA: describir`, `TRANSCRIBIR` ni tabla sin reconstruir:
      `grep -n "describir\|TRANSCRIBIR" extracted/<nombre>/<nombre>.md` no devuelve nada.
- [ ] Los títulos detectados coinciden con los marcadores del PDF original (cuando los tiene).
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
| Palabras pegadas o cortadas con guion | Corte de línea del original. | El extractor une los cortes `pala-\nbra`; revisar casos con guion real. |
| Un párrafo partido en dos | Continúa en la página siguiente. | Unirlo al preparar el documento (generator.md). |
| Bloque de código dividido | Cambio de página en el original. | Unir los dos bloques al preparar el documento. |
| Código sin sangría o con renglones partidos | El PDF da la sangría por posición y parte los renglones largos. | El extractor los reconstruye (sangría por posición, renglones reunidos). Sin recuadro de fondo ni texto normal en el documento no puede saber el ancho y no reúne nada. |
| "No se extrajo: el .md fue editado a mano" | Ya hay una extracción con trabajo manual. | Seguir usando esa. Solo si el original cambió: `--forzar` y recuperar el trabajo desde `<nombre>.anterior.md`. |
| Una tabla salió como párrafos | Su dibujo no se pudo interpretar. | El reporte la marca; reconstruirla con el recorte. |
| "Formato no soportado" | Formato antiguo o poco común. | Convertir según el Paso 0. |
