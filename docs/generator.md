# Generador: cómo construir o regenerar un documento

Este documento define **cómo crear un documento nuevo o regenerar uno existente** con la
plantilla `manual.py`, a partir de un archivo Markdown.

Principio central: **el `.md` es la fuente; el PDF es un resultado.** Los cambios se hacen
siempre en el `.md` y se vuelve a generar. Nunca se edita el PDF.

---

## 1. Tres casos

| Caso | Punto de partida | Ir a |
|---|---|---|
| **A. Documento nuevo** | Ideas, apuntes o información suelta (de una o varias fuentes). | Sección 3 |
| **B. Regenerar un documento existente** | Un archivo en `sources/` (PDF, Word, PowerPoint, JSON...). | Sección 4 |
| **C. Actualizar un documento ya generado** | Un `.md` en `documentos/` que ya produjo un PDF. | Sección 5 |

---

## 2. Carpetas y comando

```
documentos/<nombre>/<nombre>.md     fuente lista para generar (se edita aquí)
documentos/<nombre>/imagenes/       imágenes que usa ese documento
output/<nombre>.pdf                 resultado
```

```
python manual.py documentos/<nombre>/<nombre>.md -o output/<nombre>.pdf
```

La terminal muestra la ruta y el peso del PDF. Requisitos: `pip install -r requirements.txt`.

---

## 3. Caso A: documento nuevo

1. Copiar la estructura de `ejemplo.md` (cabecera + capítulos) a `documentos/<nombre>/<nombre>.md`.
2. Completar la cabecera (sección 6).
3. Ordenar el contenido en capítulos (`#`), secciones (`##`) y subsecciones (`###`).
   Cada capítulo empieza en página nueva, así que conviene que tengan un tamaño parecido.
4. Si la información viene de archivos, **extraerla primero** con
   [extractor.md](extractor.md) y copiar desde `extracted/`, no desde el original.
5. Escribir el archivo completo de una sola vez (no por partes) y generar.
6. Verificar (sección 7).

---

## 4. Caso B: regenerar un documento existente

### Paso 1: extraer

Seguir [extractor.md](extractor.md) hasta completar su Paso 4 (100% verificado).

### Paso 2: copiar a `documentos/`

```
documentos/<nombre>/<nombre>.md      copia de extracted/<nombre>/<nombre>.md
documentos/<nombre>/assets/          copia de extracted/<nombre>/assets/
```

`extracted/` queda como registro fiel del original; los ajustes se hacen en la copia.

### Paso 3: preparar el `.md` (lista de ajustes)

Hacer solo los ajustes que correspondan, con ediciones puntuales:

| En el `.md` extraído | Ajuste |
|---|---|
| `<!-- p.1 PORTADA ORIGINAL: ... -->` | Pasar los datos que falten a la cabecera: `institucion`, `subtitulo`, `curso`, `version`, `fecha`. Dejar el comentario. |
| `<!-- p.2 ÍNDICE ORIGINAL: ... -->` | Nada: el índice se regenera solo. Sirve para comprobar que estén todos los títulos. |
| `<!-- ENCABEZADOS/PIES ... -->` y `<!-- p.N -->` | Nada: no se imprimen. |
| Títulos ya numerados (`# 1. Introducción`) | Dejar `numerar: no`. O bien quitar los números y poner `numerar: si`. No mezclar. |
| Párrafo cortado entre `<!-- p.N -->` | Unir las dos partes en un solo párrafo. |
| Dos bloques de código seguidos (cortados por página) | Unirlos en uno. |
| Filas de tabla como párrafos sueltos (reporte: "posible tabla sin reconstruir") | Convertirlas en tabla Markdown. |
| `**Nota**` (o Consejo, Advertencia, Importante, Ejercicio) seguido de un párrafo | Convertir en cuadro: `> [!NOTA]` + `> texto`. Con título propio: `> [!IMPORTANTE] Antes de entregar`. |
| `![pie](assets/...)` | Dejar la ruta (es relativa al `.md`). Revisar que el pie sea corto. |
| `<!-- DESCRIPCIÓN: ... -->` o `<!-- DATOS DEL GRÁFICO: ... -->` | Dejar. Si los datos aportan al lector, agregarlos también como tabla visible. |
| `Enlaces: [texto](url)` al final de una página | Mover cada enlace a su frase. |
| Diapositivas (`## Diapositiva N: ...`) | Agrupar diapositivas en capítulos con `#`; las viñetas pasan a párrafos o listas. Las notas del orador pasan a párrafos o a `> [!NOTA]`. |
| Hojas de Excel / JSON | Dejar tablas cortas; para tablas largas, conservar solo las columnas necesarias e indicarlo, o dividir en varias tablas con un subtítulo cada una. |

### Paso 4: generar y verificar

```
python manual.py documentos/<nombre>/<nombre>.md -o output/<nombre>.pdf
python tools/comparar.py sources/<original>.pdf output/<nombre>.pdf
```

`comparar.py` termina con `RESULTADO: CORRECTO` (código 0) o `RESULTADO: FALLA` (código 1).
Cuenta repeticiones, no solo palabras distintas, e informa:

| Línea del resultado | Significa | Qué hacer |
|---|---|---|
| `Faltan` | Texto del origen que no está en el PDF, con su página o línea. | Corregir el `.md` y regenerar. |
| `Cifras con otras palabras alrededor` | Una cifra está, pero en otro lugar. | Revisar esa frase: puede ser un dato cambiado. |
| `Portada: faltan` | Datos de la portada original que no llegaron. | Pasarlos a la cabecera. |
| `Aviso: sobran` | Texto del PDF que no está en el origen. | Normal si se agregó un pie de figura o una tabla de datos; si no, quitarlo. |
| `Aviso: ... pares de palabras` | Orden o contexto distinto. | Normal en tablas de celdas largas; revisar si es mucho. |

Las únicas faltas aceptables son textos que se reemplazan a propósito. Se declaran, no se
ignoran en silencio:

```
python tools/comparar.py ORIGEN.pdf output/X.pdf --ignorar "Encabezado antiguo" --ignorar-paginas 2
```

`--ignorar-paginas` sirve para un índice del original que el extractor no reconoció.

### Paso 5: traducir (solo manuales técnicos)

Los manuales de programación, ingeniería, física y matemática se trabajan en inglés
(regla 2 de `CLAUDE.md`; excepción: `Manual_Curso_IA_Python_v2`).

1. Traducir `documentos/<nombre>/<nombre>.md` completo, por secciones, sin resumir.
2. No tocar: bloques de código, comandos, nombres de archivos, fórmulas, cifras ni rutas
   de imágenes.
3. Generar y verificar contra el `.md` traducido (caso C, con `--estricto`).
4. `comparar.py` no puede comparar el PDF en inglés con el original en español: compara
   palabras. La fidelidad de la traducción se revisa con `extracted/` al lado: mismos
   títulos, mismas tablas, mismo código y mismas cifras.

---

## 5. Caso C: actualizar un documento ya generado

1. Editar solo las partes que cambian en `documentos/<nombre>/<nombre>.md` (ediciones
   puntuales; no reescribir el archivo entero).
2. Subir `version` (1.0 → 1.1 para correcciones, 2.0 para cambios grandes) y actualizar
   `fecha` (o borrarla para usar la de hoy).
3. Generar con el mismo comando.
4. Verificar con el `.md` como origen:

```
python tools/comparar.py documentos/<nombre>/<nombre>.md output/<nombre>.pdf
```

Debe terminar en `RESULTADO: CORRECTO`. Con `--estricto`, tampoco puede sobrar texto ni
cambiar el orden:

```
python tools/comparar.py documentos/<nombre>/<nombre>.md output/<nombre>.pdf --estricto
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
| `fuente` | nombre de archivo | Lo agrega el extractor; no afecta el PDF. |

---

## 7. Sintaxis disponible

| Elemento | Escribir |
|---|---|
| Capítulo / sección / subsección | `#` / `##` / `###` |
| Negrita, cursiva, código, enlace | `**texto**`, `*texto*`, `` `texto` ``, `[texto](https://...)` |
| Lista con viñetas / numerada | `- ítem` / `1. ítem` |
| Tabla | `\| A \| B \|` + `\|---\|---\|` + filas |
| Código | bloque entre ```` ``` ````. Cada renglón queda entero: si no cabe, se reduce la letra del bloque (hasta 7 pt, unos 100 caracteres); si aun así no cabe, se parte en un espacio y la continuación lleva una marca gris. |
| Cuadro destacado | `> [!NOTA]`, `[!CONSEJO]`, `[!ADVERTENCIA]`, `[!IMPORTANTE]`, `[!EJERCICIO]` (+ título opcional) |
| Cita simple | `> texto` |
| Imagen con pie | `![pie de figura](ruta/imagen.png)` en una línea sola |
| Salto de página | `\salto` en una línea sola |
| Comentario (no se imprime) | `<!-- texto -->` |

No se admiten listas anidadas, celdas combinadas ni notas al pie: convertirlas en listas
simples, filas repetidas o un párrafo "Notas" al final de la sección.

---

## 8. Verificación final

- [ ] `manual.py` terminó sin errores y el peso es razonable (texto: decenas de KB; con imágenes, según `dpi_imagenes`).
- [ ] `comparar.py` termina en `RESULTADO: CORRECTO` (código 0).
- [ ] Revisión visual **mínima**: renderizar solo la portada, el índice y 1-2 páginas con tablas o
      figuras, varias por imagen y a escala baja. No revisar todas las páginas una por una.

```
python -c "import pymupdf,tempfile,os; s=pymupdf.open('output/X.pdf'); n=min(4,len(s)); r=s[0].rect; \
o=pymupdf.open(); p=o.new_page(width=r.width*n,height=r.height); \
[p.show_pdf_page(pymupdf.Rect(i*r.width,0,(i+1)*r.width,r.height),s,i) for i in range(n)]; \
f=os.path.join(tempfile.gettempdir(),'revision.png'); p.get_pixmap(dpi=58).save(f); print(f)"
```

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
| Tildes o ñ con símbolos raros | Guardar el `.md` en UTF-8. |
| `[Imagen no encontrada: ...]` en el PDF | La ruta es relativa al `.md`; revisar mayúsculas y carpeta. |
| Números dobles en títulos ("1. 1. Introducción") | Títulos ya numerados con `numerar: si`: usar `numerar: no` o quitar los números. |
| PDF muy pesado | Bajar `dpi_imagenes` o recortar imágenes. |
| Tabla muy angosta o cortada | Demasiadas columnas: dividirla en dos tablas o abreviar encabezados. |
| Un cuadro `> [!NOTA]` sale como cita gris | El tipo está mal escrito o falta `!`. |
