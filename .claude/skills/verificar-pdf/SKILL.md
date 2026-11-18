---
name: verificar-pdf
description: Verifica un PDF generado antes de darlo por terminado (contenido contra su origen y revisión visual mínima). Usar al final de cualquier generación de manual.
argument-hint: <nombre>
effort: low
allowed-tools:
  - Bash(python tools/comparar.py documentos/*)
  - Bash(python tools/comparar.py extracted/*)
  - PowerShell(python tools/comparar.py documentos/*)
  - PowerShell(python tools/comparar.py extracted/*)
  - Bash(python tools/revisar.py output/*)
  - PowerShell(python tools/revisar.py output/*)
---

# Verificar `output/$ARGUMENTS/$ARGUMENTS.pdf`

Un PDF no está terminado hasta que `comparar.py` termina con código 0.

## 1. Contenido

El contenido sale de `sources/` (regla 9): un manual regenerado se compara con su original.

| Caso | Comando |
|---|---|
| Regenerado, original en PDF | `python tools/comparar.py "sources/<archivo>" output/$ARGUMENTS/$ARGUMENTS.pdf` |
| Regenerado, original en otro formato | `python tools/comparar.py extracted/$ARGUMENTS/$ARGUMENTS.md output/$ARGUMENTS/$ARGUMENTS.pdf` |
| Nuevo, actualizado o traducido | `python tools/comparar.py documentos/$ARGUMENTS/$ARGUMENTS.md output/$ARGUMENTS/$ARGUMENTS.pdf --estricto` |

- `<archivo>` está en `extracted/$ARGUMENTS/fuente.json`. Es el original del manual: se
  usa como fuente y no se modifica (regla 1). Lo lee el script, no la conversación. Si no
  está en la raíz de `sources/`, buscarlo por ese nombre (puede estar en una subcarpeta).
- Contra el original, leer la falla antes de tocar el `.md`:
  - La misma frase en casi todas las páginas: es un encabezado o pie del original que
    `comparar.py` no reconoció. No es una pérdida; es un defecto de la herramienta
    (`docs/auditoria.md`, C9): avisar al usuario.
  - Un rótulo que el original pone sobre cada título y que al reestructurar pasó a la
    numeración («PARTE II · CAPÍTULO 5»): se declara con `--ignorar "PARTE II · CAPÍTULO"`,
    una vez por variante.
  - `Aviso: sobran` y pares en otro orden por títulos reordenados o diagramas: no son falla
    aquí (esta comparación no lleva `--estricto`).
- Un manual traducido ya se comparó con su original en español, antes de traducir
  (skill `regenerar-manual`); aquí se compara con su `.md` en inglés.
- `Faltan`, `Cifras`, `Portada`, `Estructura`: corregir el `.md`, regenerar, repetir.
- `Plantilla` (pie, índice o idioma): si es el idioma, falta `idioma: en` en la cabecera;
  si es el pie o el índice, es un error de `manual.py`: avisar al usuario.
- `Aviso: sobran`: aceptable solo si es texto agregado a propósito (pies de figura,
  tablas de datos, las tablas de un diagrama). Decirlo en el informe.
- `Aviso: N palabras cortadas al final de un renglón…`: informativo. Son identificadores
  que uno de los dos PDF parte donde se le acaba el ancho; se contaron enteros.
- `comparar.py` en código 0 dice que están las palabras, no que la conversión esté bien:
  la estructura la revisa `tools/validar.py`, que es obligatorio en todo documento: sin
  0 errores y 0 avisos el PDF no está terminado (regla 8; skill `regenerar-manual`, paso 3).
- Una falta aceptada se declara con `--ignorar "texto"`; no se calla.

## 2. Vista (dos imágenes como máximo)

```
python tools/revisar.py output/$ARGUMENTS/$ARGUMENTS.pdf
```

Crea `output/$ARGUMENTS/revision.png` (portada, índice, primera y última página) y, si hay tablas,
figuras o código largo, `output/$ARGUMENTS/revision2.png` con esas páginas. Imprime qué página es
cada una. Pasar las dos rutas al subagente `revisor-visual`, con esa lista de páginas, el
idioma del manual y la aclaración de que el texto en español dentro de bloques de código
es intencional. No abrir las imágenes en esta conversación.

A 58 dpi no se distingue la alineación de un diagrama: si el revisor marca una página,
verla de cerca con `python tools/revisar.py output/$ARGUMENTS/$ARGUMENTS.pdf --paginas N --dpi 110`
y volver a pasarla.

## 3. Informe

Tres líneas: resultado de `comparar.py`, observaciones del revisor, peso del PDF.

## Presupuesto

- Nunca leer el PDF ni revisar página por página.
- Máximo dos imágenes por verificación.
