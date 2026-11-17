---
name: regenerar-manual
description: Regenera el PDF de un documento que ya está en extracted/ (preparar, resolver pendientes, validar, generar, verificar). Usar cuando se pide regenerar, rehacer o dar formato a un manual extraído.
argument-hint: <nombre>
effort: medium
allowed-tools:
  - Bash(python tools/costo.py *)
  - Bash(python tools/preparar.py *)
  - Bash(python tools/validar.py *)
  - Bash(python manual.py *)
  - PowerShell(python tools/costo.py *)
  - PowerShell(python tools/preparar.py *)
  - PowerShell(python tools/validar.py *)
  - PowerShell(python manual.py *)
---

# Regenerar `$ARGUMENTS`

Requiere `extracted/$ARGUMENTS/` sin pendientes. Si no existe, pedir al usuario que
ejecute `/extraer <archivo>` (esa skill es la que autoriza usar `sources/`).

## Pasos

1. `python tools/costo.py $ARGUMENTS` y seguir su plan por tandas.
2. `python tools/preparar.py extracted/$ARGUMENTS`
   - Si dice que el documento ya existe, seguir con ese. No usar `--forzar` sin preguntar.
3. Estructura, **antes de traducir y antes de generar**. La cobertura cuenta palabras:
   da 100%, y `comparar.py` da correcto, con el código lleno de rótulos, tablas partidas
   y cuadros sin armar. Lo que sí los ve es el validador:
   `python tools/validar.py documentos/$ARGUMENTS/$ARGUMENTS.md --max 400`
   Dejarlo en **0 errores y 0 avisos**. No leer la salida renglón por renglón: agruparla
   por tipo de aviso y resolver cada tipo de una vez, con su herramienta o con un script.

   | Aviso o pendiente | Qué hacer |
   |---|---|
   | «los N títulos están en un mismo nivel», «título fundido con su párrafo» | Script: partes y capítulos en `#`, secciones en `##`, con los títulos tal como están en el índice original. Contar `#` y `##` contra «Marcadores del PDF» de `reporte.md`. `capitulos.py` solo parte por esos dos niveles. |
   | «renglón con puntos guía» | El índice del original quedó en el cuerpo: pasar cada una de esas páginas a `<!-- p.N ÍNDICE ORIGINAL: ... -->` (el índice se genera solo). |
   | «la primera línea del bloque es el rótulo», «… rótulo en medio del código» | `python tools/rotulos_codigo.py <md> --ver`; si todos los bloques «sin rótulo reconocido» de la lista empiezan con uno, aplicar con `--todos`; si no, sin esa opción. |
   | «código en línea partido», «cuadro sin armar», «encabezado de tabla suelto», «fila de tabla vacía», tabla que no cabe en la página | Los resuelve `preparar.py`: si aparecen, el documento se preparó con una versión anterior. Preguntar antes de `--forzar` (pisa lo ajustado a mano) o corregirlos con un script. |
   | Pendiente de `preparar.py`: una fila «quedó debajo de su tabla» | Pasarla a celdas dentro de la tabla, en su lugar. |
   | Pendiente de `preparar.py`: rótulo en negrita solo en su línea | Si era un cuadro, `> [!TIPO] rótulo`; si es un subtítulo, dejarlo. Un tipo por rótulo, aplicado a todos con un script. |
   | Portada | El título y el subtítulo van en la cabecera, y `fecha` si la portada la trae. Lo demás de la portada (etiquetas, viñetas) queda como texto antes del primer capítulo. |
   | Diagrama o recuadro de texto aplanado (negritas sueltas sin frases, flechas `──►` dentro de una celda) | No hay aviso: buscarlo con `grep -n "──►\|^\*\*[^*]*\*\*$"`. `tools/region.py` sobre el original (modo `imagen` para `describir-figuras`, modo `texto` para rehacer un bloque de código con su sangría). |

   Corregir aquí, en español: después de traducir, cada corrección hay que hacerla dos veces.
4. ¿Manual de programación, ingeniería, física o matemática, y no es
   `Manual_Curso_IA_Python_v2`? Entonces se traduce (regla 2; el costo no es motivo para
   dejarlo en español: avisarlo y seguir), y **antes** se verifica contra el original:
   generar el PDF en español (paso 7) y compararlo como «regenerado» en la skill
   `verificar-pdf` hasta código 0. Un antetítulo que la plantilla no lleva («PARTE I ·
   CAPÍTULO 1») se declara: `--ignorar "PARTE I · CAPÍTULO"`, uno por parte.
   Después de traducir solo se puede comparar la estructura, no las palabras.
5. Skill `traducir-manual` (solo si corresponde por el paso 4).
6. `python tools/validar.py documentos/$ARGUMENTS/$ARGUMENTS.md` otra vez: 0 errores y
   0 avisos también en el documento traducido.
7. `python manual.py documentos/$ARGUMENTS/$ARGUMENTS.md -o output/$ARGUMENTS/$ARGUMENTS.pdf --estricto`
   (código 1 = algo se imprimió tal cual o no se imprimió: corregir el `.md`; código 2 =
   no se generó: el mensaje dice la línea).
8. Skill `verificar-pdf` con `$ARGUMENTS`.
9. Informar en 6 líneas o menos: páginas, resultado de la verificación, qué se ajustó a
   mano, qué quedó pendiente y qué no se verificó.

## Presupuesto

- El contenido se mueve con scripts; al contexto entran solo resúmenes y las líneas que
  se editan.
- Nunca reescribir el `.md` completo: `Edit` puntual.
- No leer el PDF: lo verifica `comparar.py`.
- Cambios masivos al `.md`: script en un archivo (no `python -c`: PowerShell altera las
  comillas invertidas y la detección de bloques de código falla sin avisar), con una
  copia del `.md` antes y un conteo de lo cambiado después.
- Si `comparar.py` falla, leer primero `docs/auditoria.md` (secciones 3 a 5): la causa
  suele estar descrita. La ubicación que da para una palabra faltante es la de su última
  aparición en el origen, no necesariamente donde se perdió.
- Detalle de cada ajuste: `docs/generator.md`, sección 4 (leer solo si hace falta).
