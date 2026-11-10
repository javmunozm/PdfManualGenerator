# Auditoría del sistema: errores encontrados y mejoras pendientes

Fecha: 10/11/2026. Alcance: `manual.py`, `tools/extraer.py`, `tools/comparar.py`,
`docs/`, `README.md`, la demostración incluida y la configuración de Claude Code.

Este documento **no cambia nada**: registra lo que falla y lo que falta implementar.

---

## 1. Resumen

| Componente | Crítico | Alto | Medio | Bajo |
|---|---|---|---|---|
| Extractor (`tools/extraer.py`) | 3 | 4 | 6 | 2 |
| Generador (`manual.py`) | 0 | 7 | 4 | 2 |
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

---

## 5. Errores del verificador (`tools/comparar.py`)

| ID | Sev. | Error | Evidencia | Corrección |
|---|---|---|---|---|
| C1 | Crítico | Compara **conjuntos** de palabras: ignora cuántas veces aparece cada una, el orden y lo que sobra. | Probado, los tres con "100,0% cubierto": un documento de 3 capítulos contra un PDF con solo el último; "250 mg cada 8 horas" contra "8 mg cada 250 horas"; "1.250 unidades" contra "250.1 unidades" más un párrafo inventado. | Comparar por secciones con conteo de palabras y alineación de secuencia (`difflib`). Tratar las cifras como unidades completas. Informar también lo que sobra. |
| C2 | Alto | Faltantes falsos con la sintaxis de la plantilla: `\salto`, el tipo de un cuadro con título propio y el lenguaje de un bloque de código. El caso C de `generator.md` exige 100% y no puede darlo. Con un PDF de origen, las palabras cortadas con guion también salen como faltantes (Lectura; es la misma comparación de E8). | Probado: 82,4%, "Faltan: importante python salto". En `ejemplo.md` no se nota porque esas palabras aparecen en el texto. | Limpiar el `.md` con las reglas del generador (idealmente, reutilizar su lectura). Unir guiones de corte antes de comparar. |
| C3 | Alto | El código de salida es siempre 0. No hay forma de declarar faltas aceptadas (el índice, un encabezado antiguo) ni de saber dónde falta cada palabra. | Probado. | Código 1 si falta algo no aceptado; `--ignorar "texto"`; mostrar página o sección del origen. |
| C4 | Medio | Si una palabra faltante tiene caracteres fuera de cp1252, el programa falla al imprimirla (`UnicodeEncodeError`). | Probado con "αβγ" en la consola de Windows. | `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` en los tres scripts. |
| C5 | Medio | Solo acepta PDF o texto como origen: un `.docx` termina en `UnicodeDecodeError`. No compara estructura: títulos (solo cuenta marcadores), tablas, imágenes ni enlaces. | Probado el primero. | Aceptar los formatos del extractor. Agregar comparación de la lista de títulos y conteo de tablas, figuras y enlaces. |

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

Nada de esta sección existe todavía. Los hooks y las skills son diseño: hay que probarlos
al implementarlos.

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

Reglas de permiso que acompañan a H1: `deny` para `Edit(./sources/**)` y
`Write(./sources/**)`; `ask` para `Read(./sources/**)`; `allow` para
`python manual.py`, `python tools/*.py` y `python -m pytest`.

### 9.4 Subagentes (`.claude/agents/`)

| Subagente | Tarea | Beneficio |
|---|---|---|
| `describir-figuras` | Recibe la lista de `assets/` pendientes; abre cada imagen; escribe el pie y el comentario `<!-- DESCRIPCIÓN -->` o la tabla de datos del gráfico; transcribe las páginas escaneadas. Devuelve solo un resumen. | Las imágenes son lo más caro en tokens: quedan fuera de la conversación principal. |
| `revisor-visual` | Abre la hoja de `revisar.py` y devuelve una lista de problemas (o "sin observaciones"). | Igual que el anterior. |

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
- Los hooks, skills y subagentes de la sección 9 son diseño, no se probaron.
