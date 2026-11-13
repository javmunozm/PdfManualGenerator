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
3. Resolver solo los pendientes que listó, con ediciones puntuales en
   `documentos/$ARGUMENTS/$ARGUMENTS.md` (ubicar cada uno con `grep -n`, leer esas líneas).
   - Jerarquía de títulos, **antes de traducir**: contar `#`, `##` y `###` fuera de
     bloques de código y comparar con «Marcadores del PDF» de `reporte.md`. Si todos los
     títulos quedaron en un mismo nivel, o hay títulos fundidos en un párrafo
     (`**PARTE II · CAPÍTULO 6** **Título** texto...`), corregirlo con un script.
     Capítulos en `#` y secciones en `##`: `capitulos.py` solo parte por esos dos niveles.
   - Rótulos repetidos del original (`**SEGURIDAD**`, `**¿POR QUÉ?**`): elegir un tipo
     de cuadro por rótulo y aplicarlo a todos con un script, no uno por uno.
   - Validar aquí (`tools/validar.py`) y dejar 0 errores y 0 avisos en español: después
     de traducir, cada corrección hay que hacerla dos veces.
4. ¿Manual de programación, ingeniería, física o matemática, y no es
   `Manual_Curso_IA_Python_v2`? Entonces skill `traducir-manual` antes de seguir.
5. `python tools/validar.py documentos/$ARGUMENTS/$ARGUMENTS.md` hasta 0 errores. Los
   avisos se corrigen si cambian lo que el lector ve.
6. `python manual.py documentos/$ARGUMENTS/$ARGUMENTS.md -o output/$ARGUMENTS.pdf`
7. Skill `verificar-pdf` con `$ARGUMENTS`.
8. Informar en 6 líneas o menos: páginas, resultado de la verificación, qué se ajustó a
   mano, qué quedó pendiente.

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
