# Generador: cómo construir o regenerar un documento

Este documento define **cómo crear un documento nuevo o regenerar uno existente** con la
plantilla `manual.py`, a partir de un archivo Markdown.

Principio central: **el `.md` es la fuente; el PDF es un resultado.** Los cambios se hacen
siempre en el `.md` y se vuelve a generar. Nunca se edita el PDF.

---

## 1. Tres casos

| Caso | Punto de partida | Ir a |
|---|---|---|
| **A. Documento nuevo** | No hay archivo en `sources/`: el contenido se investiga en la web según lo que el lector necesita aprender. | Sección 3 |
| **B. Regenerar un documento existente** | Un archivo en `sources/` (PDF, Word, PowerPoint, JSON...). | Sección 4 |
| **C. Actualizar un documento ya generado** | Un `.md` en `documentos/` que ya produjo un PDF. | Sección 5 |

---

## 2. Carpetas y comando

```
documentos/<nombre>/<nombre>.md     fuente lista para generar (se edita aquí)
documentos/<nombre>/imagenes/       imágenes que usa ese documento
output/<nombre>/<nombre>.pdf                 resultado
```

```
python manual.py documentos/<nombre>/<nombre>.md -o output/<nombre>/<nombre>.pdf
```

La terminal muestra la ruta y el peso del PDF, y un «Aviso l.N» por cada cosa que se
imprimió tal cual o no se imprimió (imagen que no existe, bloque de código sin cerrar,
texto después de `-->`, carácter sin glifo). En la portada, un título o subtítulo largo
se imprime con letra más chica (hasta la mitad) para que quepa en la banda; si ni así
cabe, se recorta con «…» y hay un «Aviso portada». Con `--estricto` esos avisos terminan en
código 1. Código 2: no se generó (cabecera inválida, archivo inexistente, o una tabla con
más columnas de las que caben: el mensaje dice la línea). Crea la carpeta
de salida si no existe. Requisitos: `pip install -r requirements.txt` y la carpeta `fonts/`.

---

## 3. Caso A: documento nuevo

El contenido de un manual sale de `sources/` (caso B). Cuando no hay un archivo de
origen, se investiga en la web y no se escribe de memoria:

- Definir primero **el lector** (el usuario u otra persona), su nivel de partida y qué
  necesita saber o poder hacer al terminar.
- Buscar por capítulo, en fuentes primarias (documentación oficial, normas, el autor
  original), y comprobar que versiones, cifras y fechas estén vigentes.
- Anotar cada dato con su URL y la fecha de consulta en
  `documentos/<nombre>/investigacion.md`. El manual se redacta desde esas notas, con
  palabras propias, y termina con un capítulo de referencias con los enlaces usados.
- Lo que no se pudo confirmar se informa; no se rellena.

Después:

1. Copiar la estructura de `ejemplo.md` (cabecera + capítulos) a `documentos/<nombre>/<nombre>.md`.
   Antes de generar, pasar `python tools/validar.py` sobre el archivo.
2. Completar la cabecera (sección 6).
3. Ordenar el contenido en capítulos (`#`), secciones (`##`) y subsecciones (`###`).
   Cada capítulo empieza en página nueva, así que conviene que tengan un tamaño parecido.
4. Si la información viene de archivos, **extraerla primero** con
   [extractor.md](extractor.md) y copiar desde `extracted/`, no desde el original.
5. Un documento corto se escribe de una vez; uno largo, por capítulos (uno por mensaje:
   si una respuesta larga se corta, se pierde todo). Después, generar.
6. Verificar (sección 7).

---

## 4. Caso B: regenerar un documento existente

### Paso 1: extraer

Seguir [extractor.md](extractor.md) hasta completar su Paso 4 (100% verificado).

### Paso 2: preparar

```
python tools/preparar.py extracted/<nombre>
```

Crea `documentos/<nombre>/<nombre>.md` y copia `assets/`. `extracted/` queda como registro
fiel del original; los ajustes se hacen en la copia. Si el documento ya existe no lo
reemplaza (es la fuente del PDF); con `--forzar` lo rehace y guarda el anterior como
`<nombre>.anterior.md`.

`preparar.py` hace solo lo que no requiere criterio y termina con una lista corta de
pendientes (código 1) o sin pendientes (código 0):

| En el `.md` extraído | Quién lo ajusta |
|---|---|
| Párrafo, lista, bloque de código o tabla partidos por `<!-- p.N -->` | **Automático.** Los une; el marcador queda después. Una tabla solo se une si repite el mismo encabezado; si no, queda como pendiente. |
| Tabla que sigue en otra página con el encabezado repetido como párrafo de negritas (`**A** **B**`) | **Automático.** Une las dos partes. Si la última fila antes del cambio de página quedó como párrafo debajo de la tabla, queda como pendiente: pasarla a celdas. |
| Tabla con columnas y filas vacías de más (el texto de una celda repartido en varias) | **Automático.** La rehace: una columna por cada encabezado con texto; las filas vacías separan las filas reales. |
| `**NOTA** texto` en un mismo párrafo; `**SEGURIDAD**`, `**¿POR QUÉ?**` (en mayúsculas) | **Automático.** Cuadro `> [!NOTA]`, `> [!ADVERTENCIA] SEGURIDAD`, `> [!NOTA] ¿POR QUÉ?`. |
| Código en línea partido por el renglón (`` `dotnet` `sln` ``, `` `SqlServe` `r` ``) | **Automático.** Lo une; sin espacio solo si la palabra unida existe entera en el documento. |
| Rótulo de un recuadro de código como primera línea del código (`API/Program.cs`, `TERMINAL`), «… rótulo» en medio del código, dos recuadros en un bloque | `tools/rotulos_codigo.py` (primero `--ver`). No lo hace `preparar.py`: hay que mirar la lista antes de decidir si todo bloque empieza con un rótulo (`--todos`). |
| `**Nota**`, `**Consejo**`, `**Advertencia**`, `**Importante**`, `**Ejercicio 1**` (o en inglés: Note, Tip, Warning, Important, Exercise) seguido de un párrafo | **Automático.** Cuadro `> [!NOTA]`; si el rótulo no es el nombre del tipo, queda como título (`> [!ADVERTENCIA] Warning`). Solo toma el párrafo siguiente. |
| Otro rótulo en negrita solo en su línea (`**Antes de entregar**`) | **Pendiente.** No se puede saber el tipo: escribir `> [!IMPORTANTE] Antes de entregar` y el texto con `> `. |
| `<!-- p.1 PORTADA ORIGINAL: ... -->` | **Automático** para `institucion` (lo primero de la portada) y `subtitulo` (lo que sigue al título). Lo que no pudo ubicar queda como pendiente. El comentario se conserva. |
| `[texto.](url)` con la puntuación dentro | **Automático.** Queda `[texto](url).` |
| `Enlaces: [texto](url)` al final de una página | **Automático** si el texto aparece una sola vez en esa página. Si no, pendiente. |
| Documento sin ningún capítulo `#` (PowerPoint, Excel) | **Automático.** Agrega `# <titulo>` para que la numeración no empiece en 0.1. Agrupar las diapositivas en capítulos reales es **manual**. |
| `![FIGURA: describir](...)`, `TRANSCRIBIR` | **Pendiente.** Se resuelve en `extracted/` (extractor.md, paso 3) y se prepara de nuevo con `--forzar`. |

### Paso 3: ajustes a mano y validación

Con ediciones puntuales sobre `documentos/<nombre>/<nombre>.md`:

| En el `.md` | Ajuste |
|---|---|
| Lo que `preparar.py` dejó como pendiente | Resolverlo. |
| `<!-- p.2 ÍNDICE ORIGINAL: ... -->`, `<!-- ENCABEZADOS/PIES ... -->`, `<!-- p.N -->` | Nada: no se imprimen. El índice se regenera solo. |
| El índice del original dentro del cuerpo (renglones con `. . . .`; `validar.py` lo avisa) | El extractor no reconoció esas páginas: pasar cada una a un comentario `<!-- p.N ÍNDICE ORIGINAL: ... -->`. |
| Todos los títulos en un mismo nivel, o un título fundido con su párrafo (`validar.py` lo avisa) | Partes y capítulos en `#`, secciones en `##`, con un script y contando contra los marcadores del original. |
| Un diagrama o un recuadro de texto aplanado (negritas sueltas sin frases; flechas dentro de una celda) | `tools/region.py` sobre el original: modo `imagen` para `describir-figuras` (tablas de componentes y de conexiones), modo `texto` para rehacer un bloque de código con su sangría. |
| Títulos ya numerados (`# 1. Introducción`) | Dejar `numerar: no`. O bien quitar los números y poner `numerar: si`. No mezclar. |
| Filas de tabla como párrafos sueltos (reporte: "posible tabla sin reconstruir") | Convertirlas en tabla Markdown. |
| Un párrafo todo en cursiva que en el original era una cita | Escribirlo como `> texto`. |
| `![pie](assets/...)` | Dejar la ruta (es relativa al `.md`). Revisar que el pie sea corto. |
| `<!-- DESCRIPCIÓN: ... -->` o `<!-- DATOS DEL GRÁFICO: ... -->` | Dejar. Si los datos aportan al lector, agregarlos también como tabla visible. |
| Diapositivas (`## Diapositiva N: ...`) | Agrupar en capítulos con `#`; las viñetas pasan a párrafos o listas. Las notas del orador pasan a párrafos o a `> [!NOTA]`. |
| Hojas de Excel / JSON | Dejar tablas cortas; para tablas largas, conservar solo las columnas necesarias e indicarlo, o dividir en varias tablas con un subtítulo cada una. |

Después, antes de generar:

```
python tools/validar.py documentos/<nombre>/<nombre>.md
```

Revisa el `.md` sin generar el PDF y muestra, con número de línea:

- **error** (código 1): se perdería contenido o quedaría trabajo sin terminar. Imagen
  inexistente, figura sin describir, bloque de código o comentario sin cerrar, texto
  después de `-->`, caracteres que saldrían como ■ (los que no están ni en la fuente normal
  ni en `fonts/`), símbolos sin identificar (`[SIMBOLO?]`), `color` o `dpi_imagenes` inválidos.
- **aviso** (código 0; con `--estricto`, 1): sintaxis que no se admite y se imprimiría tal
  cual. Títulos de nivel 4, negrita mal cerrada, guion bajo, etiquetas HTML, enlaces
  internos, líneas `---`, `idioma` desconocido.
- **error**, también: una tabla con más columnas de las que caben en la página.
- **aviso de conversión**, solo en un documento que viene de una extracción (cabecera con
  `fuente:`): rótulo de recuadro como primera línea del código o «… rótulo» en medio,
  código en línea partido en dos, rótulo de un cuadro sin armar, encabezado de tabla
  suelto, fila de tabla vacía, tabla con casi todas las celdas vacías, renglón de índice
  con puntos guía, título fundido con su párrafo, todos los títulos en un mismo nivel.

Ningún PDF está terminado hasta que `validar.py` da **0 errores y 0 avisos**, sea
nuevo, extraído, traducido o actualizado (regla 8 de `CLAUDE.md`).
La cobertura de `extraer.py` y el resultado de `comparar.py` cuentan palabras: dan 100%
y correcto con todos esos defectos dentro (así se entregaron dos manuales). Se valida
después de preparar y otra vez después de traducir.

Al editar el `.md` de un documento, un hook ejecuta esta misma revisión y devuelve los
errores en el momento (ver `docs/pipeline.md`, sección 6).

### Paso 4: generar y verificar

```
python manual.py documentos/<nombre>/<nombre>.md -o output/<nombre>/<nombre>.pdf
python tools/comparar.py sources/<original>.pdf output/<nombre>/<nombre>.pdf
```

El contenido sale de `sources/`, así que un manual regenerado se compara con su original.
Si el original es un PDF, el origen es ese archivo (lo lee el script, no entra a la
conversación; es el que el usuario autorizó con `/extraer`, y el hook pide confirmación).
Si es de otro formato, el origen es `extracted/<nombre>/<nombre>.md`.

`comparar.py` termina con `RESULTADO: CORRECTO` (código 0) o `RESULTADO: FALLA` (código 1).
Cuenta repeticiones, no solo palabras distintas, e informa:

| Línea del resultado | Significa | Qué hacer |
|---|---|---|
| `Faltan` | Texto del origen que no está en el PDF, con su página o línea. | Corregir el `.md` y regenerar. |
| `Cifras con otras palabras alrededor` | Una cifra está, pero en otro lugar. | Revisar esa frase: puede ser un dato cambiado. |
| `Portada: faltan` | Datos de la portada original que no llegaron. | Pasarlos a la cabecera. |
| `Plantilla: pie de página` | El pie muestra otro capítulo o una numeración incorrecta. | Es un error de `manual.py`, no del `.md`: informarlo. |
| `Plantilla: índice` | El índice no coincide con los marcadores. | Igual que el anterior. |
| `Plantilla: idioma` | El `.md` declara un idioma y el pie o el índice están en otro. | Poner `idioma: en` (o `es`) en la cabecera y regenerar. |
| `Estructura: títulos` | Los títulos del `.md` no son los marcadores del PDF. | Revisar el título que nombra: suele estar dentro de un cuadro o mal escrito. |
| `Aviso: figuras` / `Aviso: enlaces` | Distinta cantidad de figuras o de direcciones. | Revisar la imagen o el enlace que falta. Con `--estricto` es falla. |
| `Aviso: sobran` | Texto del PDF que no está en el origen. | Normal si se agregó un pie de figura o una tabla de datos; si no, quitarlo. |
| `Aviso: ... pares de palabras` | Orden o contexto distinto. | Normal en tablas de celdas largas; revisar si es mucho. |
| `Aviso: N palabras cortadas al final de un renglón` | Identificadores que uno de los dos PDF parte donde se le acaba el ancho («cancellationTo» / «ken»). Se contaron enteros. | Nada: es informativo. |

Las únicas faltas aceptables son textos que se reemplazan a propósito. Se declaran, no se
ignoran en silencio:

```
python tools/comparar.py ORIGEN.pdf output/X/X.pdf --ignorar "Encabezado antiguo" --ignorar-paginas 2
```

`--ignorar-paginas` sirve para un índice del original que el extractor no reconoció.

### Paso 5: traducir (solo manuales técnicos)

Los manuales de programación, ingeniería, física y matemática se trabajan en inglés
(regla 2 de `CLAUDE.md`; excepción: `Manual_Curso_IA_Python_v2`).

1. **Antes de traducir**, generar el PDF en español y compararlo con el original (paso 4).
   `comparar.py` compara palabras: después de traducir ya no puede hacerlo. Así cada
   tramo queda verificado: original → PDF en español (palabras), español → inglés
   (estructura), `.md` en inglés → PDF final (palabras).
2. Traducir `documentos/<nombre>/<nombre>.md` completo, por partes, sin resumir
   (`tools/capitulos.py` y el subagente `traductor`; skill `/traducir-manual`).
3. No tocar: bloques de código, comandos, nombres de archivos, fórmulas, cifras ni rutas
   de imágenes. La cabecera debe quedar con `idioma: en`.
4. `python tools/comparar_traduccion.py <nombre>.anterior.md <nombre>.md` hasta
   `RESULTADO: CORRECTO`: mismos títulos, tablas, código, enlaces y cifras.
5. Generar y verificar contra el `.md` traducido (caso C, con `--estricto`).

---

## 5. Caso C: actualizar un documento ya generado

1. Editar solo las partes que cambian en `documentos/<nombre>/<nombre>.md` (ediciones
   puntuales; no reescribir el archivo entero).
2. Subir `version` (1.0 → 1.1 para correcciones, 2.0 para cambios grandes) y actualizar
   `fecha` (o borrarla para usar la de hoy).
3. Validar (`tools/validar.py`: 0 errores y 0 avisos) y generar con el mismo comando.
4. Verificar con el `.md` como origen:

```
python tools/comparar.py documentos/<nombre>/<nombre>.md output/<nombre>/<nombre>.pdf
```

Debe terminar en `RESULTADO: CORRECTO`. Con `--estricto`, tampoco puede sobrar texto ni
cambiar el orden:

```
python tools/comparar.py documentos/<nombre>/<nombre>.md output/<nombre>/<nombre>.pdf --estricto
```

---

## 6. Cabecera del `.md` (datos del documento)

```
---
titulo: Manual de Laboratorio
subtitulo: Química General
autor: Nombre Apellido
curso: QUI-101
institucion: Facultad de Ciencias
version: 1.0
fecha: 10/11/2026
color: #1F4E79
tamano: A4
indice: si
numerar: si
logo: imagenes/logo.png
palabras_clave: química, laboratorio
dpi_imagenes: 150
idioma: es
---
```

| Campo | Valores | Efecto |
|---|---|---|
| `titulo`, `subtitulo` | texto | Portada, encabezado y metadatos del PDF. |
| `autor`, `curso`, `institucion`, `version`, `fecha` | texto | Portada (y `curso` en el encabezado). Sin `fecha`, se usa la de hoy. |
| `color` | hex, ej. `#7B2C2C` | Portada, títulos, tablas, viñetas y pie. |
| `tamano` | `A4` / `carta` | Tamaño de página. |
| `indice` | `si` / `no` | Índice automático con números de página. |
| `numerar` | `si` / `no` | Numeración automática de títulos (1, 1.1, 1.1.1). |
| `logo` | ruta relativa al `.md` | Logo en la portada. |
| `palabras_clave` | texto | Metadatos del PDF (búsqueda). |
| `dpi_imagenes` | número (110-300) | Resolución máxima de imágenes: 110 para correo, 150 normal, 300 imprenta. |
| `idioma` | `es` / `en` | Idioma de los textos que pone la plantilla: «Índice» / «Contents», «Página X de Y» / «Page X of Y», rótulos de la portada y título por defecto de los cuadros («Nota» / «Note»). No traduce el contenido. Un manual en inglés lleva `idioma: en`. |
| `fuente` | nombre de archivo | Lo agrega el extractor; no afecta el PDF. |

---

## 7. Sintaxis disponible

| Elemento | Escribir |
|---|---|
| Capítulo / sección / subsección | `#` / `##` / `###` |
| Negrita, cursiva, código, enlace | `**texto**`, `*texto*`, `` `texto` ``, `[texto](https://...)` |
| Lista con viñetas / numerada | `- ítem` / `1. ítem`. La numerada empieza en el número escrito (`5.` sigue en 6, 7). Puede haber líneas vacías entre ítems. |
| Lista dentro de otra | El ítem hijo lleva 2 espacios o más de sangría que su padre. |
| Tabla | `\| A \| B \|` + `\|---\|---\|` + filas. Sin código (`` ` ``) en el encabezado: sale como un recuadro blanco sobre el color. Con 3 columnas o más, celdas cortas: el texto largo va en una lista debajo de la tabla. |
| Código | bloque entre ```` ``` ````. Cada renglón queda entero: si no cabe, se reduce la letra del bloque (hasta 7 pt, unos 100 caracteres); si aun así no cabe, se parte en un espacio y la continuación lleva una marca gris. |
| Código con título | ```API/Program.cs en la línea que abre el bloque: el título sale en una franja arriba del recuadro y no es parte del código. Una palabra corta en minúsculas (```python, ```bash) es el lenguaje y se ignora. Al traducir, el título se traduce si es texto («Raíz del proyecto»), no si es un nombre de archivo. |
| Cuadro destacado | `> [!NOTA]`, `[!CONSEJO]`, `[!ADVERTENCIA]`, `[!IMPORTANTE]`, `[!EJERCICIO]` (+ título opcional). Los renglones de un párrafo del cuadro se unen: una lista se escribe con un renglón `>` vacío entre ítems y cada ítem empieza con `•` (`> • texto`). |
| Cita simple | `> texto` |
| Imagen con pie | `![pie de figura](ruta/imagen.png)` en una línea sola |
| Salto de página | `\salto` en una línea sola. **Nunca antes de un `#`**: cada capítulo ya empieza página y el salto deja una en blanco. |
| Comentario (no se imprime) | `<!-- texto -->` |

No se admiten celdas combinadas ni notas al pie: convertirlas en filas repetidas o en un
párrafo "Notas" al final de la sección.

Símbolos: lo que no está en la fuente normal (subíndices y superíndices como H₂O o x²,
flechas, griego, casillas ☐ ✓, cirílico, líneas de caja para diagramas) se escribe con
DejaVu Sans, que viene en `fonts/`, y queda como texto que se puede buscar y copiar. Lo
que tampoco está ahí (chino, japonés, emoji) sale como ■: `validar.py` lo marca como error.

Un cuadro, una cita o una celda más altos que una página siguen en la página siguiente.

---

## 8. Verificación final

- [ ] `validar.py` no muestra errores ni avisos.
- [ ] `manual.py` terminó sin errores ni avisos y el peso es razonable (texto: decenas de KB; con imágenes, según `dpi_imagenes`).
- [ ] `comparar.py` termina en `RESULTADO: CORRECTO` (código 0).
- [ ] Revisión visual **mínima**: la portada, el índice y las páginas con tablas, figuras
      o código largo, varias por imagen y a escala baja. No revisar todas las páginas.

```
python tools/revisar.py output/X/X.pdf                        # revision.png y revision2.png
python tools/revisar.py output/X/X.pdf --paginas 12 --dpi 110  # una página de cerca
```

El script dice qué página es cada una. Las imágenes las mira el subagente `revisor-visual`.

- [ ] `revisar.py` dice «Sin páginas vacías». El muestreo de seis páginas no ve un defecto
      que se repite (21 páginas en blanco pasaron una revisión «sin observaciones»).
- [ ] Una sección nueva o cambiada se mira entera: ubicar sus páginas buscando su texto con
      PyMuPDF y pasarlas con `--paginas` (hasta 4 por imagen, dos imágenes; 80 dpi para ver
      la disposición, 110 para leer código). Incluir siempre una página con cuadro y una
      con tabla.
- [ ] El índice tiene todos los títulos y los marcadores funcionan.

---

## 9. Ahorro de tokens al generar

- Partir siempre desde `extracted/` o `documentos/`, nunca desde el original.
- Para cambios, usar ediciones puntuales sobre el `.md`; no reescribir el archivo completo.
- Verificar con `comparar.py` (unas pocas líneas y un código de salida) en vez de leer el PDF generado.
- Para la revisión visual, una sola imagen con varias páginas a escala baja.
- No imprimir el contenido del PDF en la terminal.

---

## 10. Problemas frecuentes

| Problema | Solución |
|---|---|
| Un título no aparece en el índice | Falta el espacio después de `#`, o el título está dentro de un cuadro o de una tabla. |
| Tildes o ñ con símbolos raros | Guardar el `.md` en UTF-8 (con o sin BOM). |
| Un carácter sale como ■ | No existe ni en la fuente normal ni en `fonts/` (chino, japonés, emoji), o falta la carpeta `fonts/`. `validar.py` los lista: reemplazarlos por texto. |
| El índice dice «Índice» en un manual en inglés | Falta `idioma: en` en la cabecera. `comparar.py` lo informa como `Plantilla: idioma`. |
| Una lista numerada no sigue la numeración | Empieza en el número escrito en su primer ítem; revisar ese número. |
| Asteriscos impresos (`**a *b** c*`) | Negrita y cursiva cruzadas: cerrar una antes de abrir la otra. `***texto***` sí funciona. |
| Una barra parte la celda de una tabla | Escribirla como `\|` o dentro de `` `código` ``. Para un salto de renglón dentro de la celda: `<br>`. |
| «No se generó: l.N: la tabla tiene N columnas…» | La tabla no cabe a lo ancho (en A4, 14 columnas). Casi siempre es una tabla mal reconstruida al extraer: `preparar.py` la rehace; si el documento ya está preparado, rehacerla a mano con sus columnas reales. `validar.py` la marca con su línea. |
| "Aviso l.N" al generar | Lo que indica esa línea se imprimió tal cual o no se imprimió: corregirlo en el `.md`. Con `--estricto`, código 1. |
| `[Imagen no encontrada: ...]` en el PDF | La ruta es relativa al `.md`; revisar mayúsculas y carpeta. |
| Números dobles en títulos ("1. 1. Introducción") | Títulos ya numerados con `numerar: si`: usar `numerar: no` o quitar los números. |
| PDF muy pesado | Bajar `dpi_imagenes` o recortar imágenes. |
| Páginas en blanco al final de cada capítulo | Un `\salto` antes de `#`: quitarlo. `validar.py` lo avisa y `revisar.py` lista las páginas casi vacías. |
| Las viñetas de un cuadro salen en un solo párrafo, con los guiones a la vista | Separar los ítems con un renglón `>` vacío y empezar cada uno con `•`. `validar.py` lo avisa. |
| Celda de encabezado de tabla en blanco sobre el color | Tiene código (`` ` ``): quitar las comillas invertidas. `validar.py` lo avisa. |
| Una columna de tabla sale con una palabra por renglón | Demasiado texto en una tabla de 3 columnas o más: dejar en la tabla datos cortos y pasar las explicaciones a una lista debajo. |
| Negrita alrededor de código (`` **`x`** ``) da «negrita mal cerrada» | Escribir solo el código, o la negrita sobre otras palabras. |
| Tabla muy angosta o cortada | Demasiadas columnas: dividirla en dos tablas o abreviar encabezados. |
| Un cuadro `> [!NOTA]` sale como cita gris | El tipo está mal escrito o falta `!`. |

---

## 11. Manual nuevo sin origen: lecciones

Lo aprendido al escribir el manual MongoDB (skill `nuevo-manual`, 18/11/2026). El detalle
de lo que falló está en `docs/auditoria.md`, sección 15.

### Investigación

- **Verificar todo lo verificable.** Un dato que el lector va a usar (sintaxis, campos,
  valores por defecto, opciones) no se entrega «sin verificar» si existe la página que lo
  dice. Si un detalle no está en ninguna página (por ejemplo, el formato exacto de una
  cadena de conexión), el texto lo dice y remite a la fuente; no se inventa.
- **Páginas armadas con JavaScript** (learn.mongodb.com y similares): WebFetch solo recibe
  el título. Probar la variante `.md` de la página de documentación (`<url>.md`, que además
  muestra los ejemplos que la página esconde en pestañas), la referencia de la API en su
  versión exacta, o fuentes secundarias que citen la oficial. En `investigacion.md`, marcar
  cuáles son secundarias.
- **Vigencia.** Anotar la fecha de consulta y buscar si hubo cambios en el año en curso
  (temario, versión, API). Un informe de «está vigente» dice en qué fuentes se apoya y qué
  no se pudo leer.
- **Fuentes que no coinciden.** La principal manda en el cuerpo del manual. Lo que solo
  dice otra fuente va en un apéndice («más allá del temario»), como seguro, **escrito para
  el lenguaje o contexto del manual**: si la fuente muestra Python y Node.js y el manual es
  de C#, el apéndice va en C#.

### Redacción

- Palabras, ejemplos y datos de muestra propios: no reutilizar los conjuntos de ejemplo de
  la documentación cambiando un par de valores.
- Un manual largo se escribe por partes en `documentos/<n>/partes/NN.md`, una por mensaje,
  y se une en `<n>.md`. Desde ahí el `.md` es la fuente y las partes se borran.
- Un script que reescribe el `.md` en Windows abre el archivo con `newline=""` (si no,
  duplica los fines de línea) y se prueba en una copia del scratchpad mirando el `diff`
  antes de instalarlo. Para un cambio puntual, `Edit`; no `sed` por número de línea.

### Formato (lo avisa `validar.py`)

- `\salto` nunca antes de `#`: cada capítulo ya empieza página.
- Lista dentro de un cuadro: `> • ítem`, con un renglón `>` vacío entre ítems.
- Sin código en el encabezado de una tabla; sin negrita alrededor de código.
- Tablas de 3 columnas o más con celdas cortas; las explicaciones, en una lista debajo
  (esto no lo avisa: lo ve la revisión de cerca).

### Manual de preparación de un examen o certificación

- Partir del temario oficial (objetivos y pesos) y citar el código de cada objetivo en la
  teoría y en las preguntas, para que el lector vea sus puntos débiles.
- Por capítulo: teoría con la sintaxis del examen y la del lenguaje del manual lado a lado,
  y al final un cuadro «Trampas del examen» («Exam traps»).
- Además: glosario, ejercicios paso a paso con la explicación de por qué sale cada
  resultado, exámenes de práctica, resumen para la víspera y referencias.
- Las preguntas son **originales**: nunca las reales del examen (son confidenciales) ni las
  de los cuestionarios de cursos o insignias. La clave da la respuesta y explica **cada**
  opción. Cada respuesta se comprueba contra los datos de la pregunta, documento por
  documento.
- Decir al lector qué datos del examen no publica la entidad (cantidad de preguntas, nota
  de aprobación) y que los compare con la guía oficial al inscribirse.

### Revisión visual

- El muestreo de seis páginas no ve un defecto que se repite: `revisar.py` debe decir «Sin
  páginas vacías», y las secciones nuevas se miran enteras con `--paginas`, ubicadas
  buscando su texto en el PDF (sección 8).
