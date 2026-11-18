# Plantilla de manual en PDF

Extrae documentos a Markdown y genera manuales PDF con formato uniforme.

```
sources/ --extraer.py--> extracted/ --preparar.py--> documentos/ --validar.py, manual.py--> output/
```

## Reglas (obligatorias)

1. **`sources/` se usa, no se modifica.** Sus archivos son material de origen: ubicarlos,
   extraerlos, recortarlos (`region.py`) y compararlos (`comparar.py`) está permitido. Que
   el usuario pida convertir un manual ya autoriza su archivo, sin pedirle `/extraer`.
   **Lo único prohibido** es alterar el archivo de origen: editarlo, sobrescribirlo,
   moverlo, renombrarlo o borrarlo, o cualquier operación que deje otro resultado en ese
   mismo archivo. Lo producido va siempre a `extracted/`, `documentos/` u `output/`.
   Extraer no es modificar. Para probar herramientas (no para convertir un manual), usar
   solo archivos propios (`ejemplo.md`, `ejemplo.pdf`, los que crea `tests/`).
2. **Manuales técnicos en inglés.** Los manuales de programación, ingeniería, física y
   matemática se traducen al inglés y se trabajan en inglés: el `.md` de `documentos/`
   y el PDF quedan en inglés. Única excepción: `Manual_Curso_IA_Python_v2`, que se
   mantiene en español. Al traducir: todo el contenido (regla 4), también lo que no es
   código dentro de los bloques de código (comentarios, anotaciones de árboles, textos de
   la interfaz, mensajes); sin tocar el código, comandos, nombres de archivos, claves,
   fórmulas ni cifras. Lo comprueba `tools/comparar_traduccion.py`.
3. **No abrir originales en el contexto.** Nada de leer PDF, Word, PowerPoint o Excel
   directamente: se extrae con `tools/extraer.py` y se lee primero `reporte.md`.
4. **Transcribir, no resumir.** La meta es el 100% de la información.
5. **El `.md` es la fuente; el PDF es un resultado.** Se edita el `.md` de `documentos/`
   y se vuelve a generar. Nunca se edita el PDF.
6. **Resultados a archivos, resúmenes a la terminal.** No imprimir documentos completos.
7. **No volver a extraer lo ya extraído.** `extraer.py` lo impide salvo `--forzar`.
8. **Un PDF no está terminado hasta que `tools/validar.py` da 0 errores y 0 avisos y
   `tools/comparar.py` termina con código 0.** Las dos son obligatorias en todo documento:
   `comparar.py` cuenta palabras; la estructura (títulos, tablas, cuadros, código) la
   revisa `validar.py`.
9. **El contenido sale de `sources/`.** Si el manual no parte de un archivo de `sources/`,
   el contenido se investiga en la web según lo que el lector (el usuario u otra persona)
   necesita aprender; no se escribe de memoria. La regla 5 habla de qué se edita, no de
   dónde sale el contenido.
10. **Se trabaja sobre temporales.** Lo que pisaría trabajo hecho (`--forzar`) se hace en
    copias del scratchpad (`preparar.py --salida <temp>`); la fuente no se toca nunca.
    Al terminar, los temporales se borran y en `docs/registro.md` queda qué se hizo, con
    qué scripts y qué falló.

## Comandos

```
python tools/extraer.py sources/<archivo>             # -> extracted/<nombre>/; 1 = con pendientes
python tools/preparar.py extracted/<nombre>           # -> documentos/<nombre>/ + pendientes
python tools/rotulos_codigo.py documentos/<n>/<n>.md --ver   # rótulos de recuadro dentro del código
python tools/validar.py documentos/<n>/<n>.md         # estructura; 0 errores y 0 avisos
python manual.py documentos/<n>/<n>.md -o output/<n>/<n>.pdf --estricto
python tools/comparar.py <origen> output/<n>/<n>.pdf      # código 0 = correcto, 1 = falla
python tools/revisar.py output/<n>/<n>.pdf                # hojas para el subagente revisor-visual
python tools/estado.py                                # en qué está cada documento
python -m unittest discover tests                     # pruebas (no usan sources/)
```

## Skills

Usar la skill del caso en vez de armar los pasos de memoria: `/costo` antes de un
documento largo, `/regenerar-manual`, `/traducir-manual`, `/nuevo-manual`,
`/actualizar-manual`, `/verificar-pdf`, `/extraer` (también cuando el usuario pide
convertir un manual: regla 1).
Las imágenes y la traducción van siempre a subagentes (`describir-figuras`,
`traductor`, `revisor-visual`): no entran a la conversación principal.

## Guías

- `docs/pipeline.md`: flujo completo, bibliotecas, skills y control de costo.
- `docs/extractor.md`: cómo extraer y resolver pendientes.
- `docs/generator.md`: cómo crear, regenerar o actualizar un documento; sintaxis.
- `docs/auditoria.md`: errores conocidos y mejoras pendientes, con su estado.
- `docs/registro.md`: índice de los trabajos hechos sobre temporales (regla 10).

Un manual en inglés lleva `idioma: en` en la cabecera. `<origen>` de `comparar.py`: el
original de `sources/` si es un PDF y el manual se regeneró; el `.md` de `documentos/`
con `--estricto` si es nuevo, actualizado o traducido (detalle en `docs/pipeline.md`).

Los hooks de `.claude/hooks/` aplican las reglas 1 y 3 (`guardia.py`) y avisan de un `.md`
con errores o de un PDF desactualizado (`flujo.py`).
