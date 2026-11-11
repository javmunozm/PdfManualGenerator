# Plantilla de manual en PDF

Extrae documentos a Markdown y genera manuales PDF con formato uniforme.

```
sources/ --extraer.py--> extracted/ --preparar.py--> documentos/ --validar.py, manual.py--> output/
```

## Reglas (obligatorias)

1. **`sources/` es del usuario.** No leer, listar, extraer ni probar con sus archivos sin
   permiso explícito para ese archivo. Nunca modificarlos. Para probar herramientas, usar
   solo archivos propios (`ejemplo.md`, `ejemplo.pdf`, los que crea `tests/`).
2. **Manuales técnicos en inglés.** Los manuales de programación, ingeniería, física y
   matemática se traducen al inglés y se trabajan en inglés: el `.md` de `documentos/`
   y el PDF quedan en inglés. Única excepción: `Manual_Curso_IA_Python_v2`, que se
   mantiene en español. Al traducir: todo el contenido (regla 4), sin tocar código,
   comandos, nombres de archivos, fórmulas ni cifras.
3. **No abrir originales en el contexto.** Nada de leer PDF, Word, PowerPoint o Excel
   directamente: se extrae con `tools/extraer.py` y se lee primero `reporte.md`.
4. **Transcribir, no resumir.** La meta es el 100% de la información.
5. **El `.md` es la fuente; el PDF es un resultado.** Se edita el `.md` de `documentos/`
   y se vuelve a generar. Nunca se edita el PDF.
6. **Resultados a archivos, resúmenes a la terminal.** No imprimir documentos completos.
7. **No volver a extraer lo ya extraído.** `extraer.py` lo impide salvo `--forzar`.
8. **Un PDF no está terminado hasta que `tools/comparar.py` termina con código 0.**

## Comandos

```
python tools/extraer.py sources/<archivo>             # -> extracted/<nombre>/
python tools/preparar.py extracted/<nombre>           # -> documentos/<nombre>/ + pendientes
python tools/validar.py documentos/<n>/<n>.md         # antes de generar; 0 = sin errores
python manual.py documentos/<n>/<n>.md -o output/<n>.pdf
python tools/comparar.py <origen> output/<n>.pdf      # código 0 = correcto, 1 = falla
python -m unittest discover tests                     # pruebas (no usan sources/)
```

## Skills

Usar la skill del caso en vez de armar los pasos de memoria: `/costo` antes de un
documento largo, `/regenerar-manual`, `/traducir-manual`, `/nuevo-manual`,
`/actualizar-manual`, `/verificar-pdf`. `/extraer` solo la invoca el usuario.
Las imágenes y la traducción van siempre a subagentes (`describir-figuras`,
`traductor`, `revisor-visual`): no entran a la conversación principal.

## Guías

- `docs/pipeline.md`: flujo completo, bibliotecas, skills y control de costo.

- `docs/extractor.md`: cómo extraer y resolver pendientes.
- `docs/generator.md`: cómo crear, regenerar o actualizar un documento; sintaxis.
- `docs/auditoria.md`: errores conocidos y mejoras pendientes, con su estado.

Los hooks de `.claude/hooks/` aplican las reglas 1 y 3.
