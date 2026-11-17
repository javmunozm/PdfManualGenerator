# Auditoría del sistema: errores encontrados y mejoras pendientes

Fecha: 10/11/2026. Alcance: `manual.py`, `tools/extraer.py`, `tools/comparar.py`,
`docs/`, `README.md`, la demostración incluida y la configuración de Claude Code.

Este documento registra lo que falla y lo que falta implementar. El estado de cada
punto está en la sección 1.1.

---

## 1. Resumen

| Componente | Crítico | Alto | Medio | Bajo |
|---|---|---|---|---|
| Extractor (`tools/extraer.py`) | 3 | 5 | 6 | 2 |
| Generador (`manual.py`) | 0 | 9 | 4 | 2 |
| Verificador (`tools/comparar.py`) | 1 | 2 | 2 | 0 |
| Documentación y estructura | 0 | 1 | 4 | 0 |
| Configuración de Claude Code | 0 | 2 | 2 | 0 |

Los cinco hallazgos que más importan:

1. **El sistema promete "100% de la información" pero sus dos verificaciones no pueden
   comprobarlo.** El reporte del extractor da "100%" con contenido perdido (E1, E3, E4) y
   `comparar.py` da "100%" con dos tercios del documento borrados o con cifras
   intercambiadas (C1).
2. **Volver a extraer borra el trabajo manual** (descripciones de figuras,
   transcripciones) sin aviso, y dos archivos con el mismo nombre se pisan (E2).
3. **El extractor produce Markdown que el generador no acepta**: `***texto***` lo hace
   fallar; `\|` y `<br>` rompen las tablas (E7, G1, G6).
4. **La etapa "preparar" no tiene herramienta**: son 12 ajustes manuales, y la demostración
   de ida y vuelta se generó saltándosela (D1).
5. **La regla "no usar `sources/` sin permiso" no está forzada por nada**, y la
   configuración global de Claude Code dice lo contrario (K2, K3).

Lo que sí funciona: la ida y vuelta de `ejemplo.pdf` conserva 21 de 21 marcadores y el
99,5% de las palabras; las tablas de líneas horizontales se reconstruyen; los scripts
escriben a archivos y muestran pocas líneas en la terminal.

### 1.1 Estado (10/11/2026: fases 1, 2 y 3 implementadas)

| Estado | Puntos |
|---|---|
| **Resuelto**, con prueba en `tests/` | E1, E2, E3, E7, E9, E16, G1, G6, G7, G14, G15, C1, C2, C3, C4, D1 (`preparar.py`, `validar.py` y la ida y vuelta del ejemplo), K2 (hook H1 y H2), D5 (41 pruebas) |
| **Resuelto**, sin prueba automática | K1 (`CLAUDE.md`), D4 (git, `.gitignore`), D2 (`README.md`) |
| **Parcial** | G9: un título con `<` ya no rompe el índice; un enlace en un título sigue saliendo tal cual. G8: `validar.py` detecta esos casos antes de generar y `manual.py` avisa si no pudo interpretar una línea; falta `--estricto` en el generador. G13: `preparar.py` agrega el capítulo que falta; el generador todavía numera 0.1 si no se preparó. C5: mensaje claro para otros formatos; sigue sin compararlos ni comparar estructura. D3: `requirements.txt` y revisión visual sin `pypdfium2`; falta `tools/revisar.py`. K3: contexto de este proyecto en `.claude/settings.local.json`; la configuración global no se tocó. E8: `comparar.py` ya une las palabras cortadas; el reporte del extractor todavía no. |
| **Resuelto** (sección 9) | Skills (9.2, más `costo` y `traducir-manual`), subagentes (9.4, más `traductor`) y T1 (`tools/comparar_traduccion.py`). Además `tools/costo.py` y `tools/capitulos.py`. Las herramientas tienen prueba; las skills y los subagentes solo se comprobaron en su formato, no en una tarea real. Ver `docs/pipeline.md`. |
| **Pendiente** | Fases 4 y 6, y de la 5: hooks H3, H4 y H5, `tools/estado.py` y `tools/revisar.py`. **Todo esto quedó resuelto el 15/11/2026: ver la sección 13, que reemplaza a esta tabla.** |

Notas sobre lo resuelto:

- **E3** resuelve la *detección*: el reporte ahora dice qué falta y en qué parte del
  archivo. Que el extractor recoja ese contenido solo sigue pendiente (E5, E12).
- **E16** se probó con un PDF de prueba que imita el caso (recuadro con letra grande,
  renglones partidos, sangría por posición, pie de dos líneas lejos del borde). No se
  probó con el manual real: requiere permiso para usar ese archivo de `sources/`.
- **Los hooks** se probaron entregándoles llamadas simuladas. Para que queden activos
  hay que abrir `/hooks` una vez o reiniciar Claude Code.
- **D1**: la ida y vuelta del ejemplo pasa ahora por `preparar.py` y `validar.py`, y
  `comparar.py` la aprueba sin excepciones. De los 6 cuadros, 5 se reconstruyen solos; el
  sexto ("Antes de entregar") queda como pendiente porque su tipo no se puede deducir del
  texto. Tampoco se deduce una cita simple (queda como párrafo en cursiva). Las carpetas de
  la demostración son locales: no se versionan.
- **Listas anidadas** (sección 6): siguen aplanándose; `validar.py` lo avisa.

---

## 2. Método

- Lectura completa del código y de la documentación.
- Pruebas con archivos **creados para la auditoría** (PDF, Word, PowerPoint, Excel, CSV,
  JSON, TXT y Markdown), fuera del proyecto. **No se abrió ni se listó `sources/`.**
- Los archivos de prueba eran temporales: cada error incluye lo necesario para reproducirlo.
- Entorno: Windows 11, Python 3.13, ReportLab 5.0.1, PyMuPDF 1.28.2, consola en cp1252.

En las tablas, **Probado** significa que se reprodujo; **Lectura** significa que se dedujo
del código y falta confirmarlo con una prueba.

Severidad: **Crítico** = pérdida de información sin aviso o verificación que aprueba algo
falso. **Alto** = fallo o resultado incorrecto en un caso común. **Medio** = caso menos
frecuente o con aviso. **Bajo** = detalle.

---

## 3. Errores del extractor (`tools/extraer.py`)

| ID | Sev. | Error | Evidencia | Corrección |
|---|---|---|---|---|
| E1 | Crítico | Si el 60% de las páginas tiene texto en la franja superior o inferior (6,5% de la página), **todo** el texto de esa franja se elimina del cuerpo, también el que aparece una sola vez (una nota al pie). Solo queda en el comentario de encabezados, con las cifras reemplazadas por `#`. El reporte dice "Cobertura 100%; sin observaciones". | Probado: PDF de 4 páginas con encabezado repetido y una nota al pie en la página 2 ("la dosis máxima es 250 mg cada 8 horas según la norma 4471"). El cuerpo no la contiene; el comentario dice "la dosis maxima es # mg cada # horas segun la norma #". | En `is_boiler`, eliminar solo líneas que se repiten en 2 o más páginas o que son número de página. Las líneas únicas de la franja van al cuerpo, sin enmascarar cifras, y se anotan en el reporte. |
| E2 | Crítico | Volver a ejecutar el extractor sobrescribe `extracted/<nombre>/<nombre>.md` sin aviso: se pierde el trabajo del Paso 3. Además la carpeta depende solo del nombre: `x.pdf` y `x.json` se pisan. La regla "no volver a extraer" de `extractor.md` no la aplica ningún script. | Probado: se agregó una descripción al `.md`, se re-extrajo y desapareció. Luego `guion.json` reemplazó el `.md` de `guion.pdf`. | Guardar un manifiesto (`extracted/<nombre>/fuente.json`: hash SHA-256, fecha, formato). Si existe y el hash coincide, no hacer nada; si el `.md` fue editado, abortar salvo `--forzar`. Si el nombre choca con otro formato, usar `<nombre>-<ext>`. |
| E3 | Crítico | En Word, PowerPoint y Excel la cobertura compara el Markdown contra el texto **que el mismo recorrido recolectó**: lo que el recorrido no visita nunca aparece como faltante. | Probado, todos con reporte sin faltantes: pie de página de Word; párrafo dentro de un control de contenido de Word; imagen insertada en un marcador de posición de PowerPoint (la diapositiva queda vacía); dos renglones de PowerPoint unidos sin espacio ("Usar guantesUsar lentes"). Lectura: cuadros de texto, notas al pie y comentarios de Word; SmartArt e hipervínculos de PowerPoint. | Obtener el texto de referencia por una vía independiente: todos los nodos `w:t` del paquete Word (documento, encabezados, pies, notas) y todos los `a:t` de cada diapositiva. Contar también imágenes del original contra imágenes extraídas. |
| E4 | Alto | Superíndices y subíndices se aplanan y cambian el significado; la cobertura sigue en 100%. | Probado: "10³ m² H₂O nota¹" se extrae como "103 m2 H2O nota1". | Leer el indicador de superíndice del fragmento (bit 0 de `flags`) y el tamaño o la línea base para subíndices; emitir `^{3}` / `_{2}` o caracteres Unicode, y darles soporte en `manual.py` (`<super>`, `<sub>`). |
| E5 | Alto | Word: el texto y la URL de los hipervínculos se pierden (`p.runs` no incluye los fragmentos dentro de `w:hyperlink`); las listas numeradas salen como viñetas; las celdas combinadas se repiten una vez por columna. | Probado: "Consulta la norma vigente antes de empezar" queda "Consulta  antes de empezar."; tres pasos numerados salen con `-`; "Encabezado combinado" aparece 3 veces. | Recorrer `iter_inner_content()` para incluir hipervínculos como `[texto](url)`; detectar el formato de numeración para emitir `1.`; deduplicar celdas combinadas. |
| E6 | Alto | Archivos de texto de Windows: `.txt` o `.csv` en cp1252 (lo que exporta Excel en español) termina en `UnicodeDecodeError`; un CSV de una columna termina en `csv.Error: Could not determine delimiter`; un campo con salto de línea entre comillas se une sin espacio. | Probado los tres. El tercero convierte "linea uno / linea dos" en "linea unolinea dos". | Leer con `utf-8-sig` y, si falla, `cp1252`. Capturar el error del detector y asumir coma. Leer con `csv.reader(io.StringIO(raw, newline=""))` en vez de `splitlines()`. |
| E7 | Alto | El texto en negrita y cursiva a la vez se emite como `***texto***`, que hace fallar al generador (G1). | Probado: extraer y generar termina en error. | Emitir una forma que el generador acepte, y corregir G1. |
| E8 | Medio | Palabras cortadas con guion al final del renglón: la cobertura da faltantes falsos, y la unión elimina guiones reales. | Probado: reporte "85% — faltan: docu mentacion fisico quimico"; "físico-químico" queda "fisicoquimico". | Aplicar la misma unión al texto de referencia antes de comparar. Unir solo si la palabra unida aparece en otra parte del documento; si no, conservar el guion y anotarlo en el reporte. |
| E9 | Medio | Bloques de código: se pierde la sangría cuando el PDF la da por posición, y aparecen líneas en blanco que no existían. | Probado: una función de 4 líneas con 3 niveles de sangría sale sin sangría y con 2 líneas vacías agregadas. | Calcular la sangría con la posición horizontal de cada línea y el ancho de carácter. Unir bloques contiguos sin insertar líneas. |
| E10 | Medio | Imágenes: la transparencia sale con fondo negro; una imagen repetida solo se referencia la primera vez; todo se guarda como PNG. | Probado: PNG con fondo transparente se extrae con píxel de esquina negro; la segunda aparición no queda en el `.md`; en la demo, `flujo.png` pesa 47 KB y su extracción 107 KB. | Usar `doc.extract_image` y aplicar la máscara; repetir la referencia; conservar JPEG cuando el original lo es. |
| E11 | Medio | Enlaces: la puntuación pegada entra al enlace; un enlace con formato no se encuentra y cae a la línea "Enlaces:"; el reemplazo usa la primera coincidencia del texto en la página, que puede ser otra palabra igual. | Probado los dos primeros: `[aqui.](…)` y `Enlaces: [la documentacion,](…)`. La demo tiene `[la documentación de ReportLab.](…)`. Lectura el tercero. | Recortar puntuación final; buscar el texto ignorando marcas de formato; ubicar el enlace por posición, no por la primera coincidencia. |
| E12 | Medio | PowerPoint y Excel: las diapositivas y hojas ocultas se extraen sin marca; Excel pierde el formato de número y las fechas traen hora; no hay límite de filas. | Probado: 15% sale `0.15`; la fecha sale `2026-11-10 00:00:00`; la hoja "Oculta" aparece como una hoja más. Lectura: sin límite de filas. | Marcar `(oculta)`; aplicar el formato de celda para porcentajes y fechas; sobre N filas, extraer encabezado y muestra, e indicarlo en el reporte. |
| E13 | Medio | El reporte nunca llega al estado "terminado" que define `extractor.md`: lista como "pendientes de describir" figuras que ya tienen pie, y marca portada e índice como páginas "que requieren revisión". No hay código de salida. | Verificado en `extracted/ejemplo/reporte.md`: `p4-img47.png` figura como pendiente y el `.md` ya trae su pie. | Separar "informativo" de "pendiente". Listar solo figuras con `FIGURA: describir`. Terminar con código 0 (completo) o 1 (pendientes). |
| E14 | Bajo | Cabecera: el título se toma de metadatos sin valor ("(anonymous)", "Microsoft Word - x.docx"); la `institucion` de la portada no pasa a la cabecera si no tiene etiqueta. | Probado "(anonymous)". En la demo se perdió "MATERIAL DE CLASE". | Descartar títulos de una lista conocida y usar el texto más grande de la portada; tomar como institución la primera línea de la portada. |
| E15 | Bajo | Mensajes: archivo inexistente o PDF protegido terminan en traza de Python. El índice solo se detecta si tiene puntos guía. La estimación de tokens (caracteres / 4) es optimista para español. | Lectura. | Mensajes de una línea; detectar el índice también por los marcadores; dividir por 3,5. |
| E16 | Alto | Código de un PDF con recuadros de letra grande: los renglones que el original partió por ancho quedan como renglones separados (cadenas cortadas a la mitad), se pierde la sangría y el pie de página queda dentro del bloque si está lejos del borde ("Page 95 of 168"). El manual regenerado hereda el código roto. | Reportado por el usuario con dos fragmentos. Reproducido con un PDF de prueba. | **Resuelto.** Sangría por posición; los renglones se reúnen cuando la primera palabra del siguiente no habría cabido en el anterior (el ancho sale del recuadro de fondo o del texto normal); se omite el renglón idéntico, o el contador de páginas, que ocupa la misma posición en la mitad de las páginas o más. El reporte dice cuántos renglones reunió. |
| E17 | Alto | La reunión de renglones de código (corrección de E16) une renglones que eran instrucciones distintas: basta que el anterior pase del 60% del ancho y que la primera «palabra» del siguiente no quepa, y en código esa palabra suele ser larga (`res.status(...).json({`, `SESSION_SECRET=...`). El resultado no funciona al copiarlo: una variable de `.env` queda dentro de un comentario, dos claves YAML en una línea, sentencias de TypeScript detrás de un `//`. Además se pierde la sangría del renglón unido. | Manual_4_Node_React19_MongoDB (12/11/2026): 52 uniones, las 52 falsas; en todas, el renglón siguiente traía su propia sangría en el original. Se deshicieron a mano en `extracted/` y `documentos/`. | **Resuelto (12/11/2026).** Se une solo si, además de no caber, el renglón siguiente empieza en el borde izquierdo y el anterior quedó a medias (comillas o paréntesis sin cerrar, o termina en coma u operador; un comentario nunca cuenta). `reporte.md` lista las uniones y, aparte, los casos dudosos que no se unieron. Con el manual real: 0 uniones y los 52 casos listados como dudosos. Pruebas `test_E16_*` (el caso legítimo sigue uniéndose) y `test_E17_*`. Límite conocido: un renglón partido cuya continuación no vuelve al borde izquierdo, o cuyo comienzo está completo (un comando largo sin comillas), ya no se une solo: queda en la lista de dudosos para unirlo a mano. |
| E18 | Medio | Un símbolo cuya fuente no tiene mapa de caracteres se extrae como carácter NUL (`\x00`) y nadie lo detecta: `extraer.py` informa 100% de cobertura y `validar.py` no lo marca. La herramienta `Write` rechaza un archivo con NUL, así que el subagente `traductor` no puede guardar esa parte. | Manual_4_Node_React19_MongoDB: 12 NUL (11 casillas del checklist de la p.149, 1 símbolo en una tabla de la p.104); en el original se ven como un recuadro vacío (glifo `.notdef`). Se reemplazaron a mano por `[ ]` y `↔`. | **Resuelto en la detección (12/11/2026):** `reporte.md` informa cuántos hay y en qué páginas, y `validar.py` los trata como error (prueba `test_E18_*`). **Pendiente** en `extraer.py`: reemplazar NUL y U+FFFD por una marca visible y anotar la página en `reporte.md`. En `validar.py`: tratar los caracteres de control como error. |

---

## 4. Errores del generador (`manual.py`)

| ID | Sev. | Error | Evidencia | Corrección |
|---|---|---|---|---|
| G1 | Alto | `***texto***` o énfasis cruzado (`**a *b** c*`) genera etiquetas mal anidadas y el programa termina con "Parse error: saw </b> instead of expected </i>", sin indicar la línea del `.md`. | Probado ambos. | Tratar `***x***` antes que `**` y `*`; si las marcas se cruzan, dejar el texto literal. Capturar el error del párrafo e informar la línea de origen. |
| G2 | Alto | Una celda de tabla, un cuadro `> [!NOTA]` o una cita más altos que una página (unos 700 pt) terminan en `LayoutError`. | Probado los tres con unas 1.500 palabras. | Cuadros y citas: una fila por párrafo para que puedan partirse. Tablas: `splitInRow=1`. Si aun así no cabe, avisar con la línea de origen. |
| G3 | Alto | Las listas numeradas siempre empiezan en 1: ítems separados por una línea en blanco salen "1. 1. 1."; una lista interrumpida por código o imagen reinicia; una lista que empieza en 5 sale desde 1. | Probado los tres casos. | Usar el número escrito como inicio y aceptar líneas en blanco entre ítems. |
| G4 | Alto | Los caracteres que no existen en Helvetica, Courier, Symbol o ZapfDingbats salen como ■ sin aviso: subíndices (`H₂O` queda "H■O"), emoji, otros alfabetos. `✓` se ve bien pero no queda como texto buscable. | Probado y revisado en imagen. Sí funcionan: → ≥ ≤ ≠ α β Ω π √ € µ ². | Registrar una fuente TrueType con cobertura amplia (DejaVu Sans) como respaldo, y avisar de los caracteres sin glifo. |
| G5 | Alto | Cuando el índice ocupa más de una página, el pie muestra un capítulo equivocado: `page_chapters` no se limpia entre las pasadas de `multiBuild` y conserva las páginas de la primera. | Probado con 8 capítulos y 56 secciones (36 páginas): las páginas 3 y 4 del índice dicen "1. Capitulo 1"; las páginas 7 y 8, que son del capítulo 1, dicen "2. Capitulo 2". | Vaciar `page_chapters` en `handle_documentBegin`. |
| G6 | Alto | Tablas: `\|` y el código con barra parten la celda en dos; `<br>` se imprime literal. El extractor emite ambos. | Probado: `a \| b` da dos celdas, `a \` y `b`. | Separar columnas solo en barras no escapadas y fuera de código; convertir `<br>` en salto de línea. |
| G7 | Alto | Un `.md` guardado como UTF-8 con BOM (lo que escribe PowerShell 5.1 con `-Encoding utf8`) pierde la cabecera: el título queda "Manual" y la portada sin datos. | Probado. | Leer con `encoding="utf-8-sig"`. |
| G8 | Medio | Fallos sin aviso y con código de salida 0: imagen no encontrada; bloque de código sin cerrar (se traga el resto del documento, títulos incluidos); `FIGURA: describir` impreso como pie; sintaxis no admitida impresa tal cual (`---`, `_cursiva_`, `####`, comentario dentro de un párrafo). El texto que sigue a `-->` en la misma línea se pierde. | Probado cada uno. | Juntar avisos con número de línea, mostrarlos al final y agregar `--estricto` (código 1 si hay avisos). |
| G9 | Medio | Un título que contiene `<algo>` hace fallar la construcción del índice. Un enlace en un título queda crudo en el índice y en los marcadores. | Probado: `# Etiqueta <b>` termina en error; `[enlace](url)` aparece literal en el marcador. | Escapar el texto que va al índice y quitar la sintaxis de enlace. |
| G10 | Medio | Si la carpeta de salida no existe, termina en `FileNotFoundError`; `ejemplo.md` documenta justo ese uso (`-o entregas/manual_final.pdf`). Un `color` inválido da "invalid literal for int()". | Probado ambos. | Crear la carpeta. Validar `color`, `tamano` y `dpi_imagenes` al leer la cabecera. |
| G11 | Medio | Encabezado, pie y portada no recortan textos largos: título y curso se superponen, el capítulo se monta sobre "Página X de Y", el autor se sale de la portada. | Probado y revisado en imagen. | Recortar con "…" según el ancho disponible; en la portada, usar párrafos. |
| G12 | Bajo | Un título de sección queda solo al final de la página cuando lo sigue una figura. | Probado con 22 a 25 párrafos previos. | `keepWithNext` en títulos. |
| G13 | Bajo | Un documento sin capítulos `#` (lo que produce el extractor para PowerPoint y Excel) numera "0.1, 0.2". `fecha:` vacía deja la portada sin fecha en vez de usar la de hoy. | Probado ambos. | No numerar niveles sin padre, o avisar. Tratar el valor vacío como ausente. |
| G14 | Alto | Todos los marcadores y todos los enlaces del índice llevan a la portada. Las páginas se escriben al final (para poder poner "Página X de Y") y el contador de páginas no avanzaba mientras se registraban los destinos. | Verificado en `ejemplo.pdf`: los 21 marcadores apuntaban a la página 1. Encontrado al implementar la fase 2. | **Resuelto.** El contador avanza en cada página diferida y se reinicia al escribir. `ejemplo.pdf` regenerado. |
| G15 | Alto | Recuadros de código: un renglón más largo que el recuadro se cortaba en cualquier letra, a mitad de palabra, y la continuación se confundía con un renglón nuevo. | Reportado por el usuario. | **Resuelto.** Cada renglón ocupa un renglón: primero se reduce la letra del bloque (8,5 → 7 pt, unos 100 caracteres); si aun así no cabe, se parte en un espacio, con sangría mayor y una marca gris dibujada (no es texto: no ensucia al copiar). Un renglón no se separa de su continuación al cambiar de página. |
| G16 | Alto | Tablas: todas las columnas tenían el mismo ancho, así que un comando o un nombre largo en una columna angosta se partía a mitad de palabra (`keycloak-admi` / `n.sh`) aunque sobrara espacio en otra columna. | Manual_4_Node_React19_MongoDB: 26 palabras partidas en 157 páginas. | **Resuelto.** `col_widths`: cada columna recibe al menos el ancho de su palabra más larga (el `código` cuenta entero) y el resto se reparte según el texto de cada una. Pruebas `test_G16_*`. |

---

## 5. Errores del verificador (`tools/comparar.py`)

| ID | Sev. | Error | Evidencia | Corrección |
|---|---|---|---|---|
| C1 | Crítico | Compara **conjuntos** de palabras: ignora cuántas veces aparece cada una, el orden y lo que sobra. | Probado, los tres con "100,0% cubierto": un documento de 3 capítulos contra un PDF con solo el último; "250 mg cada 8 horas" contra "8 mg cada 250 horas"; "1.250 unidades" contra "250.1 unidades" más un párrafo inventado. | Comparar por secciones con conteo de palabras y alineación de secuencia (`difflib`). Tratar las cifras como unidades completas. Informar también lo que sobra. |
| C2 | Alto | Faltantes falsos con la sintaxis de la plantilla: `\salto`, el tipo de un cuadro con título propio y el lenguaje de un bloque de código. El caso C de `generator.md` exige 100% y no puede darlo. Con un PDF de origen, las palabras cortadas con guion también salen como faltantes (Lectura; es la misma comparación de E8). | Probado: 82,4%, "Faltan: importante python salto". En `ejemplo.md` no se nota porque esas palabras aparecen en el texto. | Limpiar el `.md` con las reglas del generador (idealmente, reutilizar su lectura). Unir guiones de corte antes de comparar. |
| C3 | Alto | El código de salida es siempre 0. No hay forma de declarar faltas aceptadas (el índice, un encabezado antiguo) ni de saber dónde falta cada palabra. | Probado. | Código 1 si falta algo no aceptado; `--ignorar "texto"`; mostrar página o sección del origen. |
| C4 | Medio | Si una palabra faltante tiene caracteres fuera de cp1252, el programa falla al imprimirla (`UnicodeEncodeError`). | Probado con "αβγ" en la consola de Windows. | `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` en los tres scripts. |
| C5 | Medio | Solo acepta PDF o texto como origen: un `.docx` termina en `UnicodeDecodeError`. No compara estructura: títulos (solo cuenta marcadores), tablas, imágenes ni enlaces. | Probado el primero. | Aceptar los formatos del extractor. Agregar comparación de la lista de títulos y conteo de tablas, figuras y enlaces. |
| C6 | Alto | `--estricto` contaba como texto sobrante (y como cambio de orden) el encabezado que `manual.py` repite cuando una tabla sigue en otra página: ningún documento con una tabla de más de una página podía terminar en código 0. | Manual_4_Node_React19_MongoDB: unas 60 palabras «sobrantes» que eran encabezados repetidos. | **Resuelto.** Con origen `.md`, se descartan del PDF las apariciones de un encabezado de tabla al inicio de una página que el origen no tiene (`drop_repeated_headers`). Pruebas `test_C6_*`: una fila duplicada de verdad sigue siendo falla. |
| C7 | Medio | Los símbolos que `manual.py` dibuja con ZapfDingbats (`▼`, `▲`) se leen del PDF como letras («M», «L») y aparecían como palabras sobrantes y pares en otro orden. | Manual_4_Node_React19_MongoDB: `m x7 l` en los diagramas dentro de bloques de código. | **Resuelto.** `pdf_lines` no toma el texto de los tramos en fuente Dingbats. Prueba `test_C7_*`. |
| C8 | Medio | Una palabra partida sin guion porque no cabe en su celda (queda en dos o más renglones) se contaba como faltante y sus trozos como sobrantes. E8 solo cubría el corte con guion. | Probado con identificadores de 70 caracteres en una tabla de dos columnas. | **Resuelto.** En el PDF generado los trozos se unen si la palabra completa existe en el origen y algún trozo no (`to_tokens(..., soft=True)`). Prueba `test_C8_*`. |
| C9 | Alto | Con un PDF original como origen, un encabezado formado por dos textos a la misma altura (título a la izquierda, proyecto a la derecha) se contaba como texto faltante en cada página: `pdf_lines` unía los dos textos en un renglón antes de preguntar si era un encabezado repetido, y unido ya no coincidía con lo que `find_boilerplate` había anotado. | Manual_4_Node_React19_MongoDB (16/11/2026, primera ejecución de N4): 1.351 palabras «faltantes» de 37.425; todas eran el encabezado. | **Resuelto.** Se decide con el renglón suelto, igual que el extractor, y un renglón repetido no se une con uno que no lo es. Prueba `test_C9_*`. |
| C10 | Alto | Entre dos PDF, el encabezado de una tabla que sigue en otra página se contaba como falta (el original lo repite donde corta la tabla y el generado la corta en otro lugar) o como sobrante. Además, una cifra del original que queda en la portada generada («Manual 4 de 4») se informaba como «cifra fuera de lugar», que es falla. | Mismo manual: 8 palabras de un encabezado de tabla repetido en la p.66 y 2 cifras de la portada. | **Resuelto.** `repeated_at_page_start` reconoce los renglones con que empieza una página y que repiten, enteros y seguidos, renglones de la anterior; `drop_repeated_headers` quita de cada PDF solo las repeticiones que el otro no tiene. Las vecinas de una cifra también se buscan en la portada generada. Pruebas `test_C10_*` (una fila duplicada de verdad sigue siendo falla). Límite: un renglón perdido que estaba al inicio de una página y era idéntico a otro de la página anterior no se informaría. |

---

## 6. Incompatibilidades entre extractor y generador

Lo que el extractor escribe y el generador no reproduce. Todo probado.

| El extractor emite | El generador hace | Ver |
|---|---|---|
| `***texto***` | Termina con error. | E7, G1 |
| `\|` dentro de una celda (JSON, CSV, Excel, tablas de PDF) | Parte la celda. | G6 |
| `<br>` para saltos dentro de una celda | Lo imprime literal. | G6 |
| Listas anidadas con sangría (JSON, PowerPoint) | Las aplana: se pierde la jerarquía. | — |
| `## Diapositiva N` / `## Hoja: X` sin capítulo | Numera "0.1". | G13 |
| `**Nota**` + párrafo (cuadros del original) | Párrafo suelto: se pierde el cuadro. | D1 |
| Bloque de código y párrafo partidos por `<!-- p.N -->` | Dos bloques, dos párrafos. | D1 |
| `![FIGURA: describir](…)` sin resolver | Imprime "FIGURA: describir" como pie. | G8 |

---

## 7. Documentación y estructura del proyecto

| ID | Sev. | Problema | Corrección |
|---|---|---|---|
| D1 | Alto | El flujo dice `extracted/ --preparar--> documentos/`, pero "preparar" es una lista de 12 ajustes manuales (`generator.md`, sección 4). `documentos/` está vacío y `output/ejemplo_regenerado.pdf` se generó directo desde `extracted/`: perdió los 6 cuadros (quedan como "Consejo" + párrafo), la institución de la portada ("Faltan: clase material") y tiene el bloque de código de la cabecera partido en dos. La demostración no demuestra el flujo documentado. | Crear `tools/preparar.py` (sección 9.1) y rehacer la demo pasando por `documentos/ejemplo/`. |
| D2 | Medio | `README.md` dice que `documentos/` contiene "fuentes `.md` listas para generar"; está vacío. | Corregir junto con D1. |
| D3 | Medio | Las dependencias están en tres lugares y no coinciden. La revisión visual de `generator.md` (sección 8) usa `pypdfium2`, que no está en ninguna lista; además guarda `revision.png` en la raíz y asume 4 páginas o más. | `requirements.txt` único. Reemplazar ese comando por `tools/revisar.py`, con PyMuPDF. |
| D4 | Medio | No es un repositorio git: los `.md` de `documentos/` son "la fuente" y no tienen historial ni forma de deshacer una edición. No hay `.gitignore` (`tools/__pycache__/`). | `git init`; ignorar `__pycache__/` y decidir si `sources/`, `extracted/` y `output/` se versionan. |
| D5 | Medio | No hay pruebas automáticas. Todos los errores de este documento se encontraron con archivos de prueba hechos a mano. | Carpeta `tests/` (sección 9.1). |

---

## 8. Configuración de Claude Code

| ID | Sev. | Problema | Corrección |
|---|---|---|---|
| K1 | Alto | No hay `CLAUDE.md` ni carpeta `.claude/`. Las reglas de oro están en `docs/`, que no se carga sola: cada sesión depende de que Claude decida leer unos 5.000 tokens de guías. | `CLAUDE.md` corto (sección 9.5) y skills (sección 9.2). |
| K2 | Alto | La regla "no usar `sources/` sin permiso explícito" existe solo como una nota de memoria. Nada la aplica, y el primer comando documentado es `extraer.py sources/...`. | Hook y reglas de permiso (sección 9.3, H1). |
| K3 | Medio | `~/.claude/settings.json` (global) tiene en `autoMode.environment` la descripción de **otro** proyecto (CAD/3D en `D:\CAD\Claude-Projects`), que incluye: "routine actions under this repo's project folders (projects/, sources/, tools/) are the expected working scope". En este proyecto eso contradice K2. | Mover ese texto a la configuración de aquel proyecto, o definir el contexto de este en `.claude/settings.json`. |
| K4 | Medio | No hay permisos preaprobados para los comandos del flujo ni skills: cada tarea se arma de memoria. | Secciones 9.2 y 9.5. |

---

## 9. Mejoras que hay que implementar

De esta sección ya existen `tools/preparar.py`, `tools/validar.py`, `tests/`,
`requirements.txt`, `CLAUDE.md` y los hooks H1 y H2 (ver 1.1). El resto es diseño: hay que
probarlo al implementarlo.

### 9.1 Herramientas nuevas

| Herramienta | Qué hace | Resuelve |
|---|---|---|
| `tools/preparar.py` | Copia `extracted/<n>/` a `documentos/<n>/` y aplica los ajustes deterministas: une párrafos y bloques de código partidos por `<!-- p.N -->`; convierte `**Nota**` + párrafo en `> [!NOTA]`; pasa los datos de portada a la cabecera; mueve cada enlace de "Enlaces:" a su frase; agrupa diapositivas en capítulos. Deja en una lista corta lo que requiere criterio. | D1, sección 6 |
| `tools/validar.py` | Revisa un `.md` sin generar el PDF: sintaxis no admitida, énfasis mal cerrado, bloques sin cerrar, imágenes inexistentes, marcas pendientes (`FIGURA: describir`, `TRANSCRIBIR`), caracteres sin glifo, cabecera inválida. Sale con código 0 o 1 y un máximo de 15 líneas. | G1, G4, G8, G10 |
| `tools/revisar.py` | Arma la hoja de revisión visual (portada, índice y las páginas con tablas o figuras) con PyMuPDF, en una carpeta temporal. | D3 |
| `tools/estado.py` | Resume el flujo en unas 10 líneas: extracciones con pendientes, documentos sin PDF, PDF más antiguos que su `.md`. | Hooks H4 y H5 |
| `tests/` | Archivos de prueba generados por script (uno por error de este documento) y la ida y vuelta de `ejemplo.md` como prueba de regresión. | D5 |
| `requirements.txt`, `.gitignore`, `git init` | Dependencias únicas e historial. | D3, D4 |

Cambios en lo que ya existe: correcciones de las secciones 3 a 5; códigos de salida iguales en
todos los scripts (0 correcto; 1 hay faltantes, avisos o pendientes; 2 error); `extraer.py` imprime el resumen del
reporte en la terminal (ahorra una lectura por extracción); manifiesto con hash (E2).

### 9.2 Skills (`.claude/skills/<nombre>/SKILL.md`)

Cada skill debe ser corta (pasos y comandos) y remitir a `docs/` para el detalle.

| Skill | Cuándo | Pasos |
|---|---|---|
| `extraer` | El usuario pide extraer un archivo de `sources/`. **Solo por invocación del usuario** (`disable-model-invocation: true`): escribir `/extraer archivo.pdf` es el permiso explícito para ese archivo. | 1. `extraer.py`. 2. Leer solo el resumen. 3. Resolver pendientes; las figuras van al subagente (9.4). 4. Lista de verificación del Paso 4 de `extractor.md`. |
| `regenerar-manual` | Caso B: regenerar un documento ya extraído. | 1. `preparar.py`. 2. Ajustes de la lista corta. 3. `validar.py`. 4. `manual.py`. 5. `comparar.py`. 6. `revisar.py` y mirar una sola imagen. |
| `nuevo-manual` | Caso A: documento desde cero. | Copiar la estructura de `ejemplo.md`, completar la cabecera, escribir, validar, generar, revisar. |
| `actualizar-manual` | Caso C: cambios en un documento ya generado. | Ediciones puntuales, subir `version`, actualizar `fecha`, validar, generar, comparar contra el `.md`. |
| `verificar-pdf` | Antes de dar un PDF por terminado. | `comparar.py` + `revisar.py` + lista de la sección 8 de `generator.md`. La usan las tres anteriores. |

### 9.3 Hooks (`.claude/settings.json`)

Escribirlos en Python (ya es dependencia y funciona igual en PowerShell y en Bash).

| ID | Evento | Qué hace | Por qué |
|---|---|---|---|
| H1 | `PreToolUse` en `Read`, `Glob`, `Grep`, `Bash`, `PowerShell`, `Edit`, `Write` | Si la ruta o el comando toca `sources/`: **denegar** `Edit` y `Write` (los originales no se modifican); **preguntar** en el resto, mostrando el archivo. | K2. Convierte la regla de memoria en un control real. |
| H2 | `PreToolUse` en `Read` | Denegar la lectura directa de `.pdf`, `.docx`, `.pptx`, `.xlsx` del proyecto, con el mensaje "usa `tools/extraer.py`, `tools/comparar.py` o `tools/revisar.py`". Las imágenes de `assets/` sí se pueden leer. | Regla de oro 1 de `extractor.md`: es el mayor gasto de tokens evitable. |
| H3 | `PostToolUse` en `Edit`, `Write` | Si el archivo es un `.md` de `documentos/` o `extracted/`, ejecutar `validar.py` y devolver los avisos. | Detecta G1, G4, G8 al escribir, no al generar. |
| H4 | `Stop` | Si un `.md` de `documentos/` es más nuevo que su PDF, o la última comparación falló, impedir el cierre con el motivo. Respetar `stop_hook_active` para no entrar en bucle. | "El `.md` es la fuente": evita entregar un PDF desactualizado. |
| H5 | `SessionStart` | Insertar la salida de `estado.py` (unas 10 líneas). | Evita explorar carpetas al comenzar. |
| H6 | `PreToolUse` en `Glob`, `Bash`, `PowerShell`, `Agent` | **Implementado (12/11/2026).** Pide confirmación cuando se llega a `sources/` sin nombrarlo: `Glob` con un patrón que puede entrar (`**/*.pdf`, `s*/*`), listado o búsqueda recursiva desde la raíz (`ls -R`, `Get-ChildItem -Recurse`, `find .`, `tree`, `grep -r`, `rg --no-ignore`), ruta con comodines que alcanza la carpeta y encargo a un subagente que la nombra. | H1 solo miraba el nombre. `Glob` no respeta `.gitignore` (comprobado); `Grep` sí, y una prueba vigila que `sources/` siga ahí. Límite: un script propio que recorra carpetas no se detecta; es una barrera contra descuidos, no un aislamiento. |

Reglas de permiso que acompañan a H1: `deny` para `Edit(./sources/**)` y
`Write(./sources/**)`; `ask` para `Read(./sources/**)`; `allow` para
`python manual.py`, `python tools/*.py` y `python -m pytest`.

### 9.4 Subagentes (`.claude/agents/`)

| Subagente | Tarea | Beneficio |
|---|---|---|
| `describir-figuras` | Recibe la lista de `assets/` pendientes; abre cada imagen; escribe el pie y el comentario `<!-- DESCRIPCIÓN -->` o la tabla de datos del gráfico; transcribe las páginas escaneadas. Devuelve solo un resumen. | Las imágenes son lo más caro en tokens: quedan fuera de la conversación principal. |
| `revisor-visual` | Abre la hoja de `revisar.py` y devuelve una lista de problemas (o "sin observaciones"). | Igual que el anterior. |

### 9.6 Verificar traducciones (T1)

Regla nueva: los manuales de programación, ingeniería, física y matemática se traducen al
inglés (excepción: `Manual_Curso_IA_Python_v2`). `comparar.py` compara palabras, así que
no sirve entre un original en español y un PDF en inglés. Falta una comprobación entre
idiomas: mismos títulos en el mismo orden, misma cantidad de tablas, figuras y enlaces,
bloques de código idénticos y las mismas cifras en el mismo orden. Hasta entonces esa
revisión es manual (`docs/generator.md`, sección 4, paso 5).

### 9.5 `CLAUDE.md` del proyecto

Máximo 40 líneas: propósito y flujo; las reglas de oro (permiso por archivo para
`sources/`; no leer originales directamente; transcribir, no resumir; se edita el `.md`,
nunca el PDF; resultados a archivos, resúmenes a la terminal); los comandos; y enlaces a
`docs/extractor.md` y `docs/generator.md`.

---

## 10. Orden recomendado

| Fase | Contenido | Motivo |
|---|---|---|
| 1. Proteger | `git init`, `.gitignore`, `CLAUDE.md`, H1, H2, reglas de permiso, K3. | Bajo esfuerzo; evita repetir el incidente de `sources/` y da cómo deshacer. |
| 2. Confiar en la verificación | C1, C2, C3, C4, E1, E2, E3 y la base de `tests/`. | Mientras la verificación apruebe pérdidas, ningún "100%" significa nada. |
| 3. Cerrar la ida y vuelta | G1, G6, G7, E7, `validar.py`, `preparar.py`, rehacer la demo (D1, D2). | Hace que `extraer → preparar → generar` funcione sin intervención en el caso simple. |
| 4. Fidelidad | G2, G3, G4, G5, E4, E5, E6, E8 a E12. | Errores de contenido y formato en documentos reales. |
| 5. Automatizar | Skills, H3, H4, H5, subagentes, `estado.py`, `revisar.py`. | Tiene sentido cuando las herramientas ya son confiables. |
| 6. Pulir | G8 a G13, E13 a E15, C5, D3. | Avisos, mensajes y detalles. |

---

## 11. Lo que no se verificó

- `sources/` no se abrió ni se listó. No se comprobó que contenga `ejemplo.pdf`, como dice
  `README.md`, ni cómo se comporta el extractor con los documentos reales.
- PDF escaneados, de dos columnas y con gráficos vectoriales: solo lectura de código.
- Los puntos marcados **Lectura**.
- H1 y H2 se probaron con llamadas simuladas y, el 12/11/2026, en una sesión real
  (sección 12.2). H3 a H5 siguen siendo diseño. Las skills y los subagentes se usaron
  de punta a punta en esa sesión (sección 12).
- E16 (código partido) y la regla del pie lejos del borde: solo con PDF de prueba.

## 12. Lecciones del primer manual real (Manual_4_Node_React19_MongoDB, 12/11/2026)

Primer documento de `sources/` procesado de punta a punta: 151 páginas, ~87.000 tokens,
traducido al inglés, 157 páginas generadas, `comparar.py --estricto` en código 0.

### 12.1 Qué se aprendió

- **Cobertura 100% no significa extracción correcta.** El reporte decía 100% y aun así
  había 52 renglones de código mal unidos (E17), 12 símbolos convertidos en NUL (E18),
  todos los títulos en un solo nivel y un diagrama aplanado como texto. La cobertura
  cuenta palabras; no ve estructura ni código. Ninguno de esos problemas lo detectaba
  una herramienta: los dos primeros se encontraron al investigar otra falla.
  (Después de esa sesión: E17 quedó resuelto y E18 se detecta; ver sección 3.)
- **El modo estricto no se había probado con tablas de más de una página** (C6, C7, C8,
  G16). Las pruebas usan documentos de 3 páginas; los defectos aparecen con 150.
- **La estructura se corrige antes de traducir.** Jerarquía, cuadros y validación en
  español, una sola vez; `capitulos.py` solo parte bien si los capítulos están en `#`.
- **El costo de traducir es sobre todo arranque de subagentes.** 29 lanzamientos de
  `traductor` gastaron ~473.000 tokens para ~87.000 de contenido; cada lanzamiento
  cuesta ~7.000 aunque la parte tenga 40. Pendiente: que `capitulos.py` una las partes
  chicas con su vecina y usar una tanda de ~10.000.
- **La conversación principal también pesa:** cada subagente en segundo plano la
  despierta dos veces (informe y aviso de término), con todo el historial.
- **Scripts en archivo, no `python -c`,** para tocar los `.md` desde PowerShell: las
  comillas invertidas se alteran y la detección de bloques de código falla sin error.
- **Tras reinstalar el sistema:** `pip install -r requirements.txt` trajo PyMuPDF 2.1,
  Pillow 13, reportlab 5.1 y Python 3.14; las pruebas pasan. Git exige
  `safe.directory` porque la carpeta conserva el dueño anterior.

### 12.2 Hooks: verificados en una sesión real

- H1 y H2 funcionan de punta a punta: leer `ejemplo.pdf` con `Read` fue denegado en
  vivo con el mensaje del hook; los cinco comandos de la sesión que nombraban
  `sources/` reciben `ask`, y `Edit`/`Write`/`NotebookEdit` en `sources/` reciben `deny`.
- No se puede ver desde el modelo si cada `ask` se mostró al usuario o lo aprobó el
  modo de permisos: los comandos se ejecutaron.
- Huecos encontrados (el hook no objetaba porque no se nombra `sources`): `Glob` con
  `**/*.pdf` o `**/*` sin ruta, `Get-ChildItem -Recurse` o `ls -R` en la raíz, un comodín
  como `sourc*` y el texto de un encargo a un subagente. Ninguno se usó en la sesión.
  **Cerrados con H6** (sección 9.3) y sus pruebas en `tests/test_hooks.py`. `Grep` sin
  ruta no era un hueco: ripgrep no entra a carpetas de `.gitignore`.
- Efecto práctico de H6: un `Glob` de `**/*.md` desde la raíz ahora pregunta. Para
  evitarlo, acotar a una carpeta (`docs/**/*.md`) o usar `path`.
- H3, H4 y H5 siguen sin implementar. H3 (validar al editar) habría detectado los NUL.

### 12.3 Qué modelo usar

- El trabajo rutinario (ejecutar scripts, lanzar subagentes, leer informes de una línea)
  no necesita el modelo más caro. Con las skills actualizadas, una regeneración normal
  puede ir con Sonnet u Opus en la conversación principal; los subagentes ya usan
  Sonnet (traducción: 99% del tamaño y 5 desvíos menores, todos detectados por script)
  y Haiku (revisión visual: suficiente, con un falso positivo por la baja escala).
- Donde sí pesó la capacidad del modelo fue en depurar herramientas: separar tres
  causas distintas de una misma falla de `comparar.py`, y demostrar con la sangría del
  original que las 52 uniones eran falsas. Eso es desarrollo del flujo, no su uso.
- Los defectos de fondo no los encontró el modelo por ser más capaz sino por una
  salida de diagnóstico; la protección real es que la herramienta los informe (E17,
  E18), no subir de modelo.
- Dato de la sesión: se hizo entera con Fable 5.2 en la conversación principal y el
  límite de uso del plan se alcanzó antes de terminar la retrospectiva. A precio de
  lista de la API (tabla consultada el 12/11/2026, vigente al 03/11/2026), Fable 5.2
  cuesta el doble que Opus 5.5 y cuatro veces lo que Sonnet 5.5 por token.
- Recomendación: modelo intermedio por defecto; subir solo cuando `comparar.py` falle
  por una causa que no esté en este documento o cuando se cambien las herramientas.

## 13. Fases 4, 5 y 6 y errores nuevos (15/11/2026)

Revisión completa del sistema y cierre de lo pendiente. Esta sección reemplaza a la tabla
1.1. Estado al 16/11/2026: 105 pruebas (`python -m unittest discover tests`), todas con
archivos propios, y `ejemplo.pdf` regenerado con `comparar.py --estricto` en código 0.
Los puntos resueltos con prueba llevan su código en el nombre (`test_G5_…`, `test_E11_…`,
`test_N2_…`) o en un comentario de la prueba (E13). G12, N8 y los cambios de
documentación (N5, N6) no tienen una prueba con su código.

### 13.1 Errores nuevos

| ID | Sev. | Error | Estado |
|---|---|---|---|
| N1 | Alto | El pie mostraba un capítulo equivocado en 42 de 156 páginas del manual de Node ya generado. Era G5: `page_chapters` no se vaciaba entre las pasadas de `multiBuild`. | **Resuelto.** Se vacía al comenzar cada pasada. Manual regenerado y verificado. |
| N2 | Alto | Un manual en inglés salía con «Índice», «Página X de Y», rótulos de portada, títulos por defecto de cuadros e idioma del PDF en español. | **Resuelto.** Campo `idioma: es\|en` en la cabecera; una sola tabla de textos (`manual.TEXTOS`) que usan el generador, `comparar.py` y `validar.py`. `comparar_traduccion.py` exige `idioma: en` en la traducción. |
| N3 | Alto | `comparar.py` descartaba encabezado, pie e índice: dio código 0 con N1 y N2. | **Resuelto.** En todo PDF de `manual.py` revisa el capítulo y la numeración del pie, el índice contra los marcadores y el idioma (`check_template`). Con el PDF anterior del manual de Node informa las mismas 42 páginas. |
| N4 | Alto | En un manual traducido nada comparaba el resultado con el original: el paso `extracted/` → `documentos/` en español no lo verificaba ninguna herramienta. | **Resuelto y ejecutado con un original real (16/11/2026).** `/regenerar-manual` genera y compara el PDF en español contra el original antes de traducir. Con el manual de Node (versión en español previa a la traducción, en una carpeta temporal): la primera ejecución falló por tres defectos de `comparar.py` (C9 y C10, sección 5), ninguno una pérdida real. Corregidos, termina en código 0: 36.055 palabras, 0 faltantes, declarando con `--ignorar` el rótulo «PARTE x · CAPÍTULO» que el original pone sobre cada capítulo y que al reestructurar pasó a la numeración. Quedan como aviso 34 palabras sobrantes y 24 pares en otro orden (títulos de parte y diagramas), que en esta comparación no son falla. |
| N5 | Medio | Las guías se contradecían sobre el origen de la verificación. | **Resuelto.** Regla 9 de `CLAUDE.md` y una sola regla en `pipeline.md`, `generator.md` y la skill `verificar-pdf`: el original de `sources/` si es PDF. |
| N6 | Bajo | Cantidad de pruebas desfasada en la documentación. | **Resuelto.** `pipeline.md` dice 99. El «41 pruebas» de la tabla 1.1 es el dato de su fecha. |
| N7 | Bajo | `guardia.py` dejaba pasar la llamada si no podía leerla o fallaba. | **Resuelto.** Pide confirmación. Límite: si Python no está, el hook no corre; quedan las reglas `ask` y `deny` de `settings.json`. |
| N8 | Bajo | Un documento sin títulos imprimía un índice con el texto de relleno de ReportLab. | **Resuelto.** Sin títulos no hay índice. |
| N9 | Alto | `validar.py` da 0 errores y 0 avisos con una tabla que `manual.py` no puede dibujar. Visto el 16/11/2026 en `Manual_1_DotNet10_Vue3_SQLServer_Mediator_Mapperly` (p. 50 del original, sección 8.6): el extractor reconstruyó dos tablas de 3 y 2 columnas como tablas de 15 y 10, casi todas las celdas vacías y el texto de cada celda repartido en varias filas. `manual.py` terminó con `ValueError: … 28 rows x 15 cols … negative availWidth` de ReportLab, sin indicar la línea del `.md`. | **Resuelto (16/11/2026, sección 14):** `preparar.py` rehace sola la tabla, `validar.py` da error con su línea y `manual.py` termina con un mensaje y código 2. Queda (3), en el extractor. Historia: en ese manual se corrigió a mano: se reescribieron las dos tablas con 3 y 2 columnas, sin quitar contenido. Falta: (1) que `validar.py` dé error con la línea de la tabla cuando las columnas no caben en el ancho de la página (en esta, 15 columnas con 6 pt de margen por lado dejan menos de 0 pt por columna) y aviso cuando hay muchas columnas casi vacías; (2) que `manual.py` atrape ese error e informe la línea; (3) revisar por qué el extractor partió esas tablas en columnas de más (no se investigó). |

### 13.2 Generador

| ID | Estado |
|---|---|
| G2 | **Resuelto.** Cuadros y citas van una fila por párrafo; una fila más alta que una página se parte por dentro (`SplitTable`), solo en ese caso. Límite: en un cuadro con título cuyo primer párrafo pasa de ~1.200 caracteres, el título puede quedar solo al final de una página (la regla que lo impide hace que ReportLab no termine si ambos no caben en una página). |
| G3 | **Resuelto.** La lista empieza en el número escrito y admite líneas vacías entre ítems. |
| G4 | **Resuelto.** Fuente de respaldo DejaVu Sans y DejaVu Sans Mono en `fonts/` para lo que Helvetica y Courier no tienen; queda como texto buscable. En código, cada tramo se dibuja en su columna para no desalinear diagramas. Lo que tampoco está en DejaVu (chino, japonés, emoji) sigue como ■, con error en `validar.py` y aviso en `manual.py`. Un símbolo dentro de un título en negrita sale en peso normal. |
| G5 | **Resuelto** (N1). |
| G8 | **Resuelto.** Avisos con línea para imagen inexistente, bloque o comentario sin cerrar, texto tras `-->`, `---`, título de nivel 4 y caracteres sin glifo; `--estricto` termina en 1. |
| G9 | **Resuelto.** Un enlace en un título queda como texto en el marcador y el índice. |
| G10 | **Resuelto.** Crea la carpeta de salida; `color` o `dpi_imagenes` inválidos dan un mensaje y código 2. |
| G11 | **Resuelto.** Título, curso, capítulo y datos de portada se recortan con «…». El título de la portada (16/11/2026): antes subía sin límite, se montaba sobre la institución y lo que pasaba el borde de la página se perdía sin aviso (con 14 repeticiones de una frase quedaban 6). Ahora título y subtítulo se achican hasta la mitad para caber entre la base de la banda y la institución; si ni así caben, se recortan con «…» y hay un aviso, que con `--estricto` termina en 1. Pruebas `test_G11_un_titulo_*`. |
| G12 | **Resuelto.** Un título seguido de una figura pasa junto con ella a la página siguiente. |
| G13 | **Resuelto.** `fecha:` vacía usa la de hoy; una sección sin capítulo sale sin número. |
| G17 | **Resuelto.** Listas anidadas por sangría (2 espacios o más). |

### 13.3 Extractor

| ID | Estado |
|---|---|
| E4 | **Resuelto**, también en tablas con bordes completos (16/11/2026). Superíndices y subíndices pasan a sus caracteres propios (`10³`, `H₂O`); la cobertura los cuenta bien. Lo que no tiene carácter propio queda en línea y se lista en el reporte. Al probar las tablas con bordes apareció un error mayor (**E19**, abajo). |
| E19 | **Nuevo, Alto. Resuelto (16/11/2026).** Una tabla con bordes completos y letra de 10 pt o menos se perdía como tabla: quedaba como un párrafo con todas las celdas seguidas, y el reporte decía «Cobertura 100%; sin observaciones». Causa: `Table.extract()` de PyMuPDF une las palabras cuando el espacio mide menos de 3 pt («sin cambios» → «sincambios»), `clean_table` veía palabras distintas a las de la zona y descartaba la tabla. Además se descartaba si el renglón de arriba rozaba el borde. Ahora el texto de cada celda se lee de sus tramos (`table_rows`, con `cell_md`, igual que en las tablas de líneas horizontales): conserva negrita, cursiva y código, y un renglón que solo roza el borde no cuenta. Cambio visible: un salto de renglón dentro de una celda sale como espacio, no como `<br>`. Prueba `test_E4_tabla_con_bordes_*`. Comprobado con el manual de Node (con permiso del usuario, a una carpeta temporal): el extractor de antes y el de después de esta corrección dan un `.md` idéntico, con 42 tablas y 289 filas, las mismas que la extracción del 12/11/2026. Ese manual no perdió tablas por E19. |
| E5 | **Resuelto.** Hipervínculos de Word con su dirección, listas numeradas con su número y nivel, celdas combinadas una sola vez. |
| E6 | **Resuelto.** Texto y CSV en UTF-8, UTF-16 o cp1252; CSV de una columna; salto dentro de un campo. |
| E8 | **Resuelto.** Un corte con guion se une solo si la palabra unida existe en otra parte del documento; si no, conserva el guion y lo lista. La cobertura usa la misma regla. |
| E10 | **Resuelto.** JPEG tal cual, transparencia conservada, una referencia por cada aparición (salvo una imagen repetida en el 30% de las páginas o más: una sola vez). |
| E11 | **Resuelto.** El enlace va en la aparición que corresponde a su posición, sin la puntuación final y aunque el texto tenga formato. Lo que cae dentro de código en línea sigue yendo a la línea «Enlaces:». |
| E12 | **Resuelto.** Hojas y diapositivas ocultas marcadas `(oculta)`; porcentajes con signo y fechas sin hora; límite de 2.000 filas por hoja o CSV, declarado en el reporte (`--filas 0` = todas). |
| E13 | **Resuelto.** Solo figuran como pendientes las figuras sin pie; lo informativo va aparte; código de salida 0, 1 (con pendientes) o 2. |
| E14 | **Resuelto.** Un título de metadatos sin valor se reemplaza por el texto más grande de la portada (o el nombre del archivo). Desde el 16/11/2026 tampoco pasan a la cabecera un `subtitulo` o `autor` de relleno («(unspecified)», «(anonymous)»). |
| E15 | **Resuelto.** Tokens con caracteres / 3,5; archivo protegido o dañado: mensaje de una línea y código 2. No se cambió la detección del índice sin puntos guía. |
| E18 | **Resuelto.** NUL y U+FFFD quedan como `[SIMBOLO?]`, con su página en el reporte; `validar.py` y `preparar.py` lo tratan como pendiente. |

### 13.4 Verificador, flujo y automatización

| ID | Estado |
|---|---|
| C5 | **Resuelto en lo que importa.** Con un `.md` de origen compara títulos contra marcadores (falla) y cantidad de figuras y enlaces (aviso; falla con `--estricto`). Sigue sin aceptar Word, PowerPoint o Excel como origen: para esos se usa el `.md` de `extracted/`. No cuenta tablas. |
| D3 | **Resuelto.** `tools/revisar.py` reemplaza el comando de una línea. |
| P1 | **Resuelto.** `capitulos.py` junta los capítulos chicos seguidos hasta llenar la tanda. |
| H3, H4, H5 | **Resuelto.** `.claude/hooks/flujo.py` y `tools/estado.py`. H3 se comprobó en una sesión real (devolvió el error con su línea al editar). H5 también, el 16/11/2026: la sesión empezó con el resumen de `estado.py` en el contexto. H4 se probó entregándole la llamada, porque se dispara al cerrar un turno. |
| K3 | Sin cambios: la configuración global no se tocó. |

### 13.5 Lo que no se verificó

- Con archivos de `sources/` se hicieron dos comprobaciones (16/11/2026, con permiso), las
  dos con el manual de Node y en una carpeta temporal: contar tablas con el extractor
  corregido (E19) y comparar el PDF en español contra el original (N4, código 0). La
  extracción de `extracted/`, anterior a estos cambios, sigue vigente y no se rehízo.
- N4 solo se probó con ese original. Otro PDF puede traer un encabezado o un pie que
  `comparar.py` todavía no reconozca; la señal es la misma: la misma frase «faltante» en
  casi todas las páginas.
- La skill `verificar-pdf` preaprueba `tools/revisar.py output/*` desde el 16/11/2026
  (autorizado por el usuario); no se comprobó en una sesión real que deje de pedir confirmación.
- La revisión visual del manual regenerado (dos hojas, 7 páginas) no dio observaciones;
  es una muestra a baja escala, no una revisión de las 157 páginas.
- H4 (impedir el cierre con un PDF desactualizado) no se vio actuar en una sesión real.

## 14. Segundo manual de la serie (Manual_2_DotNet10_React19_SQLServer_Mediator_Mapperly, 16/11/2026)

176 páginas, ~112.000 tokens. Regenerado en español y comparado con el original (100%,
código 0), traducido al inglés (180 páginas, 130 marcadores), `comparar_traduccion.py`
correcto y `comparar.py --estricto` en código 0. Revisión visual: dos hojas y un
acercamiento a dos páginas, sin observaciones al final.

### 14.1 Lo que la conversión dejaba mal y nadie avisaba

La cobertura era 100% y `validar.py` daba 0 errores con todo esto dentro. El manual 1
(mismo diseño) se entregó con casi todos estos defectos; el manual 4, con los de código.

| ID | Qué pasaba | Estado |
|---|---|---|
| N9 | Tabla reconstruida con 15 columnas (casi todas vacías): `manual.py` terminaba en una traza de ReportLab. | **Resuelto.** `preparar.py` la rehace (columnas donde el encabezado tiene texto; filas vacías como separación); `validar.py` da error con la línea si no cabe y aviso si casi todo está vacío; `manual.py` da mensaje y código 2; ninguna columna queda con menos ancho que su relleno. |
| N10 | Tabla que sigue en otra página: el encabezado repetido quedaba como un párrafo de negritas y la primera fila de datos, como encabezado de una tabla nueva. A veces con una columna vacía de más y la fila partida en dos. | **Resuelto** en `preparar.py`. Si entre la tabla y el cambio de página quedó la última fila como párrafo (sin celdas), une lo demás y lo deja como pendiente: esa fila se arma a mano. |
| N11 | 22 de 48 cuadros no se armaban: el rótulo venía en el mismo párrafo (`**NOTA** texto`), o era `SEGURIDAD` o `¿POR QUÉ?`. | **Resuelto** en `preparar.py`. Los dos últimos solo valen en mayúsculas; «**Seguridad**» sigue quedando como pendiente. |
| N12 | Palabras que el original corta al final del renglón («cancellationTo» / «ken») contaban dos veces en `comparar.py`: los trozos como faltantes y la palabra entera como sobrante. Lo mismo cuando el corte lo hace el PDF generado, o los dos en puntos distintos. | **Resuelto.** `comparar.py` las cuenta enteras y las lista en un aviso. Solo une dos palabras seguidas que están de más en su lado y que juntas forman una que está de más en el otro. |
| N13 | El rótulo de cada recuadro de código (`API/Program.cs`, `TERMINAL`) quedaba como primera línea del código; 86 rótulos «… archivo» de cambio de página quedaban **en medio** del código; 57 recuadros distintos quedaban pegados en un mismo bloque. Quien copia el código se lleva esas líneas. También pasa en el manual 4 (71 y 40). | **Resuelto** con `tools/rotulos_codigo.py` y el título de bloque (```` ```API/Program.cs ````) que `manual.py` dibuja en una franja. `comparar.py` no cuenta como falta el «… rótulo» que el original repite. El manual 4 no se rehízo. |
| N14 | En una tabla con código largo, las palabras normales de las otras columnas se partían («component» / «es»). | **Resuelto** en `manual.py`: primero el ancho de la palabra más larga de cada columna; el resto se reparte de menor a mayor, así un código corto queda entero y solo el más largo se parte. |
| N15 | Un bloque de código de tres páginas o más quedaba en dos bloques. | **Resuelto** en `preparar.py` (y `rotulos_codigo.py` une los que ya estaban preparados). |
| N16 | Código en línea partido por el renglón: `` `dotnet` `sln` `` y, peor, `` `SqlServe` `r` ``. 50 casos. | **Resuelto** en `preparar.py`: los une; sin espacio solo si la palabra unida existe entera en el documento y algún trozo no existe suelto. |

### 14.2 Pendiente en el extractor (se corrigió a mano en este manual)

Son cinco, todos del mismo diseño de origen; el manual 3 los va a traer:

| ID | Qué pasa | Qué hacer |
|---|---|---|
| E20 | Todos los títulos en `###` y los capítulos como «PARTE I · CAPÍTULO 1 Título». Si el título ocupa dos renglones, queda fundido con el párrafo (`**PARTE II · CAPÍTULO 6** **Título** texto`). El PDF tiene 130 marcadores con su nivel, pero el título de la página no coincide con el del marcador y no se usa. | En `extraer.py`, comparar cada bloque con los marcadores de **su página** por el final del texto, y tomar del marcador el nivel y el título. Mientras tanto: script sobre `documentos/` (partes y capítulos en `#`, secciones en `##`) y `--ignorar "PARTE I · CAPÍTULO"` al comparar. |
| E21 | Las páginas de índice no se reconocen: los puntos guía vienen de a uno (`**.** **.**`) y `LEADER` no los ve. Quedan en el cuerpo, parte como tablas. | Detectar la página también por la proporción de renglones que son solo «.» o por los marcadores. |
| E22 | 11 renglones de código cortados por el ancho de la página no se unen: la continuación trae 4 espacios más de sangría que el renglón cortado, y la regla exige que empiece en el borde. Están en la lista de dudosos del reporte, entre 93 que no son cortes. | Unir cuando el renglón siguiente no habría cabido **y** su sangría es la del anterior más un valor fijo que se repite en todo el documento. |
| E23 | La última fila de una tabla antes del cambio de página queda fuera de la tabla, como párrafo sin celdas. Una celda angosta parte un identificador y el extractor le pone un espacio («Op enIdConnect»). | Revisar el borde inferior en `ruled_tables`; para el identificador, la misma regla de N16 dentro de las celdas. |
| E24 | Un recuadro con texto en letra de código y dibujo de flechas (un diagrama de flujo) sale como tabla de una celda con todos los renglones en línea. | Tratarlo como bloque de código. En este manual se rehízo con las posiciones leídas del original. |

### 14.3 Costo de traducir, medido

- 14 partes con `--tanda 10000`. 13 fueron a `traductor` (Sonnet): ~445.000 tokens de
  subagente en total, entre 29.000 y 41.000 por parte, y cerca de un minuto cada una
  (tres a la vez: unos 6 minutos en total). La parte de 864 tokens se tradujo en la
  conversación principal con reemplazos exactos.
- Desvíos: 6 marcadores dentro de código en línea traducidos (`<proyecto>` → `<project>`),
  todos detectados por `comparar_traduccion.py` y devueltos con un script. Tamaño 99%.
- El glosario salió del manual 4, ya traducido, y se pasó a todas las partes desde el
  principio: no hizo falta esperar la primera.
- Traducir no es lo caro de este flujo: lo caro fue depurar la conversión. Dejar un manual
  técnico en español por costo no se justifica con estos números (regla 2 de `CLAUDE.md`).

### 14.4 Lo que no se verificó

- **El manual 1 sigue en español** y con los defectos N10, N11, N13 y N16 y el diagrama
  de la sección 3.1 aplanado. No se tocó: no era el encargo.
- El manual 4 conserva N13 (rótulos dentro del código).
- La revisión visual vio 9 páginas de 180.
- `rotulos_codigo.py --todos` se usó porque en este manual todo bloque empieza con un
  rótulo; un caso (dos recuadros pegados sin línea vacía entre ellos) se separó a mano.
- La traducción no se leyó entera: se comprobó la estructura, no la calidad de cada frase.

### 14.5 Verificación de la conversión y herramientas nuevas (17/11/2026)

| Qué | Estado |
|---|---|
| Avisos de conversión de `validar.py` (`conversion()`): rótulo en la primera línea del código, «… rótulo» en medio, código en línea partido, puntos guía, fila vacía, cuadro sin armar, encabezado de tabla suelto, título fundido, todos los títulos en un nivel. Solo con `fuente:` en la cabecera. | **Resuelto**, con prueba por aviso (`AvisosDeConversion`) y otra de que un documento sin `fuente:` no recibe ninguno. |
| Regla 8 de `CLAUDE.md`: `validar.py` con 0 errores y 0 avisos es obligatorio en **todo** documento, no solo en los extraídos (decisión del usuario). | **Resuelto** en `CLAUDE.md`, `pipeline.md`, `generator.md` y las skills `actualizar-manual` y `verificar-pdf`. |
| E24, en parte: `extraer.py` (`diagram_like`) reconoce tres o más cajas unidas por conectores con rótulos cortos, guarda `p<N>-diagrama<M>.png` y lo lista en «## Diagramas con texto». | **Resuelto solo para cajas y flechas dibujadas**, con prueba (`Diagramas`). El recuadro con letra de código y flechas que sale como tabla de una celda **sigue pendiente**. |
| `tools/region.py`: renglones de una franja con su columna, o recorte `.png`, sin abrir el PDF en la conversación. | **Resuelto**, con prueba de los dos modos y del código 2. No se agregó a `allowed-tools` de ninguna skill ni a los comandos de `CLAUDE.md` (decisión del usuario). |
| `rotulos_codigo.py`: dos recuadros pegados sin línea vacía se separan si un «… X» más abajo confirma que «X» es un rótulo (el caso que en 14.4 se separó a mano). | **Resuelto**, con prueba. Tampoco va en `allowed-tools` (decisión del usuario). |
| Coherencia: toda opción `--algo` citada en skills, subagentes, `CLAUDE.md`, `README.md`, `pipeline.md`, `extractor.md` y `generator.md` existe en su script. | **Resuelto**, con prueba (`Coherencia`). |
| Regla 10 de `CLAUDE.md`: lo que pisaría trabajo hecho se hace en temporales que se borran al terminar; lo hecho queda en `docs/registro.md`. | **Resuelto** (decisión del usuario). |
| Manual 4: N13 y N16 (172 rótulos al título del bloque, 30 códigos en línea unidos), títulos de bloque traducidos, dos celdas git. | **Resuelto**: validar 0/0, `comparar --estricto` código 0. |
| Manual 1: rehecho como el manual 2 y traducido al inglés (detalle en `docs/registro.md`). | **Resuelto**: validar 0/0, `comparar --estricto` código 0. **No verificado contra el original** (permiso denegado): se comparó con `extracted/`; el diagrama 3.1 y la disposición del flujo 8.1 se tomaron del manual 2 (mismas palabras). |

Pruebas al 17/11/2026: 134, todas OK.
