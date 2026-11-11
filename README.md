# Plantilla de manual en PDF

Extrae información de documentos (PDF, Word, PowerPoint, Excel, JSON, CSV, Markdown) y
genera manuales PDF con portada, índice, encabezados, pie "Página X de Y", marcadores y
estilos uniformes.

Este repositorio contiene solo el flujo de trabajo (scripts, pruebas, hooks y guías).
Los documentos y sus resultados (`sources/`, `extracted/`, `documentos/`, `output/`) son
locales y no se versionan.

## Flujo

```
sources/ --extraer.py--> extracted/ --preparar.py--> documentos/ --validar.py, manual.py--> output/ --comparar.py
```

| Guía | Para qué |
|---|---|
| [docs/pipeline.md](docs/pipeline.md) | El flujo completo: etapas, bibliotecas instaladas, skills, subagentes y control de costo. |
| [docs/extractor.md](docs/extractor.md) | Extraer el 100% de la información con pocos tokens. |
| [docs/generator.md](docs/generator.md) | Crear, regenerar o actualizar un documento. |
| [docs/auditoria.md](docs/auditoria.md) | Errores conocidos y mejoras pendientes, con su estado. |
| [CLAUDE.md](CLAUDE.md) | Reglas que Claude Code aplica en este proyecto. |

## Uso rápido

```
pip install -r requirements.txt

python tools/extraer.py sources/archivo.pdf          # -> extracted/archivo/
python tools/preparar.py extracted/archivo           # -> documentos/archivo/ + pendientes
python tools/validar.py documentos/x/x.md            # revisa el .md antes de generar
python manual.py documentos/x/x.md -o output/x.pdf   # genera el PDF
python tools/comparar.py sources/archivo.pdf output/x.pdf   # código 0 = correcto
python -m unittest discover tests                    # pruebas del flujo
```

Para un manual nuevo, copia `ejemplo.md` y reemplaza el contenido. `ejemplo.pdf`
explica toda la sintaxis.

## Archivos

| Ruta | Contenido |
|---|---|
| `manual.py` | Generador de PDF (no hace falta editarlo). |
| `tools/extraer.py` | Extractor multiformato a Markdown + reporte de cobertura. |
| `tools/preparar.py` | Pasa una extracción a `documentos/` y aplica los ajustes que no requieren criterio. |
| `tools/validar.py` | Revisa un `.md` antes de generar: errores y sintaxis no admitida, con número de línea. |
| `tools/costo.py` | Estima los tokens de trabajar un documento y propone un plan por tandas. |
| `tools/capitulos.py` | Parte un `.md` por capítulos y lo vuelve a unir (para traducir o trabajar por partes). |
| `tools/comparar_traduccion.py` | Verifica una traducción por su estructura: código, cifras, tablas, enlaces, títulos. |
| `tools/comparar.py` | Verifica el PDF generado contra su origen: faltantes, cifras, portada, sobrantes y orden. |
| `tests/` | Pruebas automáticas. Crean sus propios archivos; no usan `sources/`. |
| `.claude/skills/` | Skills: `/extraer`, `/costo`, `/regenerar-manual`, `/traducir-manual`, `/nuevo-manual`, `/actualizar-manual`, `/verificar-pdf`. |
| `.claude/agents/` | Subagentes: `describir-figuras`, `traductor`, `revisor-visual`. |
| `.claude/hooks/`, `.claude/settings.json` | Hook y permisos de Claude Code (protegen `sources/`). |
| `ejemplo.md` / `ejemplo.pdf` | Ejemplo y guía de sintaxis. `imagenes/` tiene su figura. |
| `sources/` | Originales (no se modifican). Local. |
| `extracted/` | Resultados de extracción. Local. |
| `documentos/` | Fuentes `.md` listas para generar. Local. |
| `output/` | PDFs generados. Local. |
