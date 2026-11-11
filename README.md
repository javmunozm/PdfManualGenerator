# Plantilla de manual en PDF

Extrae información de documentos (PDF, Word, PowerPoint, Excel, JSON, CSV, Markdown) y
genera manuales PDF con portada, índice, encabezados, pie "Página X de Y", marcadores y
estilos uniformes.

Este repositorio contiene solo el flujo de trabajo (scripts, pruebas, hooks y guías).
Los documentos y sus resultados (`sources/`, `extracted/`, `documentos/`, `output/`) son
locales y no se versionan.

## Flujo

```
sources/  --tools/extraer.py-->  extracted/  --preparar-->  documentos/  --manual.py-->  output/
```

| Guía | Para qué |
|---|---|
| [docs/extractor.md](docs/extractor.md) | Extraer el 100% de la información con pocos tokens. |
| [docs/generator.md](docs/generator.md) | Crear, regenerar o actualizar un documento. |
| [docs/auditoria.md](docs/auditoria.md) | Errores conocidos y mejoras pendientes, con su estado. |
| [CLAUDE.md](CLAUDE.md) | Reglas que Claude Code aplica en este proyecto. |

## Uso rápido

```
pip install -r requirements.txt

python tools/extraer.py sources/archivo.pdf          # -> extracted/archivo/
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
| `tools/comparar.py` | Verifica el PDF generado contra su origen: faltantes, cifras, portada, sobrantes y orden. |
| `tests/` | Pruebas automáticas. Crean sus propios archivos; no usan `sources/`. |
| `.claude/` | Hooks y permisos de Claude Code (protegen `sources/`). |
| `ejemplo.md` / `ejemplo.pdf` | Ejemplo y guía de sintaxis. `imagenes/` tiene su figura. |
| `sources/` | Originales (no se modifican). Local. |
| `extracted/` | Resultados de extracción. Local. |
| `documentos/` | Fuentes `.md` listas para generar. Local. |
| `output/` | PDFs generados. Local. |
