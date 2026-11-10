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

La terminal muestra la ruta y el peso del PDF. Requisitos: `pip install reportlab pillow`.

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

`comparar.py` muestra páginas y marcadores (antes → después) y las palabras del original
que faltan en el PDF nuevo. Las únicas faltas aceptables son textos que se reemplazan a
propósito (por ejemplo, el índice o un encabezado antiguo). Cualquier otra falta se corrige
en el `.md` y se vuelve a generar.

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

Debe dar 100% cubierto.

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
| Código | bloque entre ```` ``` ```` |
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
- [ ] `comparar.py` sin faltas inesperadas.
- [ ] Revisión visual **mínima**: renderizar solo la portada, el índice y 1-2 páginas con tablas o
      figuras, varias por imagen y a escala baja. No revisar todas las páginas una por una.

```
python -c "import pypdfium2 as p; from PIL import Image; d=p.PdfDocument('output/X.pdf'); \
ims=[d[i].render(scale=0.8).to_pil() for i in (0,1,2,3)]; w,h=ims[0].size; \
s=Image.new('RGB',(w*4,h),'white'); [s.paste(im,(i*w,0)) for i,im in enumerate(ims)]; s.save('revision.png')"
```

- [ ] El índice tiene todos los títulos y los marcadores funcionan.

---

## 9. Ahorro de tokens al generar

- Partir siempre desde `extracted/` o `documentos/`, nunca desde el original.
- Para cambios, usar ediciones puntuales sobre el `.md`; no reescribir el archivo completo.
- Verificar con `comparar.py` (unas pocas líneas) en vez de leer el PDF generado.
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
